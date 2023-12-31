#!/usr/bin/env python3 -u
# coding: utf-8
<<<<<<< HEAD
=======
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)
>>>>>>> 67c56be8b1e838f2628df829946f795b7dba9aed

__author__ = ["Markus LÃ¶ning"]
__all__ = ["BaseStatsModelsAdapter"]

<<<<<<< HEAD
from sktime.forecasting.base._sktime import BaseSktimeForecaster, OptionalForecastingHorizonMixin
from sktime.forecasting.base._base import DEFAULT_ALPHA


class BaseStatsModelsAdapter(OptionalForecastingHorizonMixin, BaseSktimeForecaster):
=======
from sktime.forecasting.base._base import DEFAULT_ALPHA
from sktime.forecasting.base._sktime import BaseSktimeForecaster
from sktime.forecasting.base._sktime import OptionalForecastingHorizonMixin


class BaseStatsModelsAdapter(OptionalForecastingHorizonMixin,
                             BaseSktimeForecaster):
>>>>>>> 67c56be8b1e838f2628df829946f795b7dba9aed
    """Base class for interfacing statsmodels forecasting algorithms
    """
    _fitted_param_names = ()

    def __init__(self):
        self._forecaster = None
        self._fitted_forecaster = None
        super(BaseStatsModelsAdapter, self).__init__()

    def fit(self, y_train, fh=None, X_train=None):
        """Fit to training data.

        Parameters
        ----------
        y_train : pd.Series
            Target time series to which to fit the forecaster.
        fh : int, list or np.array, optional (default=None)
            The forecasters horizon with the steps ahead to to predict.
        X_train : pd.DataFrame, optional (default=None)
            Exogenous variables are ignored
        Returns
        -------
        self : returns an instance of self.
        """

        # update observation horizon
        self._set_oh(y_train)
        self._set_fh(fh)
        self._fit_forecaster(y_train, X_train=X_train)
        self._is_fitted = True
        return self

    def _fit_forecaster(self, y_train, X_train=None):
        """Internal fit"""
        raise NotImplementedError("abstract method")

    def _predict(self, fh, X=None, return_pred_int=False, alpha=DEFAULT_ALPHA):
        """
        Make forecasts.

        Parameters
        ----------
        fh : int or array-like, optional (default=1)
<<<<<<< HEAD
            The forecasters horizon with the steps ahead to to predict. Default is one-step ahead forecast,
=======
            The forecasters horizon with the steps ahead to to predict.
            Default is one-step ahead forecast,
>>>>>>> 67c56be8b1e838f2628df829946f795b7dba9aed
            i.e. np.array([1])
        X : None
            Exogenous variables are ignored.
        return_pred_int : bool, optional (default=False)
        alpha : int or list, optional (default=0.95)

        Returns
        -------
        y_pred : pandas.Series
            Returns series of predicted values.
        """
        if return_pred_int:
            raise NotImplementedError()
        # Forecast all periods from start to end of pred horizon,
        # but only return given time points in pred horizon
        fh_abs = fh.absolute(self.cutoff)
<<<<<<< HEAD
        y_pred = self._fitted_forecaster.predict(start=fh_abs[0], end=fh_abs[-1])
=======
        y_pred = self._fitted_forecaster.predict(start=fh_abs[0],
                                                 end=fh_abs[-1])
>>>>>>> 67c56be8b1e838f2628df829946f795b7dba9aed
        return y_pred.loc[fh_abs]

    def get_fitted_params(self):
        """Get fitted parameters

        Returns
        -------
        fitted_params : dict
        """
        self.check_is_fitted()
        return {name: self._fitted_forecaster.params.get(name)
                for name in self._get_fitted_param_names()}

    def _get_fitted_param_names(self):
        """Get names of fitted parameters"""
        return self._fitted_param_names
