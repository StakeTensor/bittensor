""" An interface for serializing and deserializing bittensor tensors"""
from bittensor import bittensor_pb2
import numpy as np
import pickle
import PIL
import torch
from typing import List, Tuple, Dict, Optional

import bittensor
   
def torch_dtype_to_bittensor_dtype(tdtype):
    if tdtype == torch.float32:
        dtype = bittensor_pb2.DataType.FLOAT32
    elif tdtype == torch.float64:
        dtype = bittensor_pb2.DataType.FLOAT64
    elif tdtype == torch.int32:
        dtype = bittensor_pb2.DataType.INT32
    elif tdtype == torch.int64:
        dtype = bittensor_pb2.DataType.INT64
    else:
        dtype = bittensor_pb2.DataType.UNKNOWN
    return dtype


def bittensor_dtype_to_torch_dtype(odtype):
    if odtype == bittensor_pb2.DataType.FLOAT32:
        dtype = torch.float32
    elif odtype == bittensor_pb2.DataType.FLOAT64:
        dtype = torch.float64
    elif odtype == bittensor_pb2.DataType.INT32:
        dtype = torch.int32
    elif odtype == bittensor_pb2.DataType.INT64: 
        dtype = torch.int64
    else:
        # TODO (const): raise error
        dtype = torch.float32
    return dtype

def bittensor_dtype_np_dtype(odtype):
    if odtype == bittensor_pb2.DataType.FLOAT32:
        dtype = np.float32
    elif odtype == bittensor_pb2.DataType.FLOAT64:
        dtype = np.float64
    elif odtype == bittensor_pb2.DataType.INT32:
        dtype = np.int32
    elif odtype == bittensor_pb2.DataType.INT64: 
        dtype = np.int64
    else:
        # TODO(const): raise error.
        dtype = np.float32
    return dtype

class PyTorchSerializer():
    
    @staticmethod
    def image_todef(tensor: List[object]) -> bittensor_pb2.TensorDef:
        """ Returns a bittensor TensorDef proto for a torch.Tensor. 

        Args:
            tensor (torch.Tensor): Any torch.Tensor object.

        Returns:
            bittensor_pb2.TensorDef: An bittensor TensorDef for the passed torch.Tensor.
        """    
        shape = [len(tensor), 1]
        dtype = bittensor_pb2.DataType.IMAGE
        return bittensor_pb2.TensorDef(
                        version = bittensor.__version__, 
                        shape = shape, 
                        dtype = dtype,
                        requires_grad = False)
   
    @staticmethod
    def string_todef(tensor: List[str]) -> bittensor_pb2.TensorDef:
        """ Returns a bittensor TensorDef proto for a torch.Tensor. 

        Args:
            tensor (torch.Tensor): Any torch.Tensor object.

        Returns:
            bittensor_pb2.TensorDef: An bittensor TensorDef for the passed torch.Tensor.
        """         
        shape = [len(tensor), 1]
        dtype = bittensor_pb2.DataType.STRING
        return bittensor_pb2.TensorDef(
                        version = bittensor.__version__, 
                        shape = shape, 
                        dtype = dtype,
                        requires_grad = False)
        
    @staticmethod
    def tensor_todef(tensor: torch.Tensor) -> bittensor_pb2.TensorDef:
        """ Returns a bittensor TensorDef proto for a torch.Tensor. 

        Args:
            tensor (torch.Tensor): Any torch.Tensor object.

        Returns:
            bittensor_pb2.TensorDef: An bittensor TensorDef for the passed torch.Tensor.
        """
        dtype = torch_dtype_to_bittensor_dtype(tensor.dtype)
        # NOTE: The first dimension is the batch dimensiondatetime A combination of a date and a time. Attributes: ()
        assert len(tensor.shape) > 1
        shape = list(tensor.shape)
        return bittensor_pb2.TensorDef(
                        version = bittensor.__version__, 
                        shape = shape, 
                        dtype = dtype,
                        requires_grad = tensor.requires_grad)
    
    @staticmethod
    def serialize(tensor: object) -> bittensor_pb2.Tensor:
        """Serializes a torch.Tensor to an bittensor Tensor proto.

        Args:
            tensor (torch.Tensor): torch.Tensor to serialize.

        Returns:
            bittensor_pb2.Tensor: Serialized tensor as bittensor_pb2.proto. 
        """
        
        # Check typing
        if isinstance(tensor, torch.Tensor):
            return PyTorchSerializer.serialize_tensor( tensor )
        elif isinstance (tensor, list):
            if isinstance (tensor[0], str):
                return PyTorchSerializer.serialize_string ( tensor )
            elif isinstance (tensor[0], PIL.Image.Image):
                return PyTorchSerializer.serialize_image ( tensor )
            else:
                raise NotImplementedError
        else:
            raise NotImplementedError
    
    @staticmethod
    def serialize_string(tensor: List[str]) -> bittensor_pb2.Tensor:
        """Serializes a torch.Tensor to an bittensor Tensor proto.

        Args:
            tensor (torch.Tensor): torch.Tensor to serialize.

        Returns:
            bittensor_pb2.Tensor: Serialized tensor as bittensor_pb2.proto. 
        """
            
        data_buffer = pickle.dumps(tensor)
        tensor_def = PyTorchSerializer.string_todef(tensor)
        proto = bittensor_pb2.Tensor(
                    version = bittensor.__version__,
                    buffer = data_buffer,
                    tensor_def = tensor_def)      
        return proto
        
    @staticmethod
    def serialize_image(tensor: List[object]) -> bittensor_pb2.Tensor:
        """Serializes a torch.Tensor to an bittensor Tensor proto.

        Args:
            tensor (torch.Tensor): torch.Tensor to serialize.

        Returns:
            bittensor_pb2.Tensor: Serialized tensor as bittensor_pb2.proto. 
        """
            
        data_buffer = pickle.dumps(tensor)
        tensor_def = PyTorchSerializer.image_todef(tensor)
        proto = bittensor_pb2.Tensor(
                    version = bittensor.__version__,
                    buffer = data_buffer,
                    tensor_def = tensor_def)      
        return proto
    
    
    @staticmethod
    def serialize_tensor(tensor: torch.Tensor) -> bittensor_pb2.Tensor:
        """Serializes a torch.Tensor to an bittensor Tensor proto.

        Args:
            tensor (torch.Tensor): torch.Tensor to serialize.

        Returns:
            bittensor_pb2.Tensor: Serialized tensor as bittensor_pb2.proto. 
        """
        # Using numpy intermediary because deserializing with pickle can run arbitray code on your machine.
        data_buffer = tensor.cpu().numpy().tobytes()
        tensor_def = PyTorchSerializer.tensor_todef(tensor)
        proto = bittensor_pb2.Tensor(
                    version = bittensor.__version__,
                    buffer = data_buffer,
                    tensor_def = tensor_def)      
        return proto

    @staticmethod
    def deserialize_image(proto: bittensor_pb2.Tensor) -> List[object]:
        """Deserializes an bittensor_pb2.Tensor to a torch.Tensor object.

        Args:
            proto (bittensor_pb2.Tensor): Proto to derserialize.

        Returns:
            List[object]:
        """
        return pickle.loads(proto.buffer)
    
    @staticmethod
    def deserialize_string(proto: bittensor_pb2.Tensor) -> List[str]:
        """Deserializes an bittensor_pb2.Tensor to a torch.Tensor object.

        Args:
            proto (bittensor_pb2.Tensor): Proto to derserialize.

        Returns:
            List[object]:
        """
        return pickle.loads(proto.buffer)
            
    @staticmethod
    def deserialize_tensor(proto: bittensor_pb2.Tensor) -> torch.Tensor:
        """Deserializes an bittensor_pb2.Tensor to a torch.Tensor object.

        Args:
            proto (bittensor_pb2.Tensor): Proto to derserialize.

        Returns:
            torch.Tensor: torch.Tensor to deserialize.
        """
        dtype = bittensor_dtype_np_dtype(proto.tensor_def.dtype)
        # TODO avoid copying the array (need to silence pytorch warning, because array is not writable)
        array = np.frombuffer(proto.buffer, dtype=np.dtype(dtype)).copy()
        # NOTE (const): The first dimension is always assumed to be the batch dimension.
        shape = tuple(proto.tensor_def.shape)
        assert len(shape) > 1 
        tensor = torch.as_tensor(array).view(shape).requires_grad_(proto.tensor_def.requires_grad)
        return tensor