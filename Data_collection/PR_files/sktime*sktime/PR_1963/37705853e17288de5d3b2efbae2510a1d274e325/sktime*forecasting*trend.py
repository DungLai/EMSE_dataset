# -*- coding: utf-8 -*-
# !/usr/bin/env python3 -u
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)
"""Implements trend based forecasters."""

__author__ = ["Anthony Jancso", "mloning", "aiwalter"]
__all__ = ["TrendForecaster", "PolynomialTrendForecaster", "STLForecaster"]

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures
from statsmodels.tsa.seasonal import STL as _STL

from sktime.forecasting.base import BaseForecaster
from sktime.forecasting.base._base import DEFAULT_ALPHA
from sktime.forecasting.naive import NaiveForecaster
from sktime.utils.datetime import _get_duration


class TrendForecaster(BaseForecaster):
    """Trend based forecasts of time series data.

    Default settings train a linear regression model.

    Parameters
    ----------
    regressor : estimator object, default = None
        Define the regression model type. If not set, will default to
         sklearn.linear_model.LinearRegression

    Examples
    --------
    >>> from sktime.datasets import load_airline
    >>> from sktime.forecasting.trend import TrendForecaster
    >>> y = load_airline()
    >>> forecaster = TrendForecaster()
    >>> forecaster.fit(y)
    TrendForecaster(...)
    >>> y_pred = forecaster.predict(fh=[1,2,3])
    """

    _tags = {
        "ignores-exogeneous-X": True,
        "requires-fh-in-fit": False,
        "handles-missing-data": False,
    }

    def __init__(self, regressor=None):
        # for default regressor, set fit_intercept=True
        self.regressor = regressor
        super(TrendForecaster, self).__init__()

    def _fit(self, y, X=None, fh=None):
        """Fit to training data.

        Parameters
        ----------
        y : pd.Series
            Target time series with which to fit the forecaster.
        X : pd.DataFrame, default=None
            Exogenous variables are ignored
        fh : int, list or np.array, optional (default=None)
            The forecasters horizon with the steps ahead to to predict.

        Returns
        -------
        self : returns an instance of self.
        """
        self.regressor_ = self.regressor or LinearRegression(fit_intercept=True)

        # create a clone of self.regressor
        self.regressor_ = clone(self.regressor_)

        # transform data
        X = y.index.astype("int").to_numpy().reshape(-1, 1)

        # fit regressor
        self.regressor_.fit(X, y)
        return self

    def _predict(self, fh=None, X=None, return_pred_int=False, alpha=DEFAULT_ALPHA):
        """Make forecasts for the given forecast horizon.

        Parameters
        ----------
        fh : int, list or np.array
            The forecast horizon with the steps ahead to predict
        X : pd.DataFrame, default=None
            Exogenous variables (ignored)
        return_pred_int : bool, default=False
            Return the prediction intervals for the forecast.
        alpha : float or list, default=0.95
            If alpha is iterable, multiple intervals will be calculated.

        Returns
        -------
        y_pred : pd.Series
            Point predictions for the forecast
        y_pred_int : pd.DataFrame
            Prediction intervals for the forecast
        """
        # use relative fh as time index to predict
        fh = self.fh.to_absolute_int(self._y.index[0], self.cutoff)
        X_pred = fh.to_numpy().reshape(-1, 1)
        y_pred = self.regressor_.predict(X_pred)
        return pd.Series(y_pred, index=self.fh.to_absolute(self.cutoff))


class PolynomialTrendForecaster(BaseForecaster):
    """Forecast time series data with a polynomial trend.

    Default settings train a linear regression model with a 1st degree
    polynomial transformation of the feature.

    Parameters
    ----------
    regressor : estimator object, default = None
        Define the regression model type. If not set, will default to
         sklearn.linear_model.LinearRegression
    degree : int, default = 1
        Degree of polynomial function
    with_intercept : bool, default=True
        If true, then include a feature in which all polynomial powers are
        zero. (i.e. a column of ones, acts as an intercept term in a linear
        model)

    Examples
    --------
    >>> from sktime.datasets import load_airline
    >>> from sktime.forecasting.trend import PolynomialTrendForecaster
    >>> y = load_airline()
    >>> forecaster = PolynomialTrendForecaster(degree=1)
    >>> forecaster.fit(y)
    PolynomialTrendForecaster(...)
    >>> y_pred = forecaster.predict(fh=[1,2,3])
    """

    _tags = {
        "ignores-exogeneous-X": True,
        "requires-fh-in-fit": False,
        "handles-missing-data": False,
    }

    def __init__(self, regressor=None, degree=1, with_intercept=True):
        self.regressor = regressor
        self.degree = degree
        self.with_intercept = with_intercept
        self.regressor_ = self.regressor
        super(PolynomialTrendForecaster, self).__init__()

    def _fit(self, y, X=None, fh=None):
        """Fit to training data.

        Parameters
        ----------
        y : pd.Series
            Target time series with which to fit the forecaster.
        X : pd.DataFrame, default=None
            Exogenous variables are ignored
        fh : int, list or np.array, default=None
            The forecasters horizon with the steps ahead to to predict.

        Returns
        -------
        self : returns an instance of self.
        """
        # for default regressor, set fit_intercept=False as we generate a
        # dummy variable in polynomial features
        if self.regressor is None:
            regressor = LinearRegression(fit_intercept=False)
        else:
            regressor = self.regressor

        # make pipeline with polynomial features
        self.regressor_ = make_pipeline(
            PolynomialFeatures(degree=self.degree, include_bias=self.with_intercept),
            regressor,
        )

        # transform data
        n_timepoints = _get_duration(self._y.index, coerce_to_int=True) + 1
        X = np.arange(n_timepoints).reshape(-1, 1)

        # fit regressor
        self.regressor_.fit(X, y)
        return self

    def _predict(self, fh=None, X=None, return_pred_int=False, alpha=DEFAULT_ALPHA):
        """Make forecasts for the given forecast horizon.

        Parameters
        ----------
        fh : int, list or np.array
            The forecast horizon with the steps ahead to predict
        X : pd.DataFrame, default=None
            Exogenous variables (ignored)
        return_pred_int : bool, default=False
            Return the prediction intervals for the forecast.
        alpha : float or list, default=0.95
            If alpha is iterable, multiple intervals will be calculated.

        Returns
        -------
        y_pred : pd.Series
            Point predictions for the forecast
        y_pred_int : pd.DataFrame
            Prediction intervals for the forecast
        """
        # use relative fh as time index to predict
        fh = self.fh.to_absolute_int(self._y.index[0], self.cutoff)
        X_pred = fh.to_numpy().reshape(-1, 1)
        y_pred = self.regressor_.predict(X_pred)
        return pd.Series(y_pred, index=self.fh.to_absolute(self.cutoff))


class STLForecaster(BaseForecaster):
    """Implements STLForecaster based on statsmodels.tsa.seasonal.STL implementation.

    The STLForecaster is using an STL to decompose the given
    series y into the three components trend, season and residuals [1]_. Then,
    the forecaster_trend, forecaster_seasonal and forecaster_resid are fitted
    on the components individually to forecast them also individually. The
    final forecast is then the sum of the three component forecasts. The STL
    decomposition is done by means of using the package statsmodels [2]_.

    Parameters
    ----------
    forecaster_trend : sktime forecaster, optional
        Forecaster to be fitted on trend_ component of the
        STL, by default None. If None, then
        a NaiveForecaster(strategy="drift") is used.
    forecaster_seasonal : sktime forecaster, optional
        Forecaster to be fitted on seasonal_ component of the
        STL, by default None. If None, then
        a NaiveForecaster(strategy="last") is used.
    forecaster_resid : sktime forecaster, optional
        Forecaster to be fitted on resid_ component of the
        STL, by default None. If None, then
        a NaiveForecaster(strategy="mean") is used.
    sp : int, optional
        Seasonal period for defaulting forecasters and/or STL.period param,
        by default None. Can only be used if at least on the forecasters
        or the stl is None.
    period : {int, None}, optional
        Periodicity of the sequence. If None and endog is a pandas Series or
        DataFrame, attempts to determine from endog. If endog is a ndarray,
        period must be provided.
    seasonal : int, optional
        Length of the seasonal smoother. Must be an odd integer, and should
        normally be >= 7 (default).
    trend : {int, None}, optional
        Length of the trend smoother. Must be an odd integer. If not provided
        uses the smallest odd integer greater than
        1.5 * period / (1 - 1.5 / seasonal), following the suggestion in
        the original implementation.
    low_pass : {int, None}, optional
        Length of the low-pass filter. Must be an odd integer >=3. If not
        provided, uses the smallest odd integer > period.
    seasonal_deg : int, optional
        Degree of seasonal LOESS. 0 (constant) or 1 (constant and trend).
    trend_deg : int, optional
        Degree of trend LOESS. 0 (constant) or 1 (constant and trend).
    low_pass_deg : int, optional
        Degree of low pass LOESS. 0 (constant) or 1 (constant and trend).
    robust : bool, optional
        Flag indicating whether to use a weighted version that is robust to
        some forms of outliers.
    seasonal_jump : int, optional
        Positive integer determining the linear interpolation step. If larger
        than 1, the LOESS is used every seasonal_jump points and linear
        interpolation is between fitted points. Higher values reduce
        estimation time.
    trend_jump : int, optional
        Positive integer determining the linear interpolation step. If larger
        than 1, the LOESS is used every trend_jump points and values between
        the two are linearly interpolated. Higher values reduce estimation
        time.
    low_pass_jump : int, optional
        Positive integer determining the linear interpolation step. If larger
        than 1, the LOESS is used every low_pass_jump points and values between
        the two are linearly interpolated. Higher values reduce estimation
        time.

    Attributes
    ----------
    trend_ : pd.Series
        Trend component.
    seasonal_ : pd.Series
        Seasonal component.
    resid_ : pd.Series
        Residuals component.
    forecaster_trend_ : sktime forecaster
        Fitted trend forecaster.
    forecaster_seasonal_ : sktime forecaster
        Fitted seasonal forecaster.
    forecaster_resid_ : sktime forecaster
        Fitted residual forecaster.
    stl_ : STL
        Fitted statsmodels.STL

    Examples
    --------
    >>> from sktime.datasets import load_airline
    >>> from sktime.forecasting.trend import STLForecaster
    >>> y = load_airline()
    >>> forecaster = STLForecaster(sp=12)
    >>> forecaster.fit(y)
    STLForecaster(...)
    >>> y_pred = forecaster.predict(fh=[1,2,3])

    See Also
    --------
    Deseasonalizer
    Detrender

    References
    ----------
    .. [1] R. B. Cleveland, W. S. Cleveland, J.E. McRae, and I. Terpenning (1990)
       STL: A Seasonal-Trend Decomposition Procedure Based on LOESS.
       Journal of Official Statistics, 6, 3-73.
    .. [2] https://www.statsmodels.org/dev/generated/statsmodels.tsa.seasonal.STL.html
    """

    _tags = {
        "scitype:y": "univariate",  # which y are fine? univariate/multivariate/both
        "ignores-exogeneous-X": False,  # does estimator ignore the exogeneous X?
        "handles-missing-data": False,  # can estimator handle missing data?
        "y_inner_mtype": "pd.Series",  # which types do _fit, _predict, assume for y?
        "X_inner_mtype": "pd.DataFrame",  # which types do _fit, _predict, assume for X?
        "requires-fh-in-fit": False,  # is forecasting horizon already required in fit?
    }

    def __init__(
        self,
        forecaster_trend=None,
        forecaster_seasonal=None,
        forecaster_resid=None,
        sp=2,
        seasonal=7,
        trend=None,
        low_pass=None,
        seasonal_deg=1,
        trend_deg=1,
        low_pass_deg=1,
        robust=False,
        seasonal_jump=1,
        trend_jump=1,
        low_pass_jump=1,
    ):
        self.forecaster_trend = forecaster_trend
        self.forecaster_seasonal = forecaster_seasonal
        self.forecaster_resid = forecaster_resid
        self.sp = sp
        self.seasonal = seasonal
        self.trend = trend
        self.low_pass = low_pass
        self.seasonal_deg = seasonal_deg
        self.trend_deg = trend_deg
        self.low_pass_deg = low_pass_deg
        self.robust = robust
        self.seasonal_jump = seasonal_jump
        self.trend_jump = trend_jump
        self.low_pass_jump = low_pass_jump
        super(STLForecaster, self).__init__()

    def _fit(self, y, X=None, fh=None):
        """Fit forecaster to training data.

        Parameters
        ----------
        y : pd.Series
            Target time series to which to fit the forecaster.
        fh : int, list, np.array or ForecastingHorizon, optional (default=None)
            The forecasters horizon with the steps ahead to to predict.
        X : pd.DataFrame, optional (default=None)

        Returns
        -------
        self : returns an instance of self.
        """
        self.stl_ = _STL(
            y.values,
            period=self.sp,
            seasonal=self.seasonal,
            trend=self.trend,
            low_pass=self.low_pass,
            seasonal_deg=self.seasonal_deg,
            trend_deg=self.trend_deg,
            low_pass_deg=self.low_pass_deg,
            robust=self.robust,
            seasonal_jump=self.seasonal_jump,
            trend_jump=self.trend_jump,
            low_pass_jump=self.low_pass_jump,
        ).fit()

        self.seasonal_ = pd.Series(self.stl_.seasonal, index=y.index)
        self.resid_ = pd.Series(self.stl_.resid, index=y.index)
        self.trend_ = pd.Series(self.stl_.trend, index=y.index)

        # TODO: set sp=self.sp after NaiveForecaster bug fix
        # setting defualt forecasters if required
        self.forecaster_seasonal_ = (
            NaiveForecaster(sp=1, strategy="last")
            if self.forecaster_seasonal is None
            else clone(self.forecaster_seasonal)
        )
        self.forecaster_trend_ = (
            NaiveForecaster(strategy="drift")
            if self.forecaster_trend is None
            else clone(self.forecaster_trend)
        )
        self.forecaster_resid_ = (
            NaiveForecaster(sp=1, strategy="mean")
            if self.forecaster_resid is None
            else clone(self.forecaster_resid)
        )

        # fitting forecasters to different components
        self.forecaster_seasonal_.fit(y=self.seasonal_, X=X, fh=fh)
        self.forecaster_trend_.fit(y=self.trend_, X=X, fh=fh)
        self.forecaster_resid_.fit(y=self.resid_, X=X, fh=fh)

    def _predict(self, fh, X=None, return_pred_int=False, alpha=DEFAULT_ALPHA):
        """Forecast time series at future horizon.

        Parameters
        ----------
        fh : int, list, np.array or ForecastingHorizon
            Forecasting horizon
        X : pd.DataFrame, optional (default=None)
                Exogenous time series
        return_pred_int : bool, optional (default=False)
            If True, returns prediction intervals for given alpha values.
        alpha : float or list, optional (default=0.95)

        Returns
        -------
        y_pred : pd.Series
            Point predictions
        """
        y_pred_seasonal = self.forecaster_seasonal_.predict(fh=fh, X=X)
        y_pred_trend = self.forecaster_trend_.predict(fh=fh, X=X)
        y_pred_resid = self.forecaster_resid_.predict(fh=fh, X=X)
        y_pred = y_pred_seasonal + y_pred_trend + y_pred_resid
        return y_pred

    def _update(self, y, X=None, update_params=True):
        """Update cutoff value and, optionally, fitted parameters.

        Parameters
        ----------
        y : pd.Series, pd.DataFrame, or np.array
            Target time series to which to fit the forecaster.
        X : pd.DataFrame, optional (default=None)
            Exogeneous data
        update_params : bool, optional (default=True)
            whether model parameters should be updated

        Returns
        -------
        self : reference to self
        """
        # TODO: remove _update method after refactor of update methods in base class.
        # This method is only required to pass tests.
        self.stl_ = _STL(
            y.values,
            period=self.sp,
            seasonal=self.seasonal,
            trend=self.trend,
            low_pass=self.low_pass,
            seasonal_deg=self.seasonal_deg,
            trend_deg=self.trend_deg,
            low_pass_deg=self.low_pass_deg,
            robust=self.robust,
            seasonal_jump=self.seasonal_jump,
            trend_jump=self.trend_jump,
            low_pass_jump=self.low_pass_jump,
        ).fit()

        self.seasonal_ = pd.Series(self.stl_.seasonal, index=y.index)
        self.resid_ = pd.Series(self.stl_.resid, index=y.index)
        self.trend_ = pd.Series(self.stl_.trend, index=y.index)

        self.forecaster_seasonal_.update(
            y=self.seasonal_, X=X, update_params=update_params
        )
        self.forecaster_trend_.update(y=self.trend_, X=X, update_params=update_params)
        self.forecaster_resid_.update(y=self.resid_, X=X, update_params=update_params)
        return self
