# SPDX-License-Identifier: Apache-2.0

from ..common._registration import register_shape_calculator
from ..common.shape_calculator import (
    _calculate_linear_classifier_output_shapes)


register_shape_calculator(
    'SklearnVotingClassifier',
    lambda op: _calculate_linear_classifier_output_shapes(
        op, enable_type_checking=False))
