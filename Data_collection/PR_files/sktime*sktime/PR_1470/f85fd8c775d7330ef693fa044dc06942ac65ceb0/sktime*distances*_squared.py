# -*- coding: utf-8 -*-
__author__ = ["chrisholder"]

from typing import Any

import numpy as np
from numba import njit

from sktime.distances.base import DistanceCallable, NumbaDistance


class _SquaredDistance(NumbaDistance):
    """Squared distance between two timeseries."""

    def _distance_factory(
        self, x: np.ndarray, y: np.ndarray, **kwargs: Any
    ) -> DistanceCallable:
        """Create a no_python compiled Squared distance callable.

        Parameters
        ----------
        x: np.ndarray (1d or 2d array)
            First timeseries.
        y: np.ndarray (1d or 2d array)
            Second timeseries.
        kwargs: Any
            Extra kwargs. For squared there are none however, this is kept for
            consistency.

        Returns
        -------
        Callable[[np.ndarray, np.ndarray], float]
            No_python compiled Squared distance callable.
        """
        return _numba_squared_distance


@njit(cache=True, fastmath=True)
def _numba_squared_distance(x: np.ndarray, y: np.ndarray) -> float:
    """Squared distance compiled to no_python.

    Parameters
    ----------
    x: np.ndarray (2d array)
        First timeseries.
    y: np.ndarray (2d array)
        Second timeseries.

    Returns
    -------
    distance: float
        Squared distance between the x and y.
    """
    dist = 0.0
    for i in range(x.shape[0]):
        for j in range(x.shape[1]):
            dist += (x[i, j] - y[i, j]) ** 2
    return dist


@njit(cache=True, fastmath=True)
def _local_squared_distance(x: np.ndarray, y: np.ndarray):
    """Compute the local squared distance.

    Parameters
    ----------
    x: np.ndarray (1d array)
        First time series
    y: np.ndarray (1d array)
        Second time series

    Returns
    -------
    float
        Squared distance between the two time series
    """
    distance = 0.0
    for i in range(x.shape[0]):
        difference = x[i] - y[i]
        distance += difference * difference
    return distance
