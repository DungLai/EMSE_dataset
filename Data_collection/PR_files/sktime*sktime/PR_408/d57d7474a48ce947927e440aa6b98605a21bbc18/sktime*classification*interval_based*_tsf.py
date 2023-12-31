# -*- coding: utf-8 -*-
""" Time Series Forest Classifier (TSF).
Implementation of Deng's Time Series Forest, with minor changes
"""

__author__ = ["Tony Bagnall"]
__all__ = ["TimeSeriesForest"]

import math

import numpy as np
from joblib import Parallel
from joblib import delayed
from sklearn.base import clone
from sklearn.ensemble._base import _set_random_states
from sklearn.ensemble._forest import ForestClassifier
from sklearn.ensemble._forest import MAX_INT
from sklearn.tree import DecisionTreeClassifier
from sklearn.utils.multiclass import class_distribution
from sklearn.utils.validation import check_random_state
from sktime.classification.base import BaseClassifier
from sktime.utils.data_container import tabularize
from sktime.utils.validation.series_as_features import check_X
from sktime.utils.validation.series_as_features import check_X_y


def _lsq_fit(Y):
    """Find the slope for each series (row) of Y
    Parameters
    ----------
    Y: array of shape = [n_samps, interval_size]

    Returns
    ----------
    slope: array of shape = [n_samps]

    """
    x = np.arange(Y.shape[1]) + 1
    slope = (np.mean(x * Y, axis=1) - np.mean(x) * np.mean(Y, axis=1)) / (
        (x * x).mean() - x.mean() ** 2
    )
    return slope


def _transform(X, intervals):
    """
    Compute the mean, standard deviation and slope for given intervals
    of input data X.
    """
    n_instances, _ = X.shape
    n_intervals, _ = intervals.shape
    transformed_x = np.empty(shape=(3 * n_intervals, n_instances), dtype=np.float32)
    for j in range(n_intervals):
        X_slice = X[:, intervals[j][0]: intervals[j][1]]
        means = np.mean(X_slice, axis=1)
        std_dev = np.std(X_slice, axis=1)
        slope = _lsq_fit(X_slice)
        transformed_x[3 * j] = means
        transformed_x[3 * j + 1] = std_dev
        transformed_x[3 * j + 2] = slope

    return transformed_x.T


def _get_intervals(n_intervals, min_interval, series_length, random_state=None):
    """
    Generate random intervals for given parameters.
    """
    rng = check_random_state(random_state)
    intervals = np.zeros((n_intervals, 2), dtype=int)
    for j in range(n_intervals):
        intervals[j][0] = rng.randint(series_length - min_interval)
        length = rng.randint(series_length - intervals[j][0] - 1)
        if length < min_interval:
            length = min_interval
        intervals[j][1] = intervals[j][0] + length
    return intervals


def _fit_estimator(X, y, base_estimator, n_intervals, min_interval, random_state=None):
    """
    Fit an estimator - a clone of base_estimator - on input data (X, y)
    transformed using the randomly generated intervals.
    """

    estimator = clone(base_estimator)
    if random_state is not None:
        _set_random_states(estimator, random_state)

    _, series_length = X.shape
    intervals = _get_intervals(n_intervals, min_interval, series_length, random_state)
    transformed_x = _transform(X, intervals)

    estimator.fit(transformed_x, y)

    return estimator, intervals


def _predict_proba_for_estimator(X, estimator, intervals):
    """
    Find probability estimates for each class for all cases in X using
    given estimator and intervals.
    """
    transformed_x = _transform(X, intervals)
    return estimator.predict_proba(transformed_x)


class TimeSeriesForest(ForestClassifier, BaseClassifier):
    """Time-Series Forest Classifier.

    TimeSeriesForest: Implementation of Deng's Time Series Forest,
    with minor changes
    @article
    {deng13forest,
     author = {H.Deng and G.Runger and E.Tuv and M.Vladimir},
              title = {A time series forest for classification and feature
              extraction},
    journal = {Information Sciences},
    volume = {239},
    year = {2013}

    Overview: Input n series length m
    for each tree
        sample sqrt(m) intervals
        find mean, sd and slope for each interval, concatenate to form new
        data set
        build decision tree on new data set
    ensemble the trees with averaged probability estimates

    This implementation deviates from the original in minor ways. It samples
    intervals with replacement and
    does not use the splitting criteria tiny refinement described in
    deng13forest. This is an intentionally
    stripped down, non configurable version for use as a hive-cote
    component. For a configurable tree based
    ensemble, see sktime.classifiers.ensemble.TimeSeriesForestClassifier

    TO DO: handle missing values, unequal length series and multivariate
    problems

    Parameters
    ----------
    n_estimators         : int, ensemble size, optional (default = 200)
    random_state    : int, seed for random, optional (default to no seed,
    I think!)
    min_interval    : int, minimum width of an interval, optional (default
    to 3)
    n_jobs          : int, optional (default=1)
        The number of jobs to run in parallel for both `fit` and `predict`.
        ``-1`` means using all processors.

    Attributes
    ----------
    n_classes    : int, extracted from the data
    num_atts     : int, extracted from the data
    n_intervals  : int, sqrt(num_atts)
    classifiers    : array of shape = [n_estimators] of DecisionTree
    classifiers
    intervals      : array of shape = [n_estimators][n_intervals][2] stores
    indexes of all start and end points for all classifiers
    dim_to_use     : int, the column of the panda passed to use (can be
    passed a multidimensional problem, but will only use one)

    """

    def __init__(
        self,
        random_state=None,
        min_interval=3,
        n_estimators=200,
        n_jobs=1,
    ):
        super(TimeSeriesForest, self).__init__(
            base_estimator=DecisionTreeClassifier(criterion="entropy"),
            n_estimators=n_estimators,
        )

        self.random_state = random_state
        self.n_estimators = n_estimators
        self.min_interval = min_interval
        self.n_jobs = n_jobs
        # The following set in method fit
        self.n_classes = 0
        self.series_length = 0
        self.n_intervals = 0
        self.classifiers = []
        self.intervals = []
        self.classes_ = []

        # We need to add is-fitted state when inheriting from scikit-learn
        self._is_fitted = False

    def fit(self, X, y):
        """Build a forest of trees from the training set (X, y) using random
        intervals and summary features
        Parameters
        ----------
        X : array-like or sparse matrix of shape = [n_instances,
        series_length] or shape = [n_instances,n_columns]
            The training input samples.  If a Pandas data frame is passed it
            must have a single column (i.e. univariate
            classification. RISE has no bespoke method for multivariate
            classification as yet.
        y : array-like, shape =  [n_instances]    The class labels.

        Returns
        -------
        self : object
        """
        X, y = check_X_y(X, y, enforce_univariate=True)
        X = tabularize(X, return_array=True)
        _, self.series_length = X.shape

        rng = check_random_state(self.random_state)

        self.n_classes = np.unique(y).shape[0]

        self.classes_ = class_distribution(np.asarray(y).reshape(-1, 1))[0][0]
        self.n_intervals = int(math.sqrt(self.series_length))
        if self.n_intervals == 0:
            self.n_intervals = 1
        if self.series_length < self.min_interval:
            self.min_interval = self.series_length

        self.classifiers = []
        self.intervals = []

        for estimator, intervals in Parallel(n_jobs=self.n_jobs)(
            delayed(_fit_estimator)(
                X,
                y,
                self.base_estimator,
                self.n_intervals,
                self.min_interval,
                rng.randint(MAX_INT),
            )
            for _ in range(self.n_estimators)
        ):
            self.classifiers.append(estimator)
            self.intervals.append(intervals)

        self._is_fitted = True
        return self

    def predict(self, X):
        """
        Find predictions for all cases in X. Built on top of predict_proba
        Parameters
        ----------
        X : The training input samples. array-like or pandas data frame.
        If a Pandas data frame is passed, a check is performed that it only
        has one column.
        If not, an exception is thrown, since this classifier does not yet have
        multivariate capability.

        Returns
        -------
        output : array of shape = [n_test_instances]
        """
        proba = self.predict_proba(X)
        return np.asarray([self.classes_[np.argmax(prob)] for prob in proba])

    def predict_proba(self, X):
        """
        Find probability estimates for each class for all cases in X.
        Parameters
        ----------
        X : The training input samples. array-like or sparse matrix of shape
        = [n_test_instances, series_length]
            If a Pandas data frame is passed (sktime format) a check is
            performed that it only has one column.
            If not, an exception is thrown, since this classifier does not
            yet have
            multivariate capability.

        Local variables
        ----------
        n_test_instances     : int, number of cases to classify
        series_length    : int, number of attributes in X, must match
        _num_atts determined in fit

        Returns
        -------
        output : array of shape = [n_test_instances, num_classes] of
        probabilities
        """
        self.check_is_fitted()
        X = check_X(X, enforce_univariate=True)
        X = tabularize(X, return_array=True)

        _, series_length = X.shape
        if series_length != self.series_length:
            raise TypeError(
                " ERROR number of attributes in the train does not match "
                "that in the test data"
            )
        sums = np.zeros((X.shape[0], self.n_classes), dtype=np.float64)

        for proba in Parallel(n_jobs=self.n_jobs)(
            delayed(_predict_proba_for_estimator)(
                X, self.classifiers[i], self.intervals[i]
            )
            for i in range(self.n_estimators)
        ):
            sums += proba

        output = sums / (np.ones(self.n_classes) * self.n_estimators)
        return output
