# -*- coding: utf-8 -*-
import pandas as pd

import pytest
from sktime.utils._testing.estimator_checks import _construct_instance, _make_args
from sktime.utils import all_estimators

ALL_ANNOTATORS = all_estimators(estimator_types="stream-annotator", return_names=False)


@pytest.mark.parametrize("Estimator", ALL_ANNOTATORS)
def test_output_type(Estimator):
    estimator = _construct_instance(Estimator)

    args = _make_args(estimator, "fit")
    estimator.fit(*args)
    args = _make_args(estimator, "predict")
    annotated_series = estimator.predict(*args)
    assert isinstance(annotated_series, pd.Series)
