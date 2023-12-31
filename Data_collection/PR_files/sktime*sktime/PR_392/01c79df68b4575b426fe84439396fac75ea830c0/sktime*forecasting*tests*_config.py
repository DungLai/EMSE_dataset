#!/usr/bin/env python3 -u
# coding: utf-8

__author__ = ["Markus LÃ¶ning"]
__all__ = [
    "TEST_YS",
    "TEST_SPS",
    "TEST_ALPHAS",
    "TEST_FHS",
    "TEST_STEP_LENGTHS",
    "TEST_INS_FHS",
    "TEST_OOS_FHS",
    "TEST_WINDOW_LENGTHS",
    "SUPPORTED_INDEX_FH_COMBINATIONS",
    "INDEX_TYPE_LOOKUP"
]

import numpy as np
import pandas as pd

from sktime.utils._testing.forecasting import generate_time_series

# default parameter testing grid
TEST_WINDOW_LENGTHS = [1, 5]
TEST_STEP_LENGTHS = [1, 5]
TEST_OOS_FHS = [1, np.array([2, 5])]  # out-of-sample
TEST_INS_FHS = [
    -3,  # single in-sample
    np.array([-2, -5]),  # multiple in-sample
    0,  # last training point
    np.array([-3, 2])  # mixed in-sample and out-of-sample
]
TEST_FHS = TEST_OOS_FHS + TEST_INS_FHS
TEST_SPS = [3, 7, 12]
TEST_ALPHAS = [0.05, 0.1]
TEST_YS = [
    # zero-based index
    generate_time_series(positive=True),
    # non-zero-based index, raises warnings in statsmodels
    # generate_time_series(positive=True, non_zero_index=True),
]

# supported combinations of index and forecasting horizon types
# | index type | fh type | is_relative |
SUPPORTED_INDEX_FH_COMBINATIONS = [
    ("int", "int", True),
    ("int", "int", False),
    ("range", "int", True),
    ("range", "int", False),
    ("period", "int", True),
    ("period", "period", False),
    ("datetime", "int", True),
    ("datetime", "datetime", False)
]

INDEX_TYPE_LOOKUP = {
    "int": pd.Int64Index,
    "range": pd.RangeIndex,
    "datetime": pd.DatetimeIndex,
    "period": pd.PeriodIndex
}
