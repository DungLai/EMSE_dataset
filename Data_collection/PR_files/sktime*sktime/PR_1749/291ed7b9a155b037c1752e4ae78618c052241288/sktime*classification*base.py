# -*- coding: utf-8 -*-
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)
"""
Abstract base class for time series classifiers.

    class name: BaseClassifier

Defining methods:
    fitting         - fit(self, X, y)
    predicting      - predict(self, X)
                    - predict_proba(self, X)

Inspection methods:
    hyper-parameter inspection  - get_params()
    fitted parameter inspection - get_fitted_params()

State:
    fitted model/strategy   - by convention, any attributes ending in "_"
    fitted state flag       - is_fitted (property)
    fitted state inspection - check_is_fitted()
"""

__all__ = [
    "BaseClassifier",
]
__author__ = ["mloning", "fkiraly", "TonyBagnall", "MatthewMiddlehurst"]

import numpy as np
import pandas as pd
import time

from sktime.base import BaseEstimator
from sktime.datatypes._panel._convert import(
    from_3d_numpy_to_nested,
    from_nested_to_3d_numpy,
)
from sktime.datatypes._panel._check import is_nested_dataframe
from sktime.utils.validation import check_n_jobs
from sktime.utils.validation.panel import (
    check_classifier_input,
    get_data_characteristics,
)


class BaseClassifier(BaseEstimator):
    """Abstract base class for time series classifiers.

    The base classifier specifies the methods and method signatures that all
    classifiers have to implement.
    """

    _tags = {
        "coerce-X-to-numpy": True,
        "coerce-X-to-pandas": False,
        "capability:multivariate": False,
        "capability:unequal_length": False,
        "capability:missing_values": False,
        "capability:train_estimate": False,
        "capability:contractable": False,
        "capability:multithreading": False,
    }

    def __init__(self):
        self.classes_ = []
        self.n_classes_ = 0
        self.fit_time_ = 0
        self._class_dictionary = {}
        self._threads_to_use = 1
        super(BaseClassifier, self).__init__()

    def fit(self, X, y):
        """Fit time series classifier to training data.

        Parameters
        ----------
        X : 2D np.array (univariate, equal length series) of shape = [n_instances,
        series_length]
            or 3D np.array (any number of dimensions, equal length series) of shape =
            [n_instances,n_dimensions,series_length]
            or pd.DataFrame with each column a dimension, each cell a pd.Series (any
            number of dimensions, equal or unequal length series)
        y : 1D np.array of shape =  [n_instances] - the class labels.

        Returns
        -------
        self :
            Reference to self.

        Notes
        -----
        Changes state by creating a fitted model that updates attributes
        ending in "_" and sets is_fitted flag to True.
        """
        start = int(round(time.time() * 1000))
        #Check the data is either numpy arrays or pandas dataframes
        #TODO: add parameters for min instances and min length
        check_classifier_input(X, y)
        #Query the data for characteristics
        missing, multivariate, unequal = get_data_characteristics(X)
        #Check this classifier can handle characteristics
        check_capabilities(self, missing, multivariate, unequal)
        #Convert data as dictated by the classifier tags
        X, y = convert_input(self, X, y)

        multithread = self.get_tag("capability:multithreading")
        if multithread:
            try:
                self._threads_to_use = check_n_jobs(self.n_jobs)
            except NameError:
                raise AttributeError(
                    "self.n_jobs must be set if capability:multithreading is True"
                )

        self.classes_ = np.unique(y)
        self.n_classes_ = self.classes_.shape[0]
        for index, classVal in enumerate(self.classes_):
            self._class_dictionary[classVal] = index

        self._fit(X, y)

        # this should happen last
        self._is_fitted = True

        fit_time_ = int(round(time.time() * 1000)) - start
        return self

    def predict(self, X) -> np.array:
        """Predicts labels for sequences in X.

        Parameters
        ----------
        X : 2D np.array (univariate, equal length series) of shape = [n_instances,
        series_length]
            or 3D np.array (any number of dimensions, equal length series) of shape =
            [n_instances,n_dimensions,series_length]
            or pd.DataFrame with each column a dimension, each cell a pd.Series (any
            number of dimensions, equal or unequal length series)

        Returns
        -------
        y : 1D np.array of shape =  [n_instances] - predicted class labels
        """
        self.check_is_fitted()

        #Check the data is either numpy arrays or pandas dataframes
        #TODO: add parameters for min instances and min length
        check_classifier_input(X)
        #Query the data for characteristics
        missing, multivariate, unequal = get_data_characteristics(X)
        #Check this classifier can handle characteristics
        check_capabilities(self, missing, multivariate, unequal)
        #Convert data as dictated by the classifier tags
        X, y = convert_input(self, X, y)

        return self._predict(X)

    def predict_proba(self, X) -> np.array:
        """Predicts labels probabilities for sequences in X.

        Parameters
        ----------
        X : 2D np.array (univariate, equal length series) of shape = [n_instances,
        series_length]
            or 3D np.array (any number of dimensions, equal length series) of shape =
            [n_instances,n_dimensions,series_length]
            or pd.DataFrame with each column a dimension, each cell a pd.Series (any
            number of dimensions, equal or unequal length series)

        Returns
        -------
        y : 2D array of shape =  [n_instances, n_classes] - estimated class
        probabilities
        """
        self.check_is_fitted()

        #Check the data is either numpy arrays or pandas dataframes
        #TODO: add parameters for min instances and min length
        check_classifier_input(X)
        #Query the data for characteristics
        missing, multivariate, unequal = get_data_characteristics(X)
        #Check this classifier can handle characteristics
        check_capabilities(self, missing, multivariate, unequal)
        #Convert data as dictated by the classifier tags
        X, y = convert_input(self, X, y)

        return self._predict_proba(X)

    def score(self, X, y) -> float:
        """Scores predicted labels against ground truth labels on X.

        Parameters
        ----------
        X : 2D np.array (univariate, equal length series) of shape = [n_instances,
        series_length]
            or 3D np.array (any number of dimensions, equal length series) of shape =
            [n_instances,n_dimensions,series_length]
            or pd.DataFrame with each column a dimension, each cell a pd.Series (any
            number of dimensions, equal or unequal length series)
        y : array-like, shape =  [n_instances] - actual class labels

        Returns
        -------
        float, accuracy score of predict(X) vs y
        """
        from sklearn.metrics import accuracy_score

        return accuracy_score(y, self.predict(X), normalize=True)

    def _fit(self, X, y):
        """Fit time series classifier to training data.

        Abstract method, must be implemented.

        Parameters
        ----------
        X : 3D np.array, array-like or sparse matrix
                of shape = [n_instances,n_dimensions,series_length]
                or shape = [n_instances,series_length]
            or pd.DataFrame with each column a dimension, each cell a pd.Series
        y : array-like, shape = [n_instances] - the class labels

        Returns
        -------
        self :
            Reference to self.

        Notes
        -----
        Changes state by creating a fitted model that updates attributes
        ending in "_" and sets is_fitted flag to True.
        """
        raise NotImplementedError(
            "_fit is a protected abstract method, it must be implemented."
        )

    def _predict(self, X) -> np.array:
        """Predicts labels for sequences in X.

        Abstract method, must be implemented.

        Parameters
        ----------
        X : 3D np.array, array-like or sparse matrix
                of shape = [n_instances,n_dimensions,series_length]
                or shape = [n_instances,series_length]
            or pd.DataFrame with each column a dimension, each cell a pd.Series

        Returns
        -------
        y : array-like, shape =  [n_instances] - predicted class labels
        """
        raise NotImplementedError(
            "_predict is a protected abstract method, it must be implemented."
        )

    def _predict_proba(self, X) -> np.ndarray:
        """Predicts labels probabilities for sequences in X.

        Default behaviour is to call _predict and set the predicted class probability
        to 1, other class probabilities to 0. Override if better estimates are
        obtainable.

        Parameters
        ----------
        X : 3D np.array, array-like or sparse matrix
                of shape = [n_instances,n_dimensions,series_length]
                or shape = [n_instances,series_length]
            or pd.DataFrame with each column a dimension, each cell a pd.Series

        Returns
        -------
        y : array-like, shape =  [n_instances, n_classes] - estimated probabilities
        of class membership.
        """
        dists = np.zeros((X.shape[0], self.n_classes_))
        preds = self._predict(X)
        for i in range(0, X.shape[0]):
            dists[i, self._class_dictionary[preds[i]]] = 1

        return dists


def check_capabilities(self, missing, multivariate, unequal):
    """Check wether this classifier can handle the data characteristics.
    Attributes
    ----------
    missing : boolean, does the data passed to fit contain missing values?
    multivariate : boolean, does the data passed to fit contain missing values?
    unequal : boolea, do the time series passed to fit have variable lengths?

    Raises
    ------
    ValueError if the capabilities in self._tags do not handle the data.

    """
    allow_multivariate = self.get_tag("capability:multivariate")
    allow_missing = self.get_tag("capability:missing_values")
    allow_unequal = self.get_tag("capability:missing_values")
    if missing and not allow_missing:
        raise ValueError("The data has missing values, this classifier cannot handle "
                         "missing values")
    if multivariate and not allow_multivariate:
        raise ValueError("The data is multivariate, this classifier cannot handle "
                         "multivariate time serries")
    if unequal and not allow_unequal:
        raise ValueError("The data has unequal length series, this classifier cannot "
                         "handle unequal length series")


def convert_input(self, X, y):
    """Convert equal length series from pandas to numpy or vice versa.

    Parameters
    ----------
    self : this classifier
    X : pd.DataFrame or np.array
        Input data

    Returns
    -------
    X : pd.DataFrame or np.array
        Checked and possibly converted input data
    """
    convert_to_numpy = self.get_tag("coerce-X-to-numpy")
    convert_to_pandas = self.get_tag("coerce-X-to-pandas")
    if convert_to_numpy and convert_to_pandas:
        raise ValueError("Tag error: cannot set both coerce-X-to-numpy and "
                         "coerce-X-to-pandas to be true.")
    # convert pd.DataFrame
    if convert_to_numpy:
        if isinstance(X, pd.DataFrame):
            X = from_nested_to_3d_numpy(X)
        if isinstance(y, pd.DataFrame):
            y = y.to_numpy()
    elif coerce_to_pandas:
        # Temporary fix to insist on 3D numpy. For univariate problems, most classifiers
        # simply convert back to 2D. This squashing should be done here, but touches a
        # lot of files, so will get this to work first.
        if isinstance(X, np.ndarray):
            if not X.ndim == 2:
                X = X.reshape(X.shape[0], 1, X.shape[1])
            X = from_3d_numpy_to_nested(X)
    return X, y
