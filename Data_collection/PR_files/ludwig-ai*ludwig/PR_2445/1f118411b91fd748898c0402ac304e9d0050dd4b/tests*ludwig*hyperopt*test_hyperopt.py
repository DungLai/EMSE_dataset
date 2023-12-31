import pytest

from ludwig.constants import ENCODER, INPUT_FEATURES, NAME, OUTPUT_FEATURES, TYPE
from ludwig.hyperopt.execution import substitute_parameters
from ludwig.hyperopt.run import get_features_eligible_for_shared_params


def _setup():
    config = {
        INPUT_FEATURES: [{NAME: "title", TYPE: "text"}],
        OUTPUT_FEATURES: [{NAME: "summary", TYPE: "text"}],
    }
    return config


def test_hyperopt_without_encoders_or_decoders():
    config = _setup()
    features_eligible_for_shared_params = {
        INPUT_FEATURES: get_features_eligible_for_shared_params(config, INPUT_FEATURES),
        OUTPUT_FEATURES: get_features_eligible_for_shared_params(config, OUTPUT_FEATURES),
    }
    assert features_eligible_for_shared_params[INPUT_FEATURES] == {"text": {"title"}}
    assert features_eligible_for_shared_params[OUTPUT_FEATURES] == {"text": {"summary"}}


@pytest.mark.parametrize("encoder", ["parallel_cnn", "stacked_cnn"])
def test_hyperopt_default_encoder(encoder: str):
    config = _setup()
    config[INPUT_FEATURES][0][ENCODER] = {TYPE: encoder}
    features_eligible_for_shared_params = get_features_eligible_for_shared_params(config, INPUT_FEATURES)
    print(features_eligible_for_shared_params)
    if encoder == "parallel_cnn":
        assert features_eligible_for_shared_params == {"text": {"title"}}
    else:
        # When non-default encoder is passed, there should be no features eligible for shared params
        assert features_eligible_for_shared_params == {}


@pytest.mark.parametrize(
    "parameters, expected",
    [
        (
            {
                "combiner.type": "tabnet",
                "combiner.fc_layers": [{"output_size": 64}, {"output_size": 32}],
                "trainer.learning_rate": 0.1,
                "trainer.batch_size": 256,
            },
            {
                "combiner": {"type": "tabnet", "fc_layers": [{"output_size": 64}, {"output_size": 32}]},
                "trainer": {"learning_rate": 0.1, "batch_size": 256},
            },
        ),
        (
            {
                ".": {
                    "combiner": {"type": "concat", "num_fc_layers": 2},
                    "trainer": {"learning_rate_scaling": "linear"},
                },
                "trainer.learning_rate": 0.1,
            },
            {
                "combiner": {"type": "concat", "num_fc_layers": 2},
                "trainer": {"learning_rate_scaling": "linear", "learning_rate": 0.1},
            },
        ),
        (
            {
                ".": {
                    "combiner": {"type": "concat", "num_fc_layers": 2},
                    "trainer": {"learning_rate_scaling": "linear"},
                },
                "trainer": {
                    "learning_rate": 0.1,
                    "batch_size": 256,
                },
            },
            {
                "combiner": {"type": "concat", "num_fc_layers": 2},
                "trainer": {"learning_rate_scaling": "linear", "learning_rate": 0.1, "batch_size": 256},
            },
        ),
    ],
    ids=["flat", "nested", "multi-nested"],
)
def test_substitute_parameters(parameters, expected):
    config = _setup()
    expected_config = {**config, **expected}
    actual_config = substitute_parameters(config, parameters)
    print(actual_config)
    print(expected_config)
    assert actual_config == expected_config
