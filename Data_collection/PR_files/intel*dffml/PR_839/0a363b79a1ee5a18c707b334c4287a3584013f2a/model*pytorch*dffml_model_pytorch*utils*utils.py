import sys
import inspect

import numpy as np
import torch.nn as nn
from torch.utils.data import Dataset
from torchvision import transforms

from dffml.base import BaseDataFlowFacilitatorObject
from dffml.util.entrypoint import base_entry_point, entrypoint
from .config import make_pytorch_config


def create_layer(layer_dict):
    """
    If the layer_dict is a dict of dict, a Sequential layer will be returned
    with all the indented inner layers, else if the layer_dict is a single layer
    i.e. of type Dict[str, int/str/float/sequence/bool], that layer is returned.
    """

    sequential_dict = nn.Sequential()
    for name, layer in layer_dict.items():
        if isinstance(layer, dict):
            parameters = {k: v for k, v in layer.items()}
            layer_name = parameters.pop("name")

            sequential_dict.add_module(
                name, getattr(nn, layer_name)(**parameters)
            )
        else:
            parameters = {k: v for k, v in layer_dict.items()}
            layer_name = parameters.pop("name")
            return getattr(nn, layer_name)(**parameters)
    return sequential_dict


class NumpyToTensor(Dataset):
    def __init__(
        self,
        data,
        target=None,
        size=None,
        normalizing_mean=None,
        normalizing_std=None,
    ):
        self.data = data
        self.target = target
        self.size = size
        self.mean = normalizing_mean
        self.std = normalizing_std

    def transform(self, data):
        transform = []

        if self.size:
            transform.extend(
                [
                    transforms.ToPILImage(),
                    transforms.Resize(self.size),
                    transforms.CenterCrop((self.size, self.size)),
                ]
            )
        transform.append(transforms.ToTensor())
        if self.mean and self.std:
            transform.append(transforms.Normalize(self.mean, self.std))

        return transforms.Compose(transform)(data)

    def __getitem__(self, index):
        x = self.transform(self.data[index])

        if self.target is not None:
            y = self.target[index]
            if isinstance(y, np.ndarray):
                y = self.transform(y)
            return x, y
        else:
            return x

    def __len__(self):
        return len(self.data)


@base_entry_point("dffml.model.pytorch.loss", "loss")
class PyTorchLoss(BaseDataFlowFacilitatorObject):
    def __init__(self, config):
        super().__init__(config)
        self.function = self.LOSS(**self.config._asdict())

    @classmethod
    def load(cls, class_name: str = None):
        for name, loss_class in inspect.getmembers(nn, inspect.isclass):
            if name.endswith("Loss"):
                if name.lower() == class_name:
                    return getattr(sys.modules[__name__], name + "Function")


for name, loss_class in inspect.getmembers(nn, inspect.isclass):
    if name.endswith("Loss"):

        cls_config = make_pytorch_config(name + "Config", loss_class)

        cls = entrypoint(name.lower())(
            type(
                name + "Function",
                (PyTorchLoss,),
                {"CONFIG": cls_config, "CONTEXT": {}, "LOSS": loss_class,},
            )
        )

        setattr(sys.modules[__name__], cls.__qualname__, cls)

# TODO Currently only the torch.nn module has annotations
# Add PyTorchOptimizer and PyTorchScheduler after the next torch release
# as they are currently adding type annotations for everything
