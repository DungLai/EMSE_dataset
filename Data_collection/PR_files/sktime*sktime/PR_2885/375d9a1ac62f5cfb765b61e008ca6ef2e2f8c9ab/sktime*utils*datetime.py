#!/usr/bin/env python3 -u
# -*- coding: utf-8 -*-
"""Time format related utilities."""

__author__ = ["mloning", "xiaobenbenecho", "khrapovs"]
__all__ = []

from functools import singledispatch
from typing import Optional, Tuple, Union

import numpy as np
import pandas as pd

from sktime.datatypes import VectorizedDF
from sktime.datatypes._utilities import get_time_index
from sktime.utils.validation.series import check_time_index, is_integer_index


def _coerce_duration_to_int(
    duration: Union[int, pd.Timedelta, pd.tseries.offsets.BaseOffset, pd.Index],
    freq: str = None,
) -> Union[int, pd.Index]:
    """Coerce durations into integer representations for a given unit of duration.

    Parameters
    ----------
    duration : pd.DateOffset, pd.Timedelta, pd.TimedeltaIndex, pd.Index, int
        Duration type or collection of duration types
    freq : str
        Frequency of the above duration type.

    Returns
    -------
    ret : int
        Duration in integer values for given unit
    """
    if isinstance(duration, int):
        return duration
    elif isinstance(duration, pd.tseries.offsets.BaseOffset):
        return int(duration.n / _get_intervals_count_and_unit(freq)[0])
    elif isinstance(duration, pd.Index) and isinstance(
        duration[0], pd.tseries.offsets.BaseOffset
    ):
        count = _get_intervals_count_and_unit(freq)[0]
        return pd.Index([d.n / count for d in duration], dtype=int)
    elif isinstance(duration, (pd.Timedelta, pd.TimedeltaIndex)):
        count, unit = _get_intervals_count_and_unit(freq)
        # integer conversion only works reliably with non-ambiguous units (
        # e.g. days, seconds but not months, years)
        try:
            if isinstance(duration, pd.Timedelta):
                return int(duration / pd.Timedelta(count, unit))
            if isinstance(duration, pd.TimedeltaIndex):
                return (duration / pd.Timedelta(count, unit)).astype(int)
        except ValueError:
            raise ValueError(
                "Index type not supported. Please consider using pd.PeriodIndex."
            )
    else:
        raise TypeError("`duration` type not understood.")


def _get_intervals_count_and_unit(freq: str) -> Tuple[int, str]:
    """Extract interval count and unit from frequency string.

    Supports eg: W, 3W, W-SUN, BQS, (B)Q(S)-MAR patterns, from which we
    extract the count and the unit. See
    https://pandas.pydata.org/docs/user_guide/timeseries.html#timeseries-offset-aliases
    """
    if freq is None:
        raise ValueError("frequency is missing")
    else:
        offset = pd.tseries.frequencies.to_offset(freq)
        count, unit = offset.n, offset.base.freqstr
        return count, unit


def _get_freq(x):
    """Get unit for conversion of time deltas to integer."""
    if hasattr(x, "freqstr"):
        if x.freqstr is None:
            return None
        elif "-" in x.freqstr:
            return x.freqstr.split("-")[0]
        else:
            return x.freqstr
    else:
        return None


@singledispatch
def infer_freq(y=None) -> Optional[str]:
    """Infer frequency string from the time series object.

    Parameters
    ----------
    y : Series, Panel, or Hierarchical object, or VectorizedDF, optional (default=None)

    Returns
    -------
    str
        Frequency string inferred from the pandas index,
        or `None`, if inference fails.
    """
    return None


@infer_freq.register(pd.DataFrame)
@infer_freq.register(pd.Series)
@infer_freq.register(np.ndarray)
def _(y) -> Optional[str]:
    return _infer_freq_from_index(get_time_index(y))


@infer_freq.register(VectorizedDF)
def _(y) -> Optional[str]:
    return _infer_freq_from_index(get_time_index(y.as_list()[0]))


def _infer_freq_from_index(index: pd.Index) -> Optional[str]:
    """Infer frequency string from the pandas index.

    Parameters
    ----------
    index : pd.Index

    Returns
    -------
    str
        Frequency string inferred from the pandas index,
        or `None`, if inference fails.
    """
    if hasattr(index, "freqstr"):
        return index.freqstr
    else:
        try:
            return pd.infer_freq(index, warn=False)
        except (TypeError, ValueError):
            return None


def _shift(x, by=1):
    """Shift time point `x` by a step (`by`) given frequency of `x`.

    Parameters
    ----------
    x : pd.Period, pd.Timestamp, int
        Time point
    by : int

    Returns
    -------
    ret : pd.Period, pd.Timestamp, int
        Shifted time point
    """
    assert isinstance(x, (pd.Period, pd.Timestamp, int, np.integer)), type(x)
    assert isinstance(by, (int, np.integer)) or is_integer_index(by), type(by)
    if isinstance(x, pd.Timestamp):
        if not hasattr(x, "freq") or x.freq is None:
            raise ValueError("No `freq` information available")
        by *= x.freq
    return x + by


def _get_duration(x, y=None, coerce_to_int=False, unit=None):
    """Compute duration between the time indices.

    Parameters
    ----------
    x : pd.Index, pd.Timestamp, pd.Period, int
    y : pd.Timestamp, pd.Period, int, optional (default=None)
    coerce_to_int : bool
        If True, duration is returned as integer value for given unit
    unit : str
        Time unit

    Returns
    -------
    ret : duration type
        Duration
    """
    if y is None:
        x = check_time_index(x)
        duration = x[-1] - x[0]
    else:
        assert isinstance(x, (int, np.integer, pd.Period, pd.Timestamp))
        # check types allowing (np.integer, int) combinations to pass
        assert type(x) is type(y) or (
            isinstance(x, (np.integer, int)) and isinstance(x, (np.integer, int))
        )
        duration = x - y

    # coerce to integer result for given time unit
    if coerce_to_int and isinstance(
        x, (pd.PeriodIndex, pd.DatetimeIndex, pd.Period, pd.Timestamp)
    ):
        if unit is None:
            # try to get the unit from the data if not given
            unit = _get_freq(x)
        duration = _coerce_duration_to_int(duration, freq=unit)
    return duration
