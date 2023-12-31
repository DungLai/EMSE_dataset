#!/usr/bin/env python3 -u
# coding: utf-8
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)

__author__ = ["Markus LÃ¶ning"]

import numpy as np
from scipy.stats import boxcox
from sklearn.preprocessing import PowerTransformer
from sktime.datasets import load_airline
from sktime.transformers.single_series.adapt import \
    SingleSeriesTransformAdaptor


def test_boxcox_transform():
    y = load_airline()
    t = SingleSeriesTransformAdaptor(
        PowerTransformer(method="box-cox", standardize=False)
    )
    actual = t.fit_transform(y)

    expected, _ = boxcox(
        np.asarray(y))  # returns fitted lambda as second output
    np.testing.assert_array_equal(actual, expected)
