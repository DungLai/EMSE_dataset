#!/usr/bin/env python3 -u
# -*- coding: utf-8 -*-
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)

__author__ = ["Markus LÃ¶ning", "Martin Walter"]
__all__ = ["TransformedTargetForecaster", "ForecastingPipeline"]

from sklearn.base import clone

from sktime.base import _HeterogenousMetaEstimator
from sktime.forecasting.base._base import BaseForecaster
from sktime.forecasting.base._base import DEFAULT_ALPHA
from sktime.forecasting.base._sktime import _OptionalForecastingHorizonMixin
from sktime.forecasting.base._sktime import _SktimeForecaster
from sktime.transformations.base import _SeriesToSeriesTransformer
from sktime.utils.validation.forecasting import check_y_X, check_y, check_X
from sktime.utils.validation.series import check_series
from sktime.utils import _has_tag


class _Pipeline(
    _OptionalForecastingHorizonMixin,
    _SktimeForecaster,
    _HeterogenousMetaEstimator,
    _SeriesToSeriesTransformer,
):
    def _check_steps(self):
        names, estimators = zip(*self.steps)

        # validate names
        self._check_names(names)

        # validate estimators
        transformers = estimators[:-1]
        forecaster = estimators[-1]

        valid_transformer_type = _SeriesToSeriesTransformer
        for transformer in transformers:
            if not isinstance(transformer, valid_transformer_type):
                raise TypeError(
                    f"All intermediate steps should be "
                    f"instances of {valid_transformer_type}, "
                    f"but transformer: {transformer} is not."
                )

        valid_forecaster_type = BaseForecaster
        if not isinstance(forecaster, valid_forecaster_type):
            raise TypeError(
                f"Last step of {self.__class__.__name__} must be of type: "
                f"{valid_forecaster_type}, "
                f"but forecaster: {forecaster} is not."
            )

        # Shallow copy
        return list(self.steps)

    def _iter_transformers(self, reverse=False):

        # exclude final forecaster
        steps = self.steps_[:-1]

        if reverse:
            steps = reversed(steps)

        for idx, (name, transformer) in enumerate(steps):
            yield idx, name, transformer

    def __len__(self):
        """
        Returns the length of the Pipeline
        """
        return len(self.steps)

    @property
    def named_steps(self):
        """Map the steps to a dictionary"""
        return dict(self.steps)

    def get_params(self, deep=True):
        """Get parameters for this estimator.
        Parameters
        ----------
        deep : boolean, optional
            If True, will return the parameters for this estimator and
            contained subobjects that are estimators.
        Returns
        -------
        params : mapping of string to any
            Parameter names mapped to their values.
        """
        return self._get_params("steps", deep=deep)

    def set_params(self, **kwargs):
        """Set the parameters of this estimator.
        Valid parameter keys can be listed with ``get_params()``.
        Returns
        -------
        self
        """
        self._set_params("steps", **kwargs)
        return self


class ForecastingPipeline(_Pipeline):
    """
    Pipeline for forecasting with exogenous data to apply transformers
    to the exogenous serieses. The forecaster can also be a
    TransformedTargetForecaster containing transformers to
    transform y. ForecastingPipeline is only applying the given transformers
    to X.

    Parameters
    ----------
    steps : list
        List of tuples like ("name", forecaster/transformer)

    Example
    -------
    >>> from sktime.datasets import load_longley
    >>> from sktime.forecasting.naive import NaiveForecaster
    >>> from sktime.forecasting.compose import ForecastingPipeline
    >>> from sktime.transformations.series.impute import Imputer
    >>> from sktime.transformations.series.adapt import TabularToSeriesAdaptor
    >>> from sktime.forecasting.base import ForecastingHorizon
    >>> from sktime.forecasting.model_selection import temporal_train_test_split
    >>> from sklearn.preprocessing import MinMaxScaler
    >>> y, X = load_longley()
    >>> y_train, _, X_train, X_test = temporal_train_test_split(y, X)
    >>> fh = ForecastingHorizon(X_test.index, is_relative=False)
    >>> pipe = ForecastingPipeline(steps=[
    ...     ("imputer", Imputer(method="mean")),
    ...     ("minmaxscaler", TabularToSeriesAdaptor(MinMaxScaler())),
    ...     ("forecaster", NaiveForecaster(strategy="drift"))])
    >>> pipe.fit(y_train, X_train)
    ForecastingPipeline(...)
    >>> y_pred = pipe.predict(fh=fh, X=X_test)
    """

    _required_parameters = ["steps"]

    def __init__(self, steps):
        self.steps = steps
        self.steps_ = None
        super(ForecastingPipeline, self).__init__()

    def fit(self, y, X=None, fh=None):
        """Fit to training data.

        Parameters
        ----------
        y : pd.Series
            Target time series to which to fit the forecaster.
        fh : int, list or np.array, optional (default=None)
            The forecasters horizon with the steps ahead to to predict.
        X : pd.DataFrame, optional (default=None)
            Exogenous variables are ignored
        Returns
        -------
        self : returns an instance of self.
        """
        self.steps_ = self._check_steps()
        self._set_y_X(y, X)
        self._set_fh(fh)

        # transform X
        y, Xt = check_y_X(y, X)
        for step_idx, name, transformer in self._iter_transformers():
            t = clone(transformer)
            Xt = t.fit_transform(Xt)
            self.steps_[step_idx] = (name, t)

        # fit forecaster
        name, forecaster = self.steps[-1]
        f = clone(forecaster)
        f.fit(y, Xt, fh)
        self.steps_[-1] = (name, f)

        self._is_fitted = True
        return self

    def _predict(self, fh=None, X=None, return_pred_int=False, alpha=DEFAULT_ALPHA):
        Xt = check_X(X)
        forecaster = self.steps_[-1][1]
        # transform X before doing prediction
        for _, _, transformer in self._iter_transformers():
            Xt = transformer.transform(Xt)
        y_pred = forecaster.predict(
            fh, Xt, return_pred_int=return_pred_int, alpha=alpha
        )
        return y_pred

    def update(self, y, X=None, update_params=True):
        """Update fitted parameters

        Parameters
        ----------
        y : pd.Series
        X : pd.DataFrame
        update_params : bool, optional (default=True)

        Returns
        -------
        self : an instance of self
        """
        self.check_is_fitted()
        self._update_y_X(y, X)

        for step_idx, name, transformer in self._iter_transformers():
            if hasattr(transformer, "update"):
                transformer.update(X, update_params=update_params)
                self.steps_[step_idx] = (name, transformer)

        name, forecaster = self.steps_[-1]
        forecaster.update(y=y, X=X, update_params=update_params)
        self.steps_[-1] = (name, forecaster)
        return self

    def transform(self, Z, X=None):
        self.check_is_fitted()
        Zt = check_series(Z, enforce_multivariate=True)
        for _, _, transformer in self._iter_transformers():
            Zt = transformer.transform(Zt)
        return Zt

    def inverse_transform(self, Z, X=None):
        self.check_is_fitted()
        Zt = check_series(Z, enforce_multivariate=True)
        for _, _, transformer in self._iter_transformers(reverse=True):
            if not _has_tag(transformer, "skip-inverse-transform"):
                Zt = transformer.inverse_transform(Zt)
        return Zt


class TransformedTargetForecaster(_Pipeline):
    """
    Meta-estimator for forecasting transformed time series.
    Pipeline functionality to apply transformers to the target series.

    Parameters
    ----------
    steps : list
        List of tuples like ("name", forecaster/transformer)

    Example
    -------
    >>> from sktime.datasets import load_airline
    >>> from sktime.forecasting.naive import NaiveForecaster
    >>> from sktime.forecasting.compose import TransformedTargetForecaster
    >>> from sktime.transformations.series.impute import Imputer
    >>> from sktime.transformations.series.detrend import Deseasonalizer
    >>> y = load_airline()
    >>> pipe = TransformedTargetForecaster(steps=[
    ...     ("imputer", Imputer(method="mean")),
    ...     ("detrender", Deseasonalizer()),
    ...     ("forecaster", NaiveForecaster(strategy="drift"))])
    >>> pipe.fit(y)
    TransformedTargetForecaster(...)
    >>> y_pred = pipe.predict(fh=[1,2,3])
    """

    _required_parameters = ["steps"]
    _tags = {"univariate-only": True}

    def __init__(self, steps):
        self.steps = steps
        self.steps_ = None
        super(TransformedTargetForecaster, self).__init__()

    def fit(self, y, X=None, fh=None):
        """Fit to training data.

        Parameters
        ----------
        y : pd.Series
            Target time series to which to fit the forecaster.
        fh : int, list or np.array, optional (default=None)
            The forecasters horizon with the steps ahead to to predict.
        X : pd.DataFrame, optional (default=None)
            Exogenous variables are ignored
        Returns
        -------
        self : returns an instance of self.
        """
        self.steps_ = self._check_steps()
        self._set_y_X(y, X)
        self._set_fh(fh)

        # transform
        yt = check_y(y)
        for step_idx, name, transformer in self._iter_transformers():
            t = clone(transformer)
            yt = t.fit_transform(yt)
            self.steps_[step_idx] = (name, t)

        # fit forecaster
        name, forecaster = self.steps[-1]
        f = clone(forecaster)
        f.fit(yt, X, fh)
        self.steps_[-1] = (name, f)

        self._is_fitted = True
        return self

    def _predict(self, fh=None, X=None, return_pred_int=False, alpha=DEFAULT_ALPHA):
        forecaster = self.steps_[-1][1]
        y_pred = forecaster.predict(fh, X, return_pred_int=return_pred_int, alpha=alpha)

        for _, _, transformer in self._iter_transformers(reverse=True):
            # skip sktime transformers where inverse transform
            # is not wanted ur meaningful (e.g. Imputer, HampelFilter)
            if not _has_tag(transformer, "skip-inverse-transform"):
                y_pred = transformer.inverse_transform(y_pred)
        return y_pred

    def update(self, y, X=None, update_params=True):
        """Update fitted parameters

        Parameters
        ----------
        y : pd.Series
        X : pd.DataFrame
        update_params : bool, optional (default=True)

        Returns
        -------
        self : an instance of self
        """
        self.check_is_fitted()
        self._update_y_X(y, X)

        for step_idx, name, transformer in self._iter_transformers():
            if hasattr(transformer, "update"):
                transformer.update(y, X, update_params=update_params)
                self.steps_[step_idx] = (name, transformer)

        name, forecaster = self.steps_[-1]
        forecaster.update(y=y, X=X, update_params=update_params)
        self.steps_[-1] = (name, forecaster)
        return self

    def transform(self, Z, X=None):
        self.check_is_fitted()
        zt = check_series(Z, enforce_univariate=True)
        for _, _, transformer in self._iter_transformers():
            zt = transformer.transform(zt, X)
        return zt

    def inverse_transform(self, Z, X=None):
        self.check_is_fitted()
        zt = check_series(Z, enforce_univariate=True)
        for _, _, transformer in self._iter_transformers(reverse=True):
            if not _has_tag(transformer, "skip-inverse-transform"):
                zt = transformer.inverse_transform(zt, X)
        return zt