#!/usr/bin/env python3 -u
# coding: utf-8

__author__ = ["Markus LÃ¶ning"]
__all__ = []

import numpy as np
import pytest
from sktime.forecasting.tests import TEST_SPS
from sktime.transformers.detrend import Deseasonaliser
from sktime.utils.testing.forecasting import make_forecasting_problem
from statsmodels.tsa.seasonal import seasonal_decompose

MODELS = ["additive", "multiplicative"]

y_train, y_test = make_forecasting_problem()


@pytest.mark.parametrize("sp", TEST_SPS)
def test_deseasonalised_values(sp):
    t = Deseasonaliser(sp=sp)
    t.fit(y_train)
    a = t.transform(y_train)

    r = seasonal_decompose(y_train, period=sp)
    b = y_train - r.seasonal
    np.testing.assert_array_equal(a.values, b.values)


@pytest.mark.parametrize("sp", TEST_SPS)
@pytest.mark.parametrize("model", MODELS)
def test_transform_time_index(sp, model):
    t = Deseasonaliser(sp=sp, model=model)
    t.fit(y_train)
    yt = t.transform(y_test)
    np.testing.assert_array_equal(yt.index, y_test.index)


@pytest.mark.parametrize("sp", TEST_SPS)
@pytest.mark.parametrize("model", MODELS)
def test_inverse_transform_time_index(sp, model):
    t = Deseasonaliser(sp=sp, model=model)
    t.fit(y_train)
    yit = t.inverse_transform(y_test)
    np.testing.assert_array_equal(yit.index, y_test.index)


@pytest.mark.parametrize("sp", TEST_SPS)
@pytest.mark.parametrize("model", MODELS)
def test_transform_inverse_transform_equivalence(sp, model):
    t = Deseasonaliser(sp=sp, model=model)
    t.fit(y_train)
    yit = t.inverse_transform(t.transform(y_train))
    np.testing.assert_array_equal(y_train.index, yit.index)
    np.testing.assert_almost_equal(y_train.values, yit.values)
