# -*- coding: utf-8 -*-
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)
"""Fourier features for time series with long/complex seasonality."""

__author__ = ["ltsaprounis"]

import warnings
from copy import deepcopy
from typing import List, Union

import numpy as np
import pandas as pd

from sktime.transformations.base import BaseTransformer


class FourierFeatures(BaseTransformer):
    """Fourier Features for time series seasonality.

    Fourier Series terms can be used as explanatory variables for the cases of multiple
    seasonal periods and or complex / long seasonal periods [1][2]. For every seasonal
    period, sp and fourier term k pair there are 2 fourier terms sin_sp_k and cos_sp_k:
    - sin_sp_k = sin(2*pi*k*t/sp)
    - cos_sp_k = cos(2*pi*k*t/sp)

    The implementation is based on the fourier function from the R forecast package [3]

    Parameters
    ----------
    sp_list : List[Union[int, float]]
        list of seasonal periods
    fourier_terms_list : List[int]
        list of number of fourier terms (K) for each seasonal period.
        Each K matches to the sp (seasonal period) of the sp_list.
        For example, if sp_list = [7, 365] and fourier_terms_list = [3, 9], the seasonal
        frequency of 7 will have 3 fourier terms and the seasonal frequency of 365
        will have 9 fourier terms.

    References
    ----------
    .. [1] Hyndsight - Forecasting with long seasonal periods:
        https://robjhyndman.com/hyndsight/longseasonality/
    .. [2] Hyndman, R.J., & Athanasopoulos, G. (2021) Forecasting: principles and
        practice, 3rd edition, OTexts: Melbourne, Australia. OTexts.com/fpp3.
        Accessed on August 14th 2022.
    .. [3] https://pkg.robjhyndman.com/forecast/reference/fourier.html

    Examples
    --------
    >>> from sktime.transformations.series.fourier import FourierFeatures
    >>> from sktime.datasets import load_airline
    >>> y = load_airline()
    >>> transformer = FourierFeatures(sp_list=[12], fourier_terms_list=[4])
    >>> y_hat = transformer.fit_transform(y)
    """

    _tags = {
        "scitype:transform-input": "Series",
        # what is the scitype of X: Series, or Panel
        "scitype:transform-output": "Series",
        # what scitype is returned: Primitives, Series, Panel
        "scitype:transform-labels": "None",
        # what is the scitype of y: None (not needed), Primitives, Series, Panel
        "scitype:instancewise": True,  # is this an instance-wise transform?
        "capability:inverse_transform": False,  # can the transformer inverse transform?
        "univariate-only": False,  # can the transformer handle multivariate X?
        "X_inner_mtype": "pd.DataFrame",  # which mtypes do _fit/_predict support for X?
        # this can be a Panel mtype even if transform-input is Series, vectorized
        "y_inner_mtype": "None",  # which mtypes do _fit/_predict support for y?
        "requires_y": False,  # does y need to be passed in fit?
        "enforce_index_type": pd.PeriodIndex,  # index type that needs to be enforced
        # in X/y
        "fit_is_empty": False,  # is fit empty and can be skipped? Yes = True
        "X-y-must-have-same-index": False,  # can estimator handle different X/y index?
        "transform-returns-same-time-index": True,
        # does transform return have the same time index as input X
        "skip-inverse-transform": True,  # is inverse-transform skipped when called?
        "capability:unequal_length": False,
        # can the transformer handle unequal length time series (if passed Panel)?
        "capability:unequal_length:removes": False,
        # is transform result always guaranteed to be equal length (and series)?
        #   not relevant for transformers that return Primitives in transform-output
        "handles-missing-data": False,  # can estimator handle missing data?
        # todo: rename to capability:missing_values
        "capability:missing_values:removes": False,
        # is transform result always guaranteed to contain no missing values?
        "python_version": None,  # PEP 440 python version specifier to limit versions
    }

    def __init__(self, sp_list: List[Union[int, float]], fourier_terms_list: List[int]):
        self.sp_list = sp_list
        self.fourier_terms_list = fourier_terms_list

        if len(self.sp_list) != len(self.fourier_terms_list):
            raise ValueError(
                "In FourierFeatures the length of the sp_list needs to be equal "
                "to the length of fourier_terms_list."
            )

        if np.any(np.array(self.sp_list) / np.array(self.fourier_terms_list) < 1):
            raise ValueError(
                "In FourierFeatures the number of each element of fourier_terms_list"
                "needs to be lower from the corresponding element of the sp_list"
            )

        super(FourierFeatures, self).__init__()

    def _fit(self, X, y=None):
        """Fit transformer to X and y.

        private _fit containing the core logic, called from fit

        Parameters
        ----------
        X : Series or Panel of mtype X_inner_mtype
            if X_inner_mtype is list, _fit must support all types in it
            Data to fit transform to
        y : Series or Panel of mtype y_inner_mtype, default=None
            Additional data, e.g., labels for transformation

        Returns
        -------
        self: reference to self
        """
        # Create the sp, k pairs
        # Don't add pairs where the coefficient k/sp already exists
        self.sp_k_pairs_list_ = []
        coefficient_list = []
        for i, sp in enumerate(self.sp_list):
            for k in range(1, self.fourier_terms_list[i] + 1):
                coef = k / sp
                if coef not in coefficient_list:
                    coefficient_list.append(coef)
                    self.sp_k_pairs_list_.append((sp, k))
                else:
                    warnings.warn(
                        f"The terms sin_{sp}_{k} and cos_{sp}_{k} from FourierFeatures "
                        "will be skipped because the resulting coefficient already "
                        "exists from other seasonal period, fourier term pairs."
                    )

        # store the integer form of the minimum date in the prediod index
        # this is used to make sure that time t is calculated with reference to
        # the data passed on fit
        self.min_t_ = np.min(X.index.astype(int))

        return self

    def _transform(self, X, y=None):
        """Transform X and return a transformed version.

        private _transform containing core logic, called from transform

        Parameters
        ----------
        X : Series or Panel of mtype X_inner_mtype
            if X_inner_mtype is list, _transform must support all types in it
            Data to be transformed
        y : Series or Panel of mtype y_inner_mtype, default=None
            Additional data, e.g., labels for transformation

        Returns
        -------
        transformed version of X
        """
        X_transformed = deepcopy(X)
        # get the integer form of the PeriodIndex
        int_index = X_transformed.index.astype(int) - self.min_t_

        for sp_k in self.sp_k_pairs_list_:
            sp = sp_k[0]
            k = sp_k[1]

            X_transformed[f"sin_{sp}_{k}"] = np.sin(int_index * 2 * k * np.pi / sp)
            X_transformed[f"cos_{sp}_{k}"] = np.cos(int_index * 2 * k * np.pi / sp)

        return X_transformed

    @classmethod
    def get_test_params(cls, parameter_set="default"):
        """Return testing parameter settings for the estimator.

        Parameters
        ----------
        parameter_set : str, default="default"
            Name of the set of test parameters to return, for use in tests. If no
            special parameters are defined for a value, will return `"default"` set.
            There are currently no reserved values for transformers.

        Returns
        -------
        params : dict or list of dict, default = {}
            Parameters to create testing instances of the class
            Each dict are parameters to construct an "interesting" test instance, i.e.,
            `MyClass(**params)` or `MyClass(**params[i])` creates a valid test instance.
            `create_test_instance` uses the first (or only) dictionary in `params`
        """
        params = [
            {"sp_list": [12], "fourier_terms_list": [4]},
            {"sp_list": [12, 6.2], "fourier_terms_list": [3, 4]},
        ]
        return params
