# -*- coding: utf-8 -*-
__author__ = ["Ayushmann Seth", "Markus LÃ¶ning"]

import numpy as np
import pytest
from sklearn.model_selection import train_test_split
from sktime.transformers.panel.summarize import TSFreshFeatureExtractor
from sktime.utils.data_container import from_nested_to_2d_array
from sktime.utils._testing.panel import make_classification_problem


@pytest.mark.parametrize("default_fc_parameters", ["minimal"])
def test_tsfresh_extractor(default_fc_parameters):
    X, y = make_classification_problem()
    X_train, X_test, y_train, y_test = train_test_split(X, y)

    transformer = TSFreshFeatureExtractor(
        default_fc_parameters=default_fc_parameters, disable_progressbar=True
    )

    Xt = transformer.fit_transform(X_train, y_train)
    actual = Xt.filter(like="__mean", axis=1).values.ravel()
    expected = from_nested_to_2d_array(X_train).mean(axis=1).values

    assert expected[0] == X_train.iloc[0, 0].mean()
    np.testing.assert_allclose(actual, expected)
