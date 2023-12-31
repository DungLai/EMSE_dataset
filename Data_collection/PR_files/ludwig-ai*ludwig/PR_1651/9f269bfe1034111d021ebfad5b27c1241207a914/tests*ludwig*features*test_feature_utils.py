import torch

from ludwig.features import feature_utils


def test_ludwig_feature_dict():
    feature_dict = feature_utils.LudwigFeatureDict()

    to_module = torch.nn.Module()
    type_module = torch.nn.Module()

    feature_dict["to"] = to_module
    feature_dict["type"] = type_module

    assert len(feature_dict) == 2
    assert feature_dict.keys() == ["to", "type"]
    assert feature_dict.items() == [("to", to_module), ("type", type_module)]
    assert feature_dict["to"] == to_module

    feature_dict.update({"1": torch.nn.Module()})

    assert len(feature_dict) == 3
