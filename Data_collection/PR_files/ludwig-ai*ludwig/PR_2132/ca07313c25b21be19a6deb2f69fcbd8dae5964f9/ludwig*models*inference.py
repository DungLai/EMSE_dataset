import os
from typing import Any, Dict, List, TYPE_CHECKING, Union

import pandas as pd
import torch
from torch import nn

from ludwig.constants import COLUMN, NAME, TYPE
from ludwig.data.postprocessing import convert_dict_to_df
from ludwig.data.preprocessing import load_metadata
from ludwig.features.feature_registries import input_type_registry, output_type_registry
from ludwig.features.feature_utils import get_module_dict_key_from_name, get_name_from_module_dict_key
from ludwig.globals import INFERENCE_MODULE_FILE_NAME, MODEL_HYPERPARAMETERS_FILE_NAME, TRAIN_SET_METADATA_FILE_NAME
from ludwig.utils.audio_utils import read_audio_from_path
from ludwig.utils.image_utils import read_image_from_path
from ludwig.utils.types import TorchscriptPreprocessingInput

# Prevents circular import errors from typing.
if TYPE_CHECKING:
    from ludwig.models.ecd import ECD

from ludwig.utils.data_utils import load_json
from ludwig.utils.misc_utils import get_from_registry


class InferenceModule(nn.Module):
    """Wraps preprocessing, model forward pass, and postprocessing into a single module.

    The purpose of the module is to be scripted into Torchscript for native serving. The nn.ModuleDict attributes of
    this module use keys generated by feature_utils.get_module_dict_key_from_name in order to prevent name collisions
    with keywords reserved by TorchScript.

    TODO(geoffrey): Implement torchscript-compatible feature_utils.LudwigFeatureDict to replace
    get_module_dict_key_from_name and get_name_from_module_dict_key usage.
    """

    def __init__(self, model: "ECD", config: Dict[str, Any], training_set_metadata: Dict[str, Any]):
        super().__init__()

        model.cpu()
        self.model = model.to_torchscript()

        input_features = {
            feature[NAME]: get_from_registry(feature[TYPE], input_type_registry) for feature in config["input_features"]
        }
        self.preproc_modules = nn.ModuleDict()
        for feature_name, feature in input_features.items():
            module_dict_key = get_module_dict_key_from_name(feature_name)
            self.preproc_modules[module_dict_key] = feature.create_preproc_module(training_set_metadata[feature_name])

        self.predict_modules = nn.ModuleDict()
        for feature_name, feature in model.output_features.items():
            module_dict_key = get_module_dict_key_from_name(feature_name)
            self.predict_modules[module_dict_key] = feature.prediction_module

        output_features = {
            feature[NAME]: get_from_registry(feature[TYPE], output_type_registry)
            for feature in config["output_features"]
        }
        self.postproc_modules = nn.ModuleDict()
        for feature_name, feature in output_features.items():
            module_dict_key = get_module_dict_key_from_name(feature_name)
            self.postproc_modules[module_dict_key] = feature.create_postproc_module(training_set_metadata[feature_name])

    def forward(self, inputs: Dict[str, TorchscriptPreprocessingInput]):
        with torch.no_grad():
            preproc_inputs = {}
            for module_dict_key, preproc in self.preproc_modules.items():
                feature_name = get_name_from_module_dict_key(module_dict_key)
                preproc_inputs[feature_name] = preproc(inputs[feature_name])
            outputs = self.model(preproc_inputs)

            predictions: Dict[str, Dict[str, torch.Tensor]] = {}
            for module_dict_key, predict in self.predict_modules.items():
                feature_name = get_name_from_module_dict_key(module_dict_key)
                predictions[feature_name] = predict(outputs, feature_name)

            postproc_outputs: Dict[str, Dict[str, Any]] = {}
            for module_dict_key, postproc in self.postproc_modules.items():
                feature_name = get_name_from_module_dict_key(module_dict_key)
                postproc_outputs[feature_name] = postproc(predictions[feature_name])

            return postproc_outputs


class InferenceLudwigModel:
    """Model for inference with the subset of the LudwigModel interface used for prediction.

    This model is instantiated with a model_dir, which contains the model and its metadata.
    """

    def __init__(self, model_dir: str):
        self.model = torch.jit.load(os.path.join(model_dir, INFERENCE_MODULE_FILE_NAME))
        self.config = load_json(os.path.join(model_dir, MODEL_HYPERPARAMETERS_FILE_NAME))
        self.training_set_metadata = load_metadata(os.path.join(model_dir, TRAIN_SET_METADATA_FILE_NAME))

    def predict(
        self, dataset: pd.DataFrame, return_type: Union[dict, pd.DataFrame] = pd.DataFrame
    ) -> Union[pd.DataFrame, dict]:
        """Predict on a batch of data.

        One difference between InferenceLudwigModel and LudwigModel is that the input data must be a pandas DataFrame.
        """
        inputs = {
            if_config["name"]: to_inference_module_input(dataset[if_config[COLUMN]], if_config[TYPE])
            for if_config in self.config["input_features"]
        }

        preds = self.model(inputs)

        if return_type == pd.DataFrame:
            preds = convert_dict_to_df(preds)
        return preds, None  # Second return value is for compatibility with LudwigModel.predict


def to_inference_module_input(s: pd.Series, feature_type: str, load_paths=False) -> Union[List[str], torch.Tensor]:
    """Converts a pandas Series to be compatible with a torchscripted InferenceModule forward pass."""
    if feature_type == "image":
        if load_paths:
            return [read_image_from_path(v) if isinstance(v, str) else v for v in s]
    elif feature_type == "audio":
        if load_paths:
            return [read_audio_from_path(v) if isinstance(v, str) else v for v in s]
    if feature_type in {"binary", "category", "bag", "set", "text", "sequence", "timeseries"}:
        return s.astype(str).to_list()
    return torch.from_numpy(s.to_numpy())