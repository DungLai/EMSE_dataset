#!/usr/bin/env python3 -u
# -*- coding: utf-8 -*-
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)

__author__ = ["Markus LÃ¶ning", "@big-o"]
__all__ = ["BaseForecaster"]

from sktime.base import BaseEstimator

from contextlib import contextmanager
from warnings import warn

import numpy as np
import pandas as pd

from sktime.forecasting.model_selection import CutoffSplitter
from sktime.forecasting.model_selection import SlidingWindowSplitter
from sktime.utils.datetime import _shift
from sktime.utils.validation.forecasting import check_X
from sktime.utils.validation.forecasting import check_alpha
from sktime.utils.validation.forecasting import check_cv
from sktime.utils.validation.forecasting import check_fh
from sktime.utils.validation.forecasting import check_y
from sktime.utils.validation.forecasting import check_y_X


DEFAULT_ALPHA = 0.05


class BaseForecaster(BaseEstimator):
    """Base forecaster

    The base forecaster specifies the methods and method
    signatures that all forecasters have to implement.

    Specific implementations of these methods is deferred to concrete
    forecasters.
    """

    def __init__(self):
        self._is_fitted = False

        self._y = None
        self._X = None

        # forecasting horizon
        self._fh = None
        self._cutoff = None  # reference point for relative fh

        # defaults for estimator tags
        self._tags['fh_in_fit'] = 'required'

        super(BaseForecaster, self).__init__()


    def fit(self, y, X=None, fh=None):
        """Fit to training data, including checks & utility
            dispatches to core logic in _fit

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

        self._set_fh(fh)
        y, X = check_y_X(y, X)

        self._fit(y=y, X=X, fh=fh)

        return self

        
        raise NotImplementedError("abstract method")

    def predict(self, fh=None, X=None, return_pred_int=False, alpha=DEFAULT_ALPHA):
        """Forecast to future horizon, including checks & utility
            dispatches to core logic in _predict

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
        y_pred_int : pd.DataFrame - only if return_pred_int=True
            Prediction intervals
        """

        self.check_is_fitted()
        self._set_fh(fh)

        X = check_X(X)
        alpha = check_alpha(alpha)

        return self._predict(self.fh, X, return_pred_int=return_pred_int, alpha=alpha)

    def compute_pred_int(self, y_pred, alpha=DEFAULT_ALPHA):
        """
        Get the prediction intervals for a forecast.

        If alpha is iterable, multiple intervals will be calculated.

        Parameters
        ----------

        y_pred : pd.Series
            Point predictions.

        alpha : float or list, optional (default=0.95)
            A significance level or list of significance levels.

        Returns
        -------

        intervals : pd.DataFrame
            A table of upper and lower bounds for each point prediction in
            ``y_pred``. If ``alpha`` was iterable, then ``intervals`` will be a
            list of such tables.
        """
        raise NotImplementedError("abstract method")

    def update(self, y, X=None, update_params=True):
        """Update cutoff value and, optionally, fitted parameters.

        This is useful in an online learning setting where new data is observed as
        time moves on. Updating the cutoff value allows to generate new predictions
        from the most recent time point that was observed. Updating the fitted
        parameters allows to incrementally update the parameters without having to
        completely refit. However, note that if no estimator-specific update method
        has been implemented for updating parameters refitting is the default fall-back
        option.

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
        if update_params:
            # default to re-fitting if update is not implemented
            warn(
                f"NotImplementedWarning: {self.__class__.__name__} "
                f"does not have a custom `update` method implemented. "
                f"{self.__class__.__name__} will be refit each time "
                f"`update` is called."
            )
            # refit with updated data, not only passed data
            self.fit(self._y, self._X, self.fh)
        return self

    def update_predict(
        self,
        y,
        cv=None,
        X=None,
        update_params=True,
        return_pred_int=False,
        alpha=DEFAULT_ALPHA,
    ):
        """Make and update predictions iteratively over the test set.

        Parameters
        ----------
        y : pd.Series
        cv : temporal cross-validation generator, optional (default=None)
        X : pd.DataFrame, optional (default=None)
        update_params : bool, optional (default=True)
        return_pred_int : bool, optional (default=False)
        alpha : int or list of ints, optional (default=None)

        Returns
        -------
        y_pred : pd.Series
            Point predictions
        y_pred_int : pd.DataFrame
            Prediction intervals
        """

        if return_pred_int:
            raise NotImplementedError()
        y = check_y(y)
        cv = (
            check_cv(cv)
            if cv is not None
            else SlidingWindowSplitter(fh=self.fh, start_with_window=False)
        )
        return self._predict_moving_cutoff(
            y,
            cv,
            X,
            update_params=update_params,
            return_pred_int=return_pred_int,
            alpha=alpha,
        )

    def update_predict_single(
        self,
        y_new,
        fh=None,
        X=None,
        update_params=True,
        return_pred_int=False,
        alpha=DEFAULT_ALPHA,
    ):
        """Update and make forecasts."

        This method is useful for updating forecasts in a single step,
        allowing to make use of more efficient
        updating algorithms than calling update and predict sequentially.

        Parameters
        ----------
        y_new : pd.Series
        fh : int, list, np.array or ForecastingHorizon
        X : pd.DataFrame
        update_params : bool, optional (default=False)
        return_pred_int : bool, optional (default=False)
            If True, prediction intervals are returned in addition to point
            predictions.
        alpha : float or list of floats

        Returns
        -------
        y_pred : pd.Series
            Point predictions
        pred_ints : pd.DataFrame
            Prediction intervals
        """
        self.check_is_fitted()
        self._set_fh(fh)
        return self._update_predict_single(
            y_new,
            self.fh,
            X,
            update_params=update_params,
            return_pred_int=return_pred_int,
            alpha=alpha,
        )

    def score(self, y, X=None, fh=None):
        """Compute the symmetric version of mean absolute percentage error
        for the given forecasting horizon.

        Parameters
        ----------
        y : pd.Series
            Target time series to which to compare the forecasts.
        fh : int, list, array-like or ForecastingHorizon, optional (default=None)
            The forecasters horizon with the steps ahead to to predict.
        X : pd.DataFrame, shape=[n_obs, n_vars], optional (default=None)
            An optional 2-d dataframe of exogenous variables.

        Returns
        -------
        score : float
            sMAPE loss of self.predict(fh, X) with respect to y_test.

        See Also
        --------
        :meth:`sktime.performance_metrics.forecasting.mean_absolute_percentage_error`
        """
        # no input checks needed here, they will be performed
        # in predict and loss function
        # symmetric=True is default for mean_absolute_percentage_error
        from sktime.performance_metrics.forecasting import (
            mean_absolute_percentage_error,
        )

        return mean_absolute_percentage_error(y, self.predict(fh, X))

    def get_fitted_params(self):
        """Get fitted parameters

        Returns
        -------
        fitted_params : dict
        """
        raise NotImplementedError("abstract method")

    def _set_y_X(self, y, X=None, enforce_index_type=None):
        """Set training data.

        Parameters
        ----------
        y : pd.Series
            Endogenous time series
        X : pd.DataFrame, optional (default=None)
            Exogenous time series
        """
        # set initial training data
        self._y, self._X = check_y_X(
            y, X, allow_empty=False, enforce_index_type=enforce_index_type
        )

        # set initial cutoff to the end of the training data
        self._set_cutoff(y.index[-1])

    def _update_X(self, X, enforce_index_type=None):
        if X is not None:
            X = check_X(X, enforce_index_type=enforce_index_type)
            if X is len(X) > 0:
                self._X = X.combine_first(self._X)

    def _update_y_X(self, y, X=None, enforce_index_type=None):
        """Update training data.

        Parameters
        ----------
        y : pd.Series
            Endogenous time series
        X : pd.DataFrame, optional (default=None)
            Exogenous time series
        """
        # update only for non-empty data
        y, X = check_y_X(y, X, allow_empty=True, enforce_index_type=enforce_index_type)

        if len(y) > 0:
            self._y = y.combine_first(self._y)

            # set cutoff to the end of the observation horizon
            self._set_cutoff(y.index[-1])

            # update X if given
            if X is not None:
                self._X = X.combine_first(self._X)

    def _get_y_pred(self, y_in_sample, y_out_sample):
        """Combining in-sample and out-sample prediction
        and slicing on given fh.

        Parameters
        ----------
        y_in_sample : pd.Series
            In-sample prediction
        y_out_sample : pd.Series
            Out-sample prediction

        Returns
        -------
        pd.Series
            y_pred, sliced by fh
        """
        y_pred = y_in_sample.append(y_out_sample, ignore_index=True).rename("y_pred")
        y_pred = pd.DataFrame(y_pred)
        # Workaround for slicing with negative index
        y_pred["idx"] = [x for x in range(-len(y_in_sample), len(y_out_sample))]
        y_pred = y_pred.loc[y_pred["idx"].isin(self.fh.to_indexer(self.cutoff).values)]
        y_pred.index = self.fh.to_absolute(self.cutoff)
        y_pred = y_pred["y_pred"].rename(None)
        return y_pred

    def _get_pred_int(self, lower, upper):
        """Combining lower and upper bound of
        prediction intervals. Slicing on fh.

        Parameters
        ----------
        lower : pd.Series
            Lower bound (can contain also in-sample bound)
        upper : pd.Series
            Upper bound (can contain also in-sample bound)

        Returns
        -------
        pd.DataFrame
            pred_int, predicion intervalls (out-sample, sliced by fh)
        """
        pred_int = pd.DataFrame({"lower": lower, "upper": upper})
        # Out-sample fh
        fh_out = self.fh.to_out_of_sample(cutoff=self.cutoff)
        # If pred_int contains in-sample prediction intervals
        if len(pred_int) > len(self._y):
            len_out = len(pred_int) - len(self._y)
            # Workaround for slicing with negative index
            pred_int["idx"] = [x for x in range(-len(self._y), len_out)]
        # If pred_int does not contain in-sample prediction intervals
        else:
            pred_int["idx"] = [x for x in range(len(pred_int))]
        pred_int = pred_int.loc[
            pred_int["idx"].isin(fh_out.to_indexer(self.cutoff).values)
        ]
        pred_int.index = fh_out.to_absolute(self.cutoff)
        pred_int = pred_int.drop(columns=["idx"])
        return pred_int

    @property
    def cutoff(self):
        """The time point at which to make forecasts

        Returns
        -------
        cutoff : int
        """
        return self._cutoff

    def _set_cutoff(self, cutoff):
        """Set and update cutoff

        Parameters
        ----------
        cutoff : int
        """
        self._cutoff = cutoff

    @contextmanager
    def _detached_cutoff(self):
        """When in detached cutoff mode, the cutoff can be updated but will
        be reset to the initial value after leaving the detached cutoff mode.

        This is useful during rolling-cutoff forecasts when the cutoff needs
        to be repeatedly reset, but afterwards should be restored to the
        original value.
        """
        cutoff = self.cutoff  # keep initial cutoff
        try:
            yield
        finally:
            # re-set cutoff to initial value
            self._set_cutoff(cutoff)

    @property
    def fh(self):
        """The forecasting horizon"""
        # raise error if some method tries to accessed it before it has been
        # set
        if self._fh is None:
            raise ValueError(
                "No `fh` has been set yet, please specify `fh` " "in `fit` or `predict`"
            )
        return self._fh

    def _set_fh(self, fh):
        """Check, set and update the forecasting horizon.

        Parameters
        ----------
        fh : None, int, list, np.ndarray or ForecastingHorizon
        """

        optfh = self._tags['fh_in_fit'] == 'required'

        msg = (
            f"This is because fitting of the `"
            f"{self.__class__.__name__}` "
            f"depends on `fh`. "
        )

        # below loop treats four cases from three conditions:
        #  A. forecaster is fitted yes/no - self.is_fitted
        #  B. no fh is passed yes/no - fh is None
        #  C. fh is optional in fit yes/no - optfh
    
        # B. no fh is passed
        if fh is None:
            # A. strategy fitted (call of predict or similar)
            if self.is_fitted:
                # in case C. fh is optional in fit:
                # if there is none from before, there is none overall - raise error
                if optfh and self._fh is None:
                    raise ValueError(
                        "The forecasting horizon `fh` must be passed "
                        "either to `fit` or `predict`, "
                        "but was found in neither."
                    )
                # in case C. fh is not optional in fit: this is fine
                # any error would ahve already been caught in fit

            # A. strategy not fitted (call of fit)
            elif not optfh:
                # in case fh is not optional in fit:
                # fh must be passed in fit
                raise ValueError(
                    "The forecasting horizon `fh` must be passed to "
                    "`fit`, "
                    "but none was found. " + msg
                )
                # in case C. fh is optional in fit:
                # this is fine, nothing to check/raise
    
        # B. fh is passed
        else:
            # If fh is passed, validate (no matter the situation)
            fh = check_fh(fh)

            # if A. not yet fitted, then write fh to self
            if not self.is_fitted:
                self._fh = fh
            # A. estimator is fitted
            #  the only error can arise when fitted from inconsistency
            #  between fh passed in fit and fh provided later
            # this applies to both C. cases (optional/not)
            elif self._fh:
                if not np.array_equal(fh, self._fh):
                    # raise error if existing fh and new one don't match
                    raise ValueError(
                        "A different forecasting horizon `fh` has been "
                        "provided from "
                        "the one seen in `fit`. If you want to change the "
                        "forecasting "
                        "horizon, please re-fit the forecaster. " + msg
                    )
                # if existing one and new match, ignore new one
                pass

    def _fit(self, y, X=None, fh=None):
        """Core fit logic

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
        raise NotImplementedError("abstract method")

    def _predict(self, fh, X=None, return_pred_int=False, alpha=DEFAULT_ALPHA):
        """Core forecasting logic

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
        y_pred_int : pd.DataFrame - only if return_pred_int=True
            Prediction intervals
        """
        raise NotImplementedError("abstract method")

    def _update_predict_single(
        self,
        y,
        fh,
        X=None,
        update_params=True,
        return_pred_int=False,
        alpha=DEFAULT_ALPHA,
    ):
        """Internal method for updating and making forecasts.

        Implements default behaviour of calling update and predict
        sequentially, but can be overwritten by subclasses
        to implement more efficient updating algorithms when available.
        """
        self.update(y, X, update_params=update_params)
        return self.predict(fh, X, return_pred_int=return_pred_int, alpha=alpha)
