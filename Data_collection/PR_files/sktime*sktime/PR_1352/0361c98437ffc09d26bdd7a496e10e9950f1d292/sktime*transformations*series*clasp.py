# -*- coding: utf-8 -*-

__author__ = ["Arik Ermshaus, Patrick SchÃ¤fer"]
__all__ = ["ClaSPTransformer"]

import numpy as np

# import numpy.fft as fft
import pandas as pd

from numba import njit

from sktime.transformations.base import _SeriesToSeriesTransformer
from sktime.utils.validation.series import check_series
from sktime.transformations.panel.matrix_profile import _sliding_dot_products


def _sliding_window(a, window):
    """
    the sliding windows for a time series and a window size
    :param a:
    :param window:
    :return:
    """
    shape = a.shape[:-1] + (a.shape[-1] - window + 1, window)
    strides = a.strides + (a.strides[-1],)
    return np.lib.stride_tricks.as_strided(a, shape=shape, strides=strides)


""" using the implementation in matrix_profile for now
def _sliding_dot_product(query, ts):
    ts_add = 0
    if n % 2 == 1:
        ts = np.insert(ts, 0, 0)
        ts_add = 1

    q_add = 0
    if m % 2 == 1:
        query = np.insert(query, 0, 0)
        q_add = 1

    query = query[::-1]
    query = np.pad(query, (0, n - m + ts_add - q_add), "constant")
    trim = m - 1 + ts_add
    dot_product = fft.irfft(fft.rfft(ts) * fft.rfft(query))
    return dot_product[trim:]
"""


def _sliding_mean_std(TS, m):
    """
    the sliding mean and std for a time series and a window size
    :param TS:
    :param m:
    :return:
    """
    s = np.insert(np.cumsum(TS), 0, 0)
    sSq = np.insert(np.cumsum(TS ** 2), 0, 0)
    segSum = s[m:] - s[:-m]
    segSumSq = sSq[m:] - sSq[:-m]
    movmean = segSum / m
    movstd = np.sqrt(segSumSq / m - (segSum / m) ** 2)
    return [movmean, movstd]


def _compute_distances_iterative(TS, m, k):
    """
    kNN indices with dot-product / no-loops for a time series,
    a window size and k neighbours
    :param TS:
    :param m:
    :param k:
    :return:
    """
    length = len(TS) - m + 1
    knns = np.zeros(shape=(length, k), dtype=np.int64)

    dot_prev = None
    means, stds = _sliding_mean_std(TS, m)

    for order in range(0, length):
        # first iteration O(n log n)
        if order == 0:
            # dot_first = _sliding_dot_product(TS[:m], TS)
            dot_first = _sliding_dot_products(TS[:m], TS, len(TS[:m]), len(TS))
            dot_rolled = dot_first
        # O(1) further operations
        else:
            dot_rolled = (
                np.roll(dot_prev, 1)
                + TS[order + m - 1] * TS[m - 1 : length + m]
                - TS[order - 1] * np.roll(TS[:length], 1)
            )
            dot_rolled[0] = dot_first[order]

        x_mean = means[order]
        x_std = stds[order]

        dist = 2 * m * (1 - (dot_rolled - m * means * x_mean) / (m * stds * x_std))

        # self-join: exclusion zone
        trivialMatchRange = (
            int(max(0, order - np.round(m / 2, 0))),
            int(min(order + np.round(m / 2 + 1, 0), length)),
        )
        dist[trivialMatchRange[0] : trivialMatchRange[1]] = np.inf

        idx = np.argpartition(dist, k)

        knns[order, :] = idx[:k]
        dot_prev = dot_rolled

    return knns


@njit(fastmath=True, cache=True)
def _calc_knn_labels(knn_mask, split_idx, window_size):
    """
    kNN indices relabeling at a given split index
    :param knn_mask:
    :param split_idx:
    :param window_size:
    :return:
    """
    k_neighbours, n_timepoints = knn_mask.shape

    # create hypothetical labels
    y_true = np.concatenate(
        (
            np.zeros(split_idx, dtype=np.int64),
            np.ones(n_timepoints - split_idx, dtype=np.int64),
        )
    )

    knn_mask_labels = np.zeros(shape=(k_neighbours, n_timepoints), dtype=np.int64)

    # relabel the kNN indices
    for i_neighbor in range(k_neighbours):
        neighbours = knn_mask[i_neighbor]
        knn_mask_labels[i_neighbor] = y_true[neighbours]

    # compute kNN prediction
    ones = np.sum(knn_mask_labels, axis=0)
    zeros = k_neighbours - ones
    y_pred = np.asarray(ones > zeros, dtype=np.int64)

    # apply exclusion zone at split point
    exclusion_zone = np.arange(split_idx - window_size, split_idx)
    y_pred[exclusion_zone] = np.ones(window_size, dtype=np.int64)

    return y_true, y_pred


@njit(fastmath=True, cache=True)
def _roc_auc_score(y_score, y_true):
    """roc-auc score calculation

    :param y_score:
    :param y_true:
    :return:
    """
    # make y_true a boolean vector
    y_true = y_true == 1

    # sort scores and corresponding truth values (y_true is sorted by design)
    desc_score_indices = np.arange(y_score.shape[0])[::-1]

    y_score = y_score[desc_score_indices]
    y_true = y_true[desc_score_indices]

    # y_score typically has many tied values. Here we extract
    # the indices associated with the distinct values. We also
    # concatenate a value for the end of the curve.
    distinct_value_indices = np.where(np.diff(y_score))[0]
    threshold_idxs = np.concatenate(
        (distinct_value_indices, np.array([y_true.size - 1]))
    )

    # accumulate the true positives with decreasing threshold
    tps = np.cumsum(y_true)[threshold_idxs]
    fps = 1 + threshold_idxs - tps

    tps = np.concatenate((np.array([0]), tps))
    fps = np.concatenate((np.array([0]), fps))

    if fps[-1] <= 0 or tps[-1] <= 0:
        return np.nan

    fpr = fps / fps[-1]
    tpr = tps / tps[-1]

    if fpr.shape[0] < 2:
        return np.nan

    direction = 1
    dx = np.diff(fpr)

    if np.any(dx < 0):
        if np.all(dx <= 0):
            direction = -1
        else:
            return np.nan

    area = direction * np.trapz(tpr, fpr)
    return area


@njit(fastmath=True, cache=True)
def _calc_profile(window_size, knn_mask, score, offset):
    """clasp profile calculation for the kNN indices and a score

    :param window_size:
    :param knn_mask:
    :param score:
    :param offset:
    :return:
    """
    n_timepoints = knn_mask.shape[1]
    profile = np.full(shape=n_timepoints, fill_value=np.nan, dtype=np.float64)

    for split_idx in range(offset, n_timepoints - offset):
        y_true, y_pred = _calc_knn_labels(knn_mask, split_idx, window_size)

        # try:
        profile[split_idx] = score(y_true, y_pred)
        # except:
        # roc_auc_score fails if y_true only has one class,
        # may (and does) happen in principal
        #    pass

    return profile


def clasp(
    time_series,
    window_size,
    k_neighbours=3,
    score=_roc_auc_score,
    interpolate=True,
    offset=0.05,
):
    """
    clasp calculation for a time series and a window size

    :param time_series:
    :param window_size:
    :param k_neighbours:
    :param score:
    :param interpolate:
    :param offset:
    :return:
    """
    knn_mask = _compute_distances_iterative(time_series, window_size, k_neighbours).T

    n_timepoints = knn_mask.shape[1]
    offset = np.int64(n_timepoints * offset)

    profile = _calc_profile(window_size, knn_mask, score, offset)

    if interpolate is True:
        profile = pd.Series(profile).interpolate(limit_direction="both").to_numpy()
    return profile, knn_mask


class ClaSPTransformer(_SeriesToSeriesTransformer):
    """ClaSP (Classification Score Profile) Transformer, as described in

    @inproceedings{clasp2021,
      title={ClaSP - Time Series Segmentation},
      author={Sch"afer, Patrick and Ermshaus, Arik and Leser, Ulf},
      booktitle={CIKM},
      year={2021}
    }

    Overview:

    Implementation of the Classification Score Profile of a time series.

    Parameters
    ----------
    window_size:         int, default = 8
        size of window for sliding.

    """

    _tags = {"univariate-only": True, "fit-in-transform": True}  # for unit test cases

    def __init__(self, window_length=8):
        self.window_length = window_length
        self.knn_mask = None
        super(ClaSPTransformer, self).__init__()

    def transform(self, X, y=None):
        """
        Takes as input a single time series dataset and returns the
        Classification Score profile for that single time series.

        Parameters
        ----------
        X: pandas.Series
           A single pandas series or a numpy array

        Returns
        -------
        Xt: pandas.Series
            ClaSP of the single time series as output
            with length as (n-window_length+1)
        """

        # No need to fit
        # self.check_is_fitted()

        X = check_series(X, enforce_univariate=True, allow_numpy=True)
        Xt, self.knn_mask = clasp(X.to_numpy(), self.window_length)

        return pd.Series(Xt)
