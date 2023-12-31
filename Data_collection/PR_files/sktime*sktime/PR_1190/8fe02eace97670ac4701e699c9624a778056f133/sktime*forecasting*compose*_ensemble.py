#!/usr/bin/env python3 -u
# -*- coding: utf-8 -*-
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)

__author__ = ["Markus LÃ¶ning"]
__all__ = ["EnsembleForecaster"]

import numpy as np
import pandas as pd

from sktime.forecasting.base._base import DEFAULT_ALPHA
from sktime.forecasting.base._meta import _HeterogenousEnsembleForecaster


class EnsembleForecaster(_HeterogenousEnsembleForecaster):
    """Ensemble of forecasters

    Parameters
    ----------
    forecasters : list of (str, estimator) tuples
    n_jobs : int or None, optional (default=None)
        The number of jobs to run in parallel for fit. None means 1 unless
        in a joblib.parallel_backend context.
        -1 means using all processors.
    aggfunc : str, {'mean', 'median', 'min', 'max'}, (default='mean')
        The function to aggregate prediction from individual forecasters.
    """

    _required_parameters = ["forecasters"]
    _tags = {
        "univariate-only": True,
        "requires-fh-in-fit": False,
        "handles-missing-data": False,
    }

    def __init__(self, forecasters, n_jobs=None, aggfunc="mean"):
        super(EnsembleForecaster, self).__init__(forecasters=forecasters, n_jobs=n_jobs)
        self.aggfunc = aggfunc

    def _fit(self, y, X=None, fh=None):
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

        names, forecasters = self._check_forecasters()
        self._fit_forecasters(forecasters, y, X, fh)
        return self

    def _update(self, y, X=None, update_params=True):
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

        for forecaster in self.forecasters_:
            forecaster.update(y, X, update_params=update_params)
        return self

    def _predict(self, fh, X=None, return_pred_int=False, alpha=DEFAULT_ALPHA):
        """return the predicted reduction

        Parameters
        ----------
        fh : int, list or np.array, optional (default=None)
        X : pd.DataFrame
        return_pred_int : boolean, optional (default=False)
        alpha : fh : float, (default=DEFAULT_ALPHA)

        Returns
        -------
        y_pred : pd.Series
            Aggregated predictions.
        """
        aggfunc = self._check_aggfunc()
        if return_pred_int:
            raise NotImplementedError()

        y_pred = pd.concat(self._predict_forecasters(fh, X), axis=1)
        return _aggregate(y=y_pred, aggfunc=aggfunc)

    def _check_aggfunc(self):
        valid_aggfuncs = {
            "mean": np.mean,
            "median": np.median,
            "average": np.average,
            "min": np.min,
            "max": np.max,
        }
        if self.aggfunc not in valid_aggfuncs.keys():
            raise ValueError("Aggregation function %s not recognized." % self.aggfunc)
        return valid_aggfuncs[self.aggfunc]


def _aggregate(y, aggfunc, X=None):
    """Apply aggregation function by row.

    Parameters
    ----------
    y : pd.DataFrame
        Multivariate series to transform.
    aggfunc : str
        Aggregation function used for transformation.
    X : pd.DataFrame, optional (default=None)
        Exogenous data used in transformation.

    Returns
    -------
    column_ensemble: pd.Series
        Transformed univariate series.
    """
    column_ensemble = y.apply(func=aggfunc, axis=1)

    return pd.Series(column_ensemble, index=y.index)
