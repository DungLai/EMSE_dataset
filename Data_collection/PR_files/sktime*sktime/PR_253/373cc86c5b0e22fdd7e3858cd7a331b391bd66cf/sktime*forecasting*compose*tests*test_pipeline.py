#!/usr/bin/env python3 -u
# coding: utf-8
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)

__author__ = ["Markus LÃ¶ning"]
__all__ = []

import numpy as np
from sktime.datasets import load_airline
from sktime.forecasting.compose import TransformedTargetForecaster
from sktime.forecasting.model_selection import temporal_train_test_split
from sktime.forecasting.naive import NaiveForecaster
from sktime.forecasting.trend import PolynomialTrendForecaster
from sktime.transformers.single_series.detrend import Deseasonalizer
from sktime.transformers.single_series.detrend import Detrender


def test_pipeline():
    y = load_airline()
    y_train, y_test = temporal_train_test_split(y)

    f = TransformedTargetForecaster([
        ("t1", Deseasonalizer(sp=12, model="multiplicative")),
        ("t2", Detrender(PolynomialTrendForecaster(degree=1))),
        ("f", NaiveForecaster())
    ])
    fh = np.arange(len(y_test)) + 1
    f.fit(y_train, fh)
    actual = f.predict()

    def compute_expected_y_pred(y_train, fh):
        # fitting
        yt = y_train.copy()
        t1 = Deseasonalizer(sp=12, model="multiplicative")
        yt = t1.fit_transform(yt)
        t2 = Detrender(PolynomialTrendForecaster(degree=1))
        yt = t2.fit_transform(yt)
        f = NaiveForecaster()
        f.fit(yt, fh)

        # predicting
        y_pred = f.predict()
        y_pred = t2.inverse_transform(y_pred)
        y_pred = t1.inverse_transform(y_pred)
        return y_pred

    expected = compute_expected_y_pred(y_train, fh)
    np.testing.assert_array_equal(actual, expected)
