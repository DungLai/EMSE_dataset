#! /usr/bin/env python
# coding=utf-8
# Copyright (c) 2019 Uber Technologies, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
from ludwig.constants import *
from ludwig.features.feature_registries import base_type_registry
from ludwig.features.feature_registries import input_type_registry
from ludwig.features.feature_registries import output_type_registry
from ludwig.utils.misc_utils import get_from_registry
from ludwig.utils.misc_utils import merge_dict
from ludwig.utils.misc_utils import set_default_value
import warnings

default_random_seed = 42

default_preprocessing_force_split = False
default_preprocessing_split_probabilities = (0.7, 0.1, 0.2)
default_preprocessing_stratify = None

default_preprocessing_parameters = {
    'force_split': default_preprocessing_force_split,
    'split_probabilities': default_preprocessing_split_probabilities,
    'stratify': default_preprocessing_stratify
}
default_preprocessing_parameters.update({
    name: base_type.preprocessing_defaults for name, base_type in
    base_type_registry.items()
})

default_combiner_type = 'concat'

default_training_params = {
    'optimizer': {'type': 'adam'},
    'epochs': 100,
    'regularizer': 'l2',
    'regularization_lambda': 0,
    'learning_rate': 0.001,
    'batch_size': 128,
    'eval_batch_size': 0,
    'early_stop': 5,
    'reduce_learning_rate_on_plateau': 0,
    'reduce_learning_rate_on_plateau_patience': 5,
    'reduce_learning_rate_on_plateau_rate': 0.5,
    'increase_batch_size_on_plateau': 0,
    'increase_batch_size_on_plateau_patience': 5,
    'increase_batch_size_on_plateau_rate': 2,
    'increase_batch_size_on_plateau_max': 512,
    'decay': False,
    'decay_steps': 10000,
    'decay_rate': 0.96,
    'staircase': False,
    'gradient_clipping': None,
    'validation_field': COMBINED,
    'validation_metric': LOSS,
    'bucketing_field': None,
    'learning_rate_warmup_epochs': 1
}

default_optimizer_params_registry = {
    'sgd': {},
    'stochastic_gradient_descent': {},
    'gd': {},
    'gradient_descent': {},
    'adam': {
        'beta_1': 0.9,
        'beta_2': 0.999,
        'epsilon': 1e-08
    },
    'adadelta': {
        'rho': 0.95,
        'epsilon': 1e-08
    },
    'adagrad': {
        'initial_accumulator_value': 0.1
    },
    'adamax': {},
    'ftrl': {
        'learning_rate_power': -0.5,
        'initial_accumulator_value': 0.1,
        'l1_regularization_strength': 0.0,
        'l2_regularization_strength': 0.0
    },
    'nadam': {},
    'rmsprop': {
        'decay': 0.9,
        'momentum': 0.0,
        'epsilon': 1e-10,
        'centered': False
    }
}
default_optimizer_params_registry['stochastic_gradient_descent'] = (
    default_optimizer_params_registry['sgd']
)
default_optimizer_params_registry['gd'] = (
    default_optimizer_params_registry['sgd']
)
default_optimizer_params_registry['gradient_descent'] = (
    default_optimizer_params_registry['sgd']
)


def get_default_optimizer_params(optimizer_type):
    if optimizer_type in default_optimizer_params_registry:
        return default_optimizer_params_registry[optimizer_type]
    else:
        raise ValueError('Incorrect optimizer type: ' + optimizer_type)


def _perform_sanity_checks(model_definition):
    assert 'input_features' in model_definition, (
        'Model definition does not define any input features'
    )

    assert 'output_features' in model_definition, (
        'Model definition does not define any output features'
    )

    assert isinstance(model_definition['input_features'], list), (
        'Ludwig expects input features in a list. Check your model '
        'definition format'
    )

    assert isinstance(model_definition['output_features'], list), (
        'Ludwig expects output features in a list. Check your model '
        'definition format'
    )

    assert len(model_definition['input_features']) > 0, (
        'Model definition needs to have at least one input feature'
    )

    assert len(model_definition['output_features']) > 0, (
        'Model definition needs to have at least one output feature'
    )

    if TRAINING in model_definition:
        assert isinstance(model_definition[TRAINING], dict), (
            'There is an issue while reading the training section of the '
            'model definition. The parameters are expected to be'
            'read as a dictionary. Please check your model definition format.'
        )

    if 'preprocessing' in model_definition:
        assert isinstance(model_definition['preprocessing'], dict), (
            'There is an issue while reading the preprocessing section of the '
            'model definition. The parameters are expected to be read'
            'as a dictionary. Please check your model definition format.'
        )

    if 'combiner' in model_definition:
        assert isinstance(model_definition['combiner'], dict), (
            'There is an issue while reading the combiner section of the '
            'model definition. The parameters are expected to be read'
            'as a dictionary. Please check your model definition format.'
        )


def merge_with_defaults(model_definition):
    _perform_sanity_checks(model_definition)

    # ===== Preprocessing =====
    model_definition['preprocessing'] = merge_dict(
        default_preprocessing_parameters,
        model_definition.get('preprocessing', {})
    )

    stratify = model_definition['preprocessing']['stratify']

    if stratify is not None:
        if stratify not in [x['name'] for x in
                            model_definition['output_features']]:
            warnings.warn('Stratify is not in output features. '
                          'Expecting type to be binary or category')
        elif ([x for x in model_definition['output_features'] if
             x['name'] == stratify][0][TYPE]
                not in [BINARY, CATEGORY]):
            raise ValueError('Stratify feature must be binary or category')
    # ===== Model =====
    set_default_value(model_definition, 'combiner',
                      {'type': default_combiner_type})

    # ===== Training =====
    set_default_value(model_definition, TRAINING, default_training_params)

    for param, value in default_training_params.items():
        set_default_value(model_definition[TRAINING], param,
                          value)

    set_default_value(
        model_definition[TRAINING],
        'validation_metric',

        output_type_registry[model_definition['output_features'][0][
            TYPE]].default_validation_metric
    )

    # ===== Training Optimizer =====
    optimizer = model_definition[TRAINING]['optimizer']
    default_optimizer_params = get_default_optimizer_params(optimizer[TYPE])
    for param in default_optimizer_params:
        set_default_value(optimizer, param, default_optimizer_params[param])

    # ===== Input Features =====
    for input_feature in model_definition['input_features']:
        get_from_registry(input_feature[TYPE],
                          input_type_registry).populate_defaults(input_feature)

    # ===== Output features =====
    for output_feature in model_definition['output_features']:
        get_from_registry(output_feature['type'],
                          output_type_registry).populate_defaults(
            output_feature)

    return model_definition
