# -*- coding: utf-8 -*-
__author__ = ["chrisholder", "TonyBagnall"]

from typing import Callable

import numpy as np


def mean_average(X: np.ndarray) -> np.ndarray:
    """Compute the mean average of time series.

    Parameters
    ----------
    X : np.ndarray (3d array of shape (n_instances, n_dimensions, series_length))
        Time series instances compute average from.

    Returns
    -------
    np.ndarray (2d array of shape (n_dimensions, series_length)
        The time series that is the mean.
    """
    return X.mean(axis=0)


_AVERAGE_DICT = {"mean": mean_average}


def resolve_average_callable(
    averaging_method: [str, Callable[[np.ndarray], np.ndarray]]
) -> Callable[[np.ndarray], np.ndarray]:
    """Resolve a string or callable to a averaging callable.

    Parameters
    ----------
    averaging_method: str or Callable, defaults = 'mean'
        Averaging method to compute the average of a cluster. Any of the following
        strings are valid: ['mean']. If a Callable is provided must take the form
        Callable[[np.ndarray], np.ndarray].

    Returns
    -------
    Callable[[np.ndarray], np.ndarray]
        Averaging method based on params.
    """
    if isinstance(averaging_method, str):
        if averaging_method not in _AVERAGE_DICT:
            raise ValueError(
                "averaging_method string is invalid. Please use one of the" "following",
                _AVERAGE_DICT.keys(),
            )
        return _AVERAGE_DICT[averaging_method]

    return averaging_method