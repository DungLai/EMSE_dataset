# -*- coding: utf-8 -*-
__author__ = ["chrisholder"]

from typing import Any, Union

import numpy as np
from numba import njit

from sktime.distances._euclidean import _local_euclidean_distance
from sktime.distances.base import DistanceCallable, NumbaDistance
from sktime.distances.lower_bounding import LowerBounding, resolve_bounding_matrix


class _EdrDistance(NumbaDistance):
    """Edit distance for real sequences (edr) between two timeseries."""

    def _distance_factory(
        self,
        x: np.ndarray,
        y: np.ndarray,
        lower_bounding: Union[LowerBounding, int] = LowerBounding.NO_BOUNDING,
        window: int = 2,
        itakura_max_slope: float = 2.0,
        bounding_matrix: np.ndarray = None,
        epsilon: float = None,
        **kwargs: Any
    ) -> DistanceCallable:
        """Create a no_python compiled edr distance callable.

        Parameters
        ----------
        x: np.ndarray (2d array)
            First timeseries.
        y: np.ndarray (2d array)
            Second timeseries.
        lower_bounding: LowerBounding or int, defaults = LowerBounding.NO_BOUNDING
            Lower bounding technique to use.
            If LowerBounding enum provided, the following are valid:
                LowerBounding.NO_BOUNDING - No bounding
                LowerBounding.SAKOE_CHIBA - Sakoe chiba
                LowerBounding.ITAKURA_PARALLELOGRAM - Itakura parallelogram
            If int value provided, the following are valid:
                1 - No bounding
                2 - Sakoe chiba
                3 - Itakura parallelogram
        window: int, defaults = 2
            Integer that is the radius of the sakoe chiba window (if using Sakoe-Chiba
            lower bounding).
        itakura_max_slope: float, defaults = 2.
            Gradient of the slope for itakura parallelogram (if using Itakura
            Parallelogram lower bounding).
        bounding_matrix: np.ndarray (2d array)
            Custom bounding matrix to use. If defined then other lower_bounding params
            are ignored. The matrix should be structure so that indexes considered in
            bound should be the value 0. and indexes outside the bounding matrix should
            be infinity.
        epsilon : float, defaults = None
            Matching threshold to determine if two subsequences are considered close
            enough to be considered 'common'. If not specified as per the original paper
            epsilon is set to a quarter of the maximum standard deviation.
        kwargs: Any
            Extra arguments for custom distance should be put in the kwargs. See the
            documentation for the distance for kwargs.

        Returns
        -------
        Callable[[np.ndarray, np.ndarray], float]
            No_python compiled edr distance callable.

        Raises
        ------
        ValueError
            If the input timeseries is not a numpy array.
            If the input timeseries doesn't have exactly 2 dimensions.
            If the sakoe_chiba_window_radius is not an integer.
            If the itakura_max_slope is not a float or int.
            If epsilon is not a float.
        """
        _bounding_matrix = resolve_bounding_matrix(
            x, y, lower_bounding, window, itakura_max_slope, bounding_matrix
        )

        if epsilon is not None and not isinstance(epsilon, float):
            raise ValueError("The value of epsilon must be a float.")

        @njit(cache=True, fastmath=True)
        def numba_edr_distance(_x: np.ndarray, _y: np.ndarray) -> float:
            if np.array_equal(_x, _y):
                return 0.0
            if epsilon is None:
                _epsilon = max(np.std(x), np.std(y)) / 4
            else:
                _epsilon = epsilon
            cost_matrix = _edr_cost_matrix(x, y, _bounding_matrix, _epsilon)
            return float(cost_matrix[-1, -1] / max(x.shape[0], y.shape[0]))

        return numba_edr_distance


@njit(cache=True, fastmath=True)
def _edr_cost_matrix(
    x: np.ndarray,
    y: np.ndarray,
    bounding_matrix: np.ndarray,
    epsilon: float,
):
    """Compute the edr cost matrix between two timeseries.

    Parameters
    ----------
    x: np.ndarray (2d array)
        First timeseries.
    y: np.ndarray (2d array)
        Second timeseries.
    bounding_matrix: np.ndarray (2d of size mxn where m is len(x) and n is len(y))
        Bounding matrix where the values in bound are marked by finite values and
        outside bound points are infinite values.
    epsilon : float
        Matching threshold to determine if distance between two subsequences are
        considered similar (similar if distance less than the threshold).

    Returns
    -------
    np.ndarray (2d of size mxn where m is len(x) and n is len(y))
        Edr cost matrix between x and y.
    """
    x_size = x.shape[0]
    y_size = y.shape[0]
    cost_matrix = np.zeros((x_size + 1, y_size + 1))

    for i in range(1, x_size + 1):
        for j in range(1, y_size + 1):
            if np.isfinite(bounding_matrix[i - 1, j - 1]):
                curr_dist = _local_euclidean_distance(x[i - 1], y[j - 1])
                if curr_dist < epsilon:
                    cost = 0
                else:
                    cost = 1
                cost_matrix[i, j] = min(
                    cost_matrix[i - 1, j - 1] + cost,
                    cost_matrix[i - 1, j] + 1,
                    cost_matrix[i, j - 1] + 1,
                )
    return cost_matrix[1:, 1:]
