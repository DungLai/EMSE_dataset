#!/usr/bin/env python3 -u
# coding: utf-8

__author__ = ["Markus LÃ¶ning"]
__all__ = [
    "make_classification_problem",
    "make_regression_problem",
]

import numpy as np
import pandas as pd
from sklearn.utils.validation import check_random_state


def _make_series_as_features_X(y, n_columns, n_timepoints,
                               random_state=None):
    n_instances = len(y)
    rng = check_random_state(random_state)
    columns = []
    for i in range(n_columns):
        rows = []
        for j in range(n_instances):
            # we use the y value for the mean of the generated time series
            row = pd.Series(rng.normal(loc=y.iloc[j] * 10, size=n_timepoints))
            rows.append(row)
        column = pd.Series(rows)
        columns.append(column)
    return pd.DataFrame(columns).T


def make_classification_problem(n_instances=20, n_columns=1,
                                n_timepoints=20, n_classes=2,
                                random_state=None):
    rng = check_random_state(random_state)
    y = pd.Series(np.hstack([np.arange(n_classes),
                             rng.randint(0, n_classes,
                                         size=n_instances - n_classes)]))

    X = _make_series_as_features_X(y, n_columns, n_timepoints,
                                   random_state=random_state)

    return X, y


def make_regression_problem(n_instances=20, n_columns=1, n_timepoints=20,
                            random_state=None):
    rng = check_random_state(random_state)
    y = pd.Series(rng.normal(size=n_instances))

    X = _make_series_as_features_X(y, n_columns, n_timepoints,
                                   random_state=random_state)
    return X, y
