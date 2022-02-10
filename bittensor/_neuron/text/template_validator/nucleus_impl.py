import bittensor
import torch
from torch.nn import TransformerEncoder, TransformerEncoderLayer
import torch.nn.functional as F
from ..neuron_utilities import joining_context, jacobian, partial_contexts


class Validator( torch.nn.Module ):

        def __init__(self, config, metagraph, dendrite, device):
            super(Validator, self).__init__()
            self.layers = TransformerEncoderLayer( bittensor.__network_dim__, config.nucleus.nhead, config.nucleus.nhid, config.nucleus.dropout, batch_first=True)
            self.encoder = TransformerEncoder( self.layers, config.nucleus.nlayers )
            self.decoder = torch.nn.Linear( bittensor.__network_dim__, bittensor.__vocab_size__ , bias=False)
            self.loss_fct = torch.nn.CrossEntropyLoss()
            self.peer_weights = torch.nn.Parameter(torch.ones( [ metagraph().n.item() ] , requires_grad=True, device = device))
            self.noise_offset = 0.0000001
            self.metagraph = metagraph
            self.dendrite = dendrite
            self.config = config
            self.device = device


        def forward ( self, inputs ):
            # Apply model.
            query_hidden = self.query( inputs )
            encoded_hidden = self.encoder( query_hidden )
            decoded_targets = self.decoder ( encoded_hidden )

            # Compute loss.
            shift_logits = decoded_targets[..., :-1, :].contiguous()
            shift_labels = inputs[..., 1:].contiguous()     
            self.loss = self.loss_fct( shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1) )
            return self.loss, decoded_targets

        def scores ( self , loss, inputs  ):
            """Computes salience scores for each peer in the network w.r.t the loss. 
            We use a simplified fishers information score. score_i = hessian_ii * peer_weight_i^2
            """
            validator_scores = torch.zeros(self.peer_weights.size())
            with torch.no_grad():
                for uid in self.partial_context:

                    remote_hidden = self.encoder( self.partial_context[uid] )
                    remote_target = self.decoder(remote_hidden)
                    shift_logits = remote_target[..., :-1, :].contiguous()
                    shift_labels = inputs[..., 1:].contiguous()
                    partial_remote_target_loss = self.loss_fct( shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1) ).item()
                    print(uid,loss, partial_remote_target_loss)
                    validator_scores[uid] =  (partial_remote_target_loss - loss.item())/loss.item()
                    
            peer_weights_d1 = jacobian(loss, self.peer_weights)
            first_order = (peer_weights_d1.detach()* -self.peer_weights.detach())
            print(F.normalize(validator_scores, p = 2,dim=0))
            print(F.normalize(first_order, p = 2,dim=0))
            #validator_scores= validator_scores + first_order
            #print(validator_scores)
            return F.leaky_relu(F.normalize(validator_scores, p = 2,dim=0)*(0.5) + F.normalize(first_order, p = 2,dim=0)*(0.5), negative_slope=0.1)

        def query ( self, inputs ):

            # ---- Get active peers and their weights ---- 
            active_uids = torch.where(self.metagraph().active > 0)[0]
            active_peer_weights = self.peer_weights[active_uids]

            # ---- Topk Weights ---- (TODO: check if the gaussians are enough disrupt the chain weights)
            real_topk = min( self.config.nucleus.topk, self.metagraph().n.item(), len(active_uids))
            noise = torch.normal( 0, torch.std(active_peer_weights).item()+self.noise_offset, size=( active_peer_weights.size())).to( self.config.neuron.device )
            topk_weights, topk_idx = bittensor.unbiased_topk(active_peer_weights + noise , real_topk, dim=0)
            topk_uids = active_uids[topk_idx]

            # ---- Query network ----
            responses, return_ops, query_times = self.dendrite.forward_text ( 
                endpoints = self.metagraph().endpoints[ topk_uids ], 
                inputs = inputs
            )

            # ---- Join based on weights ----
            joining_uids = torch.where(return_ops== bittensor.proto.ReturnCode.Success)[0]
            joining_weights = F.softmax( topk_weights[(return_ops == bittensor.proto.ReturnCode.Success)], dim = 0 )
            output = torch.zeros( (inputs.shape[0], inputs.shape[1], bittensor.__network_dim__)).to( self.device )
            for index, joining_weight in enumerate( joining_weights ): 
                output += responses[joining_uids[index]].to( self.device ) * joining_weight

            # ---- Calculate masked peers ----
            self.partial_context = partial_contexts(return_ops, topk_uids, topk_weights, responses)

            return output