# -*- coding: utf-8 -*-
__author__ = ["chrisholder"]

import warnings
from typing import Any

import numpy as np
from numba import njit
from numba.core.errors import NumbaWarning

from sktime.distances.base import DistanceCallable, NumbaDistance
from sktime.distances.lower_bounding import resolve_bounding_matrix

# Warning occurs when using large time series (i.e. 1000x1000)
warnings.simplefilter("ignore", category=NumbaWarning)


class _LcssDistance(NumbaDistance):
    r"""Longest common subsequence (LCSS) between two time series.

    The LCSS distance for time series is based on the solution to the
    longest common subsequence problem in pattern matching [1]. The typical problem
    is to find the longest subsequence that is common to two discrete series based on
    the edit distance. This approach can be extended to consider real-valued time series
    by using a distance threshold epsilon, which defines the maximum difference
    between a pair of values that is allowed for them to be considered a match.
    LCSS finds the optimal alignment between two series by find the greatest number
    of matching pairs. The LCSS distance uses a matrix :math:'L' that records the
    sequence of matches over valid warpings. For two series :math:'a = a_1,... a_m
    and b = b_1,... b_m, L' is found by iterating over all valid windows (i.e.
    where bounding_matrix is not infinity, which by default is the constant band
    :math:'|i-j|<w*m', where :math:'w' is the window parameter value and m is series
    length), then calculating

    ::math
    if(|a_i - b_j| < espilon) \\
            &L_{i,j} \leftarrow L_{i-1,j-1}+1 \\
    else\\
            &L_{i,j} \leftarrow \max(L_{i,j-1}, L_{i-1,j})\\

    The distance is an inverse function of the final LCSS.
    ::math
    d_{LCSS}({\bf a,b}) = 1- \frac{LCSS({\bf a,b})}{m}.\]

    Note that series a and b need not be equal length.

    References
    ----------
    .. [1] D. Hirschberg, Algorithms for the longest common subsequence problem, Journal
    of the ACM 24(4), 664--675, 1977
    """

    def _distance_factory(
        self,
        x: np.ndarray,
        y: np.ndarray,
        epsilon: float = 1.0,
        window: float = None,
        itakura_max_slope: float = None,
        bounding_matrix: np.ndarray = None,
        **kwargs: Any,
    ) -> DistanceCallable:
        """Create a no_python compiled lcss distance callable.

        Series should be shape (d, m), where d is the number of dimensions, m the series
        length. Series can be different lengths.

        Parameters
        ----------
        x: np.ndarray (2d array of shape (d,m1)).
            First time series.
        y: np.ndarray (2d array of shape (d,m2)).
            Second time series.
        epsilon : float, default = 1.
            Matching threshold to determine if two subsequences are considered close
            enough to be considered 'common'.
        window: float, default = None, radius of the bounding window (if using
        Sakoe-Chiba lower bounding). Must be between 0 and 1.
        itakura_max_slope: float, defaults = None, gradient of the slope for bounding
        parallelogram (if using Itakura parallelogram lower bounding). Must be
            between 0 and 1.
        bounding_matrix: np.ndarray (2d array of shape (m1,m2)), defaults = None
            Custom bounding matrix to use. If defined then other lower_bounding params
            are ignored. The matrix should be structure so that indexes considered in
            bound should be the value 0. and indexes outside the bounding matrix should
            be infinity.
        kwargs: Any Extra kwargs.

        Returns
        -------
        Callable[[np.ndarray, np.ndarray], float]
            No_python compiled lcss distance callable.

        Raises
        ------
        ValueError
            If the input time series is not a numpy array.
            If the input time series doesn't have exactly 2 dimensions.
            If the sakoe_chiba_window_radius is not an integer.
            If the itakura_max_slope is not a float or int.
            If epsilon is not a float.
        """
        _bounding_matrix = resolve_bounding_matrix(
            x, y, window, itakura_max_slope, bounding_matrix
        )

        if not isinstance(epsilon, float):
            raise ValueError("The value of epsilon must be a float.")

        @njit(cache=True)
        def numba_lcss_distance(
            _x: np.ndarray,
            _y: np.ndarray,
        ) -> float:
            x_size = _x.shape[1]
            y_size = _y.shape[1]
            cost_matrix = _sequence_cost_matrix(_x, _y, _bounding_matrix, epsilon)
            return 1 - float(cost_matrix[x_size, y_size] / min(x_size, y_size))

        return numba_lcss_distance


@njit(cache=True)
def _sequence_cost_matrix(
    x: np.ndarray,
    y: np.ndarray,
    bounding_matrix: np.ndarray,
    epsilon: float,
):
    """Compute the lcss cost matrix between two timeseries.

    Parameters
    ----------
    x: np.ndarray (2d array), first time series.
    y: np.ndarray (2d array), second time series.
    bounding_matrix: np.ndarray (2d of size mxn where m is len(x) and n is len(y))
        Bounding matrix where the values in bound are marked by finite values and
        outside bound points are infinite values.
    epsilon : float
        Matching threshold to determine if distance between two subsequences are
        considered similar (similar if distance less than the threshold).

    Returns
    -------
    np.ndarray (2d of size mxn where m is len(x) and n is len(y))
        Lcss cost matrix between x and y.
    """
    dimensions = x.shape[0]
    x_size = x.shape[1]
    y_size = y.shape[1]
    cost_matrix = np.zeros((x_size + 1, y_size + 1))
    for i in range(1, x_size + 1):
        for j in range(1, y_size + 1):
            if np.isfinite(bounding_matrix[i - 1, j - 1]):
                curr_dist = 0
                for k in range(dimensions):
                    curr_dist += (x[k][i - 1] - y[k][j - 1]) * (
                        x[k][i - 1] - y[k][j - 1]
                    )
                curr_dist = np.sqrt(curr_dist)
                if curr_dist < epsilon:
                    cost_matrix[i, j] = 1 + cost_matrix[i - 1, j - 1]
                else:
                    cost_matrix[i, j] = max(
                        cost_matrix[i, j - 1], cost_matrix[i - 1, j]
                    )

    return cost_matrix
