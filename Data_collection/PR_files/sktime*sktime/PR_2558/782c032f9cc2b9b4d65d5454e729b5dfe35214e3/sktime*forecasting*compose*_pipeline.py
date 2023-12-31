#!/usr/bin/env python3 -u
# -*- coding: utf-8 -*-
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)
"""Implements pipelines for forecasting."""

__author__ = ["mloning", "aiwalter"]
__all__ = ["TransformedTargetForecaster", "ForecastingPipeline"]

import pandas as pd
from sklearn.base import clone

from sktime.base import _HeterogenousMetaEstimator
from sktime.forecasting.base._base import BaseForecaster
from sktime.registry import scitype
from sktime.utils.validation.series import check_series


class _Pipeline(
    BaseForecaster,
    _HeterogenousMetaEstimator,
):
    """Abstract class for forecasting pipelines."""

    def _get_pipeline_scitypes(self, estimators):
        """Get list of scityes (str) from names/estimator list."""
        return [scitype(x[1]) for x in estimators]

    def _get_forecaster_index(self, estimators):
        """Get the index of the first forecaster in the list."""
        return self._get_pipeline_scitypes(estimators).index("forecaster")

    def _check_steps(self, estimators, allow_postproc=False):
        """Check Steps.

        Parameters
        ----------
        estimators : list of estimators, or list of (name, estimator) pairs
        allow_postproc : bool, optional, default=False
            whether transformers after the forecaster are allowed

        Returns
        -------
        step : list of (name, estimator) pairs, estimators are cloned (not references)
            if estimators was a list of (str, estimator) tuples, then just cloned
            if was a list of estimators, then str are generated via _get_estimator_names

        Raises
        ------
        TypeError if names in `estimators` are not unique
        TypeError if estimators in `estimators` are not all forecaster or transformer
        TypeError if there is not exactly one forecaster in `estimators`
        TypeError if not allow_postproc and forecaster is not last estimator
        """
        estimator_tuples = self._get_estimator_tuples(estimators, clone_ests=True)
        names, estimators = zip(*estimator_tuples)

        # validate names
        self._check_names(names)

        scitypes = self._get_pipeline_scitypes(estimator_tuples)
        if not set(scitypes).issubset(["forecaster", "transformer"]):
            raise TypeError(
                f"estimators passed to {type(self).__name__} "
                f"must be either transformer or forecaster"
            )
        if scitypes.count("forecaster") != 1:
            raise TypeError(
                f"exactly one forecaster must be contained in the chain, "
                f"but found {scitypes.count('forecaster')}"
            )

        forecaster_ind = self._get_forecaster_index(estimator_tuples)

        if not allow_postproc and forecaster_ind != len(estimators) - 1:
            TypeError(
                f"in {type(self).__name__}, last estimator must be a forecaster, "
                f"but found a transformer"
            )

        # Shallow copy
        return estimator_tuples

    def _iter_transformers(self, reverse=False, fc_idx=-1):

        # exclude final forecaster
        steps = self.steps_[:fc_idx]

        if reverse:
            steps = reversed(steps)

        for idx, (name, transformer) in enumerate(steps):
            yield idx, name, transformer

    def __len__(self):
        """Return the length of the Pipeline."""
        return len(self.steps)

    def _get_inverse_transform(self, transformers, y, X=None, mode=None):
        """Iterate over transformers.

        Inverse transform y (used for y_pred and pred_int)

        Parameters
        ----------
        transformers : list of (str, transformer) to apply
        y : pd.Series, pd.DataFrame
            Target series
        X : pd.Series, pd.DataFrame
            Exogenous series.
        mode : None or "proba"
            if proba, uses logic for probabilistic returns

        Returns
        -------
        y : pd.Series, pd.DataFrame
            Inverse transformed y
        """
        for _, transformer in reversed(transformers):
            # skip sktime transformers where inverse transform
            # is not wanted ur meaningful (e.g. Imputer, HampelFilter)
            skip_trafo = transformer.get_tag("skip-inverse-transform", False)
            if not skip_trafo:
                if mode is None:
                    y = transformer.inverse_transform(y, X)
                # if proba, we slice by quantile/coverage combination
                #   and collect the same quantile/coverage by variable
                #   then inverse transform, then concatenate
                elif mode == "proba":
                    idx = y.columns
                    n = idx.nlevels
                    idx_low = idx.droplevel(0).unique()
                    yt = dict()
                    for ix in idx_low:
                        levels = list(range(1, n))
                        if len(levels) == 1:
                            levels = levels[0]
                        yt[ix] = y.xs(ix, level=levels, axis=1)
                        # deal with the "Coverage" case, we need to get rid of this
                        #   i.d., special 1st level name of prediction objet
                        #   in the case where there is only one variable
                        if len(yt[ix].columns) == 1:
                            temp = yt[ix].columns
                            yt[ix].columns = self._y.columns
                        yt[ix] = transformer.inverse_transform(yt[ix], X)
                        if len(yt[ix].columns) == 1:
                            yt[ix].columns = temp
                    y = pd.concat(yt, axis=1)
                    flipcols = [n - 1] + list(range(n - 1))
                    y.columns = y.columns.reorder_levels(flipcols)
                else:
                    raise ValueError('mode arg must be None or "proba"')
        return y

    @property
    def named_steps(self):
        """Map the steps to a dictionary."""
        return dict(self.steps)

    def get_params(self, deep=True):
        """Get parameters for this estimator.

        Parameters
        ----------
        deep : boolean, optional, default=True
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

    # both children use the same step params for testing, so putting it here
    @classmethod
    def get_test_params(cls, parameter_set="default"):
        """Return testing parameter settings for the estimator.

        Parameters
        ----------
        parameter_set : str, default="default"
            Name of the set of test parameters to return, for use in tests. If no
            special parameters are defined for a value, will return `"default"` set.

        Returns
        -------
        params : dict or list of dict, default = {}
            Parameters to create testing instances of the class
            Each dict are parameters to construct an "interesting" test instance, i.e.,
            `MyClass(**params)` or `MyClass(**params[i])` creates a valid test instance.
            `create_test_instance` uses the first (or only) dictionary in `params`
        """
        from sklearn.preprocessing import StandardScaler

        from sktime.forecasting.arima import ARIMA
        from sktime.forecasting.naive import NaiveForecaster
        from sktime.transformations.series.adapt import TabularToSeriesAdaptor
        from sktime.transformations.series.exponent import ExponentTransformer

        # StandardScaler does not skip fit, NaiveForecaster is not probabilistic
        STEPS1 = [
            ("transformer", TabularToSeriesAdaptor(StandardScaler())),
            ("forecaster", NaiveForecaster()),
        ]
        params1 = {"steps": STEPS1}

        # ARIMA has probabilistic methods, ExponentTransformer skips fit
        STEPS2 = [
            ("transformer", ExponentTransformer()),
            ("forecaster", ARIMA()),
        ]
        params2 = {"steps": STEPS2}

        return [params1, params2]


# we ensure that internally we convert to pd.DataFrame for now
SUPPORTED_MTYPES = ["pd.DataFrame", "pd-multiindex", "pd_multiindex_hier"]


class ForecastingPipeline(_Pipeline):
    """Pipeline for forecasting with exogenous data.

    ForecastingPipeline is only applying the given transformers
    to X. The forecaster can also be a TransformedTargetForecaster containing
    transformers to transform y.

    Parameters
    ----------
    steps : list
        List of tuples like ("name", forecaster/transformer)

    Examples
    --------
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
    _tags = {
        "scitype:y": "both",
        "y_inner_mtype": SUPPORTED_MTYPES,
        "X_inner_mtype": SUPPORTED_MTYPES,
        "ignores-exogeneous-X": False,
        "requires-fh-in-fit": False,
        "handles-missing-data": False,
        "capability:pred_int": True,
    }

    def __init__(self, steps):
        self.steps = steps
        self.steps_ = self._check_steps(steps, allow_postproc=False)
        super(ForecastingPipeline, self).__init__()
        tags_to_clone = [
            "scitype:y",  # which y are fine? univariate/multivariate/both
            "ignores-exogeneous-X",  # does estimator ignore the exogeneous X?
            "capability:pred_int",  # can the estimator produce prediction intervals?
            "handles-missing-data",  # can estimator handle missing data?
            "requires-fh-in-fit",  # is forecasting horizon already required in fit?
            "X-y-must-have-same-index",  # can estimator handle different X/y index?
            "enforce_index_type",  # index type that needs to be enforced in X/y
        ]
        self.clone_tags(self.forecaster_, tags_to_clone)
        self._anytagis_then_set("fit_is_empty", False, True, self.steps_)

    @property
    def forecaster_(self):
        """Return reference to the forecaster in the pipeline. Valid after _fit."""
        return self.steps_[-1][1]

    def _fit(self, y, X=None, fh=None):
        """Fit to training data.

        Parameters
        ----------
        y : pd.Series, pd.DataFrame
            Target time series to which to fit the forecaster.
        fh : int, list or np.array, optional (default=None)
            The forecasters horizon with the steps ahead to to predict.
        X : pd.DataFrame, required
            Exogenous variables are ignored

        Returns
        -------
        self : returns an instance of self.
        """
        # If X is not given or ignored, just passthrough the data without transformation
        if self._X is not None and not self.get_tag("ignores-exogeneous-X"):
            # transform X
            for step_idx, name, transformer in self._iter_transformers():
                t = clone(transformer)
                X = t.fit_transform(X=X, y=y)
                self.steps_[step_idx] = (name, t)

        # fit forecaster
        name, forecaster = self.steps[-1]
        f = clone(forecaster)
        f.fit(y, X, fh)
        self.steps_[-1] = (name, f)

        return self

    def _predict(self, fh=None, X=None):
        """Forecast time series at future horizon.

        Parameters
        ----------
        fh : int, list, np.array or ForecastingHorizon
            Forecasting horizon
        X : pd.DataFrame, required
            Exogenous time series

        Returns
        -------
        y_pred : pd.Series
            Point predictions
        """
        X = self._transform(X=X)
        return self.forecaster_.predict(fh, X)

    def _predict_quantiles(self, fh, X=None, alpha=None):
        """Compute/return prediction quantiles for a forecast.

        private _predict_quantiles containing the core logic,
            called from predict_quantiles and possibly predict_interval

        State required:
            Requires state to be "fitted".

        Accesses in self:
            Fitted model attributes ending in "_"
            self.cutoff

        Parameters
        ----------
        fh : guaranteed to be ForecastingHorizon
            The forecasting horizon with the steps ahead to to predict.
        X : optional (default=None)
            guaranteed to be of a type in self.get_tag("X_inner_mtype")
            Exogeneous time series to predict from.
        alpha : list of float (guaranteed not None and floats in [0,1] interval)
            A list of probabilities at which quantile forecasts are computed.

        Returns
        -------
        pred_quantiles : pd.DataFrame
            Column has multi-index: first level is variable name from y in fit,
                second level being the quantile forecasts for each alpha.
                Quantile forecasts are calculated for each a in alpha.
            Row index is fh. Entries are quantile forecasts, for var in col index,
                at quantile probability in second-level col index, for each row index.
        """
        X = self._transform(X=X)
        return self.forecaster_.predict_quantiles(fh=fh, X=X, alpha=alpha)

    def _predict_interval(self, fh, X=None, coverage=None):
        """Compute/return prediction quantiles for a forecast.

        private _predict_interval containing the core logic,
            called from predict_interval and possibly predict_quantiles

        State required:
            Requires state to be "fitted".

        Accesses in self:
            Fitted model attributes ending in "_"
            self.cutoff

        Parameters
        ----------
        fh : guaranteed to be ForecastingHorizon
            The forecasting horizon with the steps ahead to to predict.
        X : optional (default=None)
            guaranteed to be of a type in self.get_tag("X_inner_mtype")
            Exogeneous time series to predict from.
        coverage : list of float (guaranteed not None and floats in [0,1] interval)
           nominal coverage(s) of predictive interval(s)

        Returns
        -------
        pred_int : pd.DataFrame
            Column has multi-index: first level is variable name from y in fit,
                second level coverage fractions for which intervals were computed.
                    in the same order as in input `coverage`.
                Third level is string "lower" or "upper", for lower/upper interval end.
            Row index is fh. Entries are forecasts of lower/upper interval end,
                for var in col index, at nominal coverage in second col index,
                lower/upper depending on third col index, for the row index.
                Upper/lower interval end forecasts are equivalent to
                quantile forecasts at alpha = 0.5 - c/2, 0.5 + c/2 for c in coverage.
        """
        X = self._transform(X=X)
        return self.forecaster_.predict_interval(fh=fh, X=X, coverage=coverage)

    def _predict_var(self, fh, X=None, cov=False):
        """Forecast variance at future horizon.

        private _predict_var containing the core logic, called from predict_var

        Parameters
        ----------
        fh : guaranteed to be ForecastingHorizon or None, optional (default=None)
            The forecasting horizon with the steps ahead to to predict.
            If not passed in _fit, guaranteed to be passed here
        X : pd.DataFrame, optional (default=None)
            Exogenous time series
        cov : bool, optional (default=False)
            if True, computes covariance matrix forecast.
            if False, computes marginal variance forecasts.

        Returns
        -------
        pred_var : pd.DataFrame, format dependent on `cov` variable
            If cov=False:
                Column names are exactly those of `y` passed in `fit`/`update`.
                    For nameless formats, column index will be a RangeIndex.
                Row index is fh. Entries are variance forecasts, for var in col index.
            If cov=True:
                Column index is a multiindex: 1st level is variable names (as above)
                    2nd level is fh.
                Row index is fh.
                Entries are (co-)variance forecasts, for var in col index, and
                    covariance between time index in row and col.
        """
        X = self._transform(X=X)
        return self.forecaster_.predict_var(fh=fh, X=X, cov=cov)

    def _predict_proba(self, fh, X, marginal=True):
        """Compute/return fully probabilistic forecasts.

        private _predict_proba containing the core logic, called from predict_proba

        Parameters
        ----------
        fh : guaranteed to be ForecastingHorizon
            The forecasting horizon with the steps ahead to to predict.
        X : optional (default=None)
            guaranteed to be of a type in self.get_tag("X_inner_mtype")
            Exogeneous time series to predict from.
        marginal : bool, optional (default=True)
            whether returned distribution is marginal by time index

        Returns
        -------
        pred_dist : tfp Distribution object
            if marginal=True:
                batch shape is 1D and same length as fh
                event shape is 1D, with length equal number of variables being forecast
                i-th (batch) distribution is forecast for i-th entry of fh
                j-th (event) index is j-th variable, order as y in `fit`/`update`
            if marginal=False:
                there is a single batch
                event shape is 2D, of shape (len(fh), no. variables)
                i-th (event dim 1) distribution is forecast for i-th entry of fh
                j-th (event dim 1) index is j-th variable, order as y in `fit`/`update`
        """
        X = self._transform(X=X)
        return self.forecaster_.predict_proba(fh=fh, X=X, marginal=marginal)

    def _update(self, y, X=None, update_params=True):
        """Update fitted parameters.

        Parameters
        ----------
        y : pd.Series
        X : pd.DataFrame, required
        update_params : bool, optional (default=True)

        Returns
        -------
        self : an instance of self
        """
        # If X is not given, just passthrough the data without transformation
        if X is not None:
            for _, _, transformer in self._iter_transformers():
                if hasattr(transformer, "update"):
                    transformer.update(X=X, y=y, update_params=update_params)
                    X = transformer.transform(X=X, y=y)

        _, forecaster = self.steps_[-1]
        forecaster.update(y=y, X=X, update_params=update_params)
        return self

    def _transform(self, X=None, y=None):
        # If X is not given or ignored, just passthrough the data without transformation
        if self._X is not None and not self.get_tag("ignores-exogeneous-X"):
            for _, _, transformer in self._iter_transformers():
                X = transformer.transform(X=X, y=y)
        return X


# removed transform and inverse_transform as long as y can only be a pd.Series
# def transform(self, Z, X=None):
#     self.check_is_fitted()
#     Zt = check_series(Z, enforce_multivariate=True)
#     for _, _, transformer in self._iter_transformers():
#         Zt = transformer.transform(Zt)
#     return Zt

# def inverse_transform(self, Z, X=None):
#     self.check_is_fitted()
#     Zt = check_series(Z, enforce_multivariate=True)
#     for _, _, transformer in self._iter_transformers(reverse=True):
#         if not _has_tag(transformer, "skip-inverse-transform"):
#             Zt = transformer.inverse_transform(Zt)
#     return Zt


class TransformedTargetForecaster(_Pipeline):
    """Meta-estimator for forecasting transformed time series.

    Pipeline functionality to apply transformers to the target series. The
    X data is not transformed. If you want to transform X, please use the
    ForecastingPipeline.

    For a list `t1`, `t2`, ..., `tN`, `f`, `tp1`, `tp2`, ..., `tpM`
        where `t[i]` and `tp[i]` are transformers (`t` to pre-, `tp` to post-process),
        and `f` is an sktime forecaster,
        the pipeline behaves as follows:
    `fit(y, X, fh)` - changes state by running `t1.fit_transform` with `X=y`, `y=X`
        then `t2.fit_transform` on `X=` the output of `t1.fit_transform`, `y=X`, etc
        sequentially, with `t[i]` receiving the output of `t[i-1]` as `X`,
        then running `f.fit` with `y` being the output of `t[N]`, and `X=X`,
        then running `tp1.fit_transform`  with `X=y`, `y=X`,
        then `tp2.fit_transform` on `X=` the output of `tp1.fit_transform`, etc
        sequentially, with `tp[i]` receiving the output of `tp[i-1]`,
    `predict(X, fh)` - result is of executing `f.predict`, with `X=X`, `fh=fh`,
        then running `tp1.inverse_transform` with `X=` the output of `f`, `y=X`,
        then `t2.inverse_transform` on `X=` the output of `t1.inverse_transform`, etc
        sequentially, with `t[i]` receiving the output of `t[i-1]` as `X`,
        then running `tp1.fit_transform` with `X=` the output of `t[N]s`, `y=X`,
        then `tp2.fit_transform` on `X=` the output of `tp1.fit_transform`, etc
        sequentially, with `tp[i]` receiving the output of `tp[i-1]`,
    `predict_interval(X, fh)`, `predict_quantiles(X, fh)` - as `predict(X, fh)`,
        with `predict_interval` or `predict_quantiles` substituted for `predict`
    `predict_var`, `predict_proba` - uses base class default to obtain
        crude estimates from `predict_quantiles`.
        Recommended to replace with better custom implementations if needed.

    `get_params`, `set_params` uses `sklearn` compatible nesting interface
        if list is unnamed, names are generated as names of classes
        if names are non-unique, `f"_{str(i)}"` is appended to each name string
            where `i` is the total count of occurrence of a non-unique string
            inside the list of names leading up to it (inclusive)

    `TransformedTargetForecaster` can also be created by using the magic multiplication
        on any forecaster, i.e., if `my_forecaster` inherits from `BaseForecaster`,
            and `my_t1`, `my_t2`, `my_tp` inherit from `BaseTransformer`,
            then, for instance, `my_t1 * my_t2 * my_forecaster * my_tp`
            will result in the same object as  obtained from the constructor
            `TransformedTargetForecaster([my_t1, my_t2, my_forecaster, my_tp])`
        magic multiplication can also be used with (str, transformer) pairs,
            as long as one element in the chain is a transformer

    Parameters
    ----------
    steps : list of sktime transformers and forecasters, or
        list of tuples (str, estimator) of sktime transformers or forecasters
            the list must contain exactly one forecaster
        these are "blueprint" transformers resp forecasters,
            forecaster/transformer states do not change when `fit` is called

    Attributes
    ----------
    steps_ : list of tuples (str, estimator) of sktime transformers or forecasters
        clones of estimators in `steps` which are fitted in the pipeline
        is always in (str, estimator) format, even if `steps` is just a list
        strings not passed in `steps` are replaced by unique generated strings
        i-th transformer in `steps_` is clone of i-th in `steps`
    forecaster_ : estimator, reference to the unique forecaster in steps_
    transformers_pre_ : list of tuples (str, transformer) of sktime transformers
        reference to pairs in steps_ that precede forecaster_
    transformers_ost_ : list of tuples (str, transformer) of sktime transformers
        reference to pairs in steps_ that succeed forecaster_

    Examples
    --------
    >>> from sktime.datasets import load_airline
    >>> from sktime.forecasting.naive import NaiveForecaster
    >>> from sktime.forecasting.compose import TransformedTargetForecaster
    >>> from sktime.transformations.series.impute import Imputer
    >>> from sktime.transformations.series.detrend import Deseasonalizer
    >>> from sktime.transformations.series.exponent import ExponentTransformer
    >>> y = load_airline()

    Example 1: string/estimator pairs
    >>> pipe = TransformedTargetForecaster(steps=[
    ...     ("imputer", Imputer(method="mean")),
    ...     ("detrender", Deseasonalizer()),
    ...     ("forecaster", NaiveForecaster(strategy="drift")),
    ... ])
    >>> pipe.fit(y)
    TransformedTargetForecaster(...)
    >>> y_pred = pipe.predict(fh=[1,2,3])

    Example 2: without strings
    >>> pipe = TransformedTargetForecaster([
    ...     Imputer(method="mean"),
    ...     Deseasonalizer(),
    ...     NaiveForecaster(strategy="drift"),
    ...     ExponentTransformer(),
    ... ])

    Example 3: using the dunder method
    >>> forecaster = NaiveForecaster(strategy="drift")
    >>> imputer = Imputer(method="mean")
    >>> pipe = imputer * Deseasonalizer() * forecaster * ExponentTransformer()
    """

    _required_parameters = ["steps"]
    _tags = {
        "scitype:y": "both",
        "y_inner_mtype": SUPPORTED_MTYPES,
        "X_inner_mtype": SUPPORTED_MTYPES,
        "ignores-exogeneous-X": False,
        "requires-fh-in-fit": False,
        "handles-missing-data": False,
        "capability:pred_int": True,
    }

    def __init__(self, steps):
        self.steps = steps
        self.steps_ = self._check_steps(steps, allow_postproc=True)
        super(TransformedTargetForecaster, self).__init__()

        # set the tags based on forecaster
        tags_to_clone = [
            "scitype:y",  # which y are fine? univariate/multivariate/both
            "ignores-exogeneous-X",  # does estimator ignore the exogeneous X?
            "capability:pred_int",  # can the estimator produce prediction intervals?
            "handles-missing-data",  # can estimator handle missing data?
            "requires-fh-in-fit",  # is forecasting horizon already required in fit?
            "X-y-must-have-same-index",  # can estimator handle different X/y index?
            "enforce_index_type",  # index type that needs to be enforced in X/y
        ]
        self.clone_tags(self.forecaster_, tags_to_clone)
        self._anytagis_then_set("fit_is_empty", False, True, self.steps_)

    @property
    def forecaster_(self):
        """Return reference to the forecaster in the pipeline.

        Returns
        -------
        sktime forecaster
            reference to unique forecaster in steps_ (without the name)
        """
        return self.steps_[self._get_forecaster_index(self.steps_)][1]

    @property
    def transformers_pre_(self):
        """Return reference to the list of pre-forecast transformers.

        Returns
        -------
        list of tuples (str, estimator) of sktime transformers
            reference to tuples that come before the unique (str, forecaster) in steps_
        """
        return self.steps_[: self._get_forecaster_index(self.steps_)]

    @property
    def transformers_post_(self):
        """Return reference to the list of post-forecast transformers.

        Returns
        -------
        list of tuples (str, estimator) of sktime transformers
            reference to tuples that come after the unique (str, forecaster) in steps_
        """
        return self.steps_[(1 + self._get_forecaster_index(self.steps_)) :]

    def __mul__(self, other):
        """Magic * method, return (right) concatenated TransformedTargetForecaster.

        Implemented for `other` being a transformer, otherwise returns `NotImplemented`.

        Parameters
        ----------
        other: `sktime` transformer, must inherit from BaseTransformer
            otherwise, `NotImplemented` is returned

        Returns
        -------
        TransformedTargetForecaster object,
            concatenation of `self` (first) with `other` (last).
            not nested, contains only non-TransformerPipeline `sktime` transformers
        """
        from sktime.transformations.base import BaseTransformer
        from sktime.transformations.compose import TransformerPipeline

        # we don't use names but _get_estimator_names to get the *original* names
        #   to avoid multiple "make unique" calls which may grow strings too much
        _, ests = zip(*self.steps_)
        names = tuple(self._get_estimator_names(self.steps))
        if isinstance(other, TransformerPipeline):
            _, trafos_o = zip(*other.steps_)
            names_o = tuple(other._get_estimator_names(other.steps))
            new_names = names + names_o
            new_ests = ests + trafos_o
        elif isinstance(other, BaseTransformer):
            new_names = names + (type(other).__name__,)
            new_ests = ests + (other,)
        elif self._is_name_and_est(other, BaseTransformer):
            other_name = other[0]
            other_trafo = other[1]
            new_names = names + (other_name,)
            new_ests = ests + (other_trafo,)
        else:
            return NotImplemented

        # if all the names are equal to class names, we eat them away
        if all(type(x[1]).__name__ == x[0] for x in zip(new_names, new_ests)):
            return TransformedTargetForecaster(steps=list(new_ests))
        else:
            return TransformedTargetForecaster(steps=list(zip(new_names, new_ests)))

    def __rmul__(self, other):
        """Magic * method, return (left) concatenated TransformerPipeline.

        Implemented for `other` being a transformer, otherwise returns `NotImplemented`.

        Parameters
        ----------
        other: `sktime` transformer, must inherit from BaseTransformer
            otherwise, `NotImplemented` is returned

        Returns
        -------
        TransformedTargetForecaster object,
            concatenation of `other` (first) with `self` (last).
            not nested, contains only non-TransformerPipeline `sktime` steps
        """
        from sktime.transformations.base import BaseTransformer
        from sktime.transformations.compose import TransformerPipeline

        _, ests = zip(*self.steps_)
        names = tuple(self._get_estimator_names(self.steps))
        if isinstance(other, TransformerPipeline):
            _, trafos_o = zip(*other.steps_)
            names_o = tuple(other._get_estimator_names(other.steps))
            new_names = names_o + names
            new_ests = trafos_o + ests
        elif isinstance(other, BaseTransformer):
            new_names = (type(other).__name__,) + names
            new_ests = (other,) + ests
        elif self._is_name_and_est(other, BaseTransformer):
            other_name = other[0]
            other_trafo = other[1]
            new_names = (other_name,) + names
            new_ests = (other_trafo,) + ests
        else:
            return NotImplemented

        # if all the names are equal to class names, we eat them away
        if all(type(x[1]).__name__ == x[0] for x in zip(new_names, new_ests)):
            return TransformedTargetForecaster(steps=list(new_ests))
        else:
            return TransformedTargetForecaster(steps=list(zip(new_names, new_ests)))

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
        self.steps_ = self._get_estimator_tuples(self.steps, clone_ests=True)

        # transform pre
        yt = y
        for _, t in self.transformers_pre_:
            yt = t.fit_transform(X=yt, y=X)

        # fit forecaster
        f = self.forecaster_
        f.fit(y=yt, X=X, fh=fh)

        # transform post
        for _, t in self.transformers_post_:
            y = t.fit_transform(X=y, y=X)

        return self

    def _predict(self, fh=None, X=None):
        """Forecast time series at future horizon.

        Parameters
        ----------
        fh : int, list, np.array or ForecastingHorizon
            Forecasting horizon
        X : pd.DataFrame, optional (default=None)
            Exogenous time series

        Returns
        -------
        y_pred : pd.Series
            Point predictions
        """
        y_pred = self.forecaster_.predict(fh=fh, X=X)
        # inverse transform y_pred
        y_pred = self._get_inverse_transform(self.transformers_pre_, y_pred, X)

        # transform post
        for _, t in self.transformers_post_:
            y_pred = t.transform(X=y_pred, y=X)

        return y_pred

    def _update(self, y, X=None, update_params=True):
        """Update fitted parameters.

        Parameters
        ----------
        y : pd.Series
        X : pd.DataFrame, optional (default=None)
        update_params : bool, optional (default=True)

        Returns
        -------
        self : an instance of self
        """
        # transform pre
        for _, t in self.transformers_pre_:
            if hasattr(t, "update"):
                t.update(X=y, y=X, update_params=update_params)
                y = t.transform(X=y, y=X)

        self.forecaster_.update(y=y, X=X, update_params=update_params)

        # transform post
        for _, t in self.transformers_post_:
            t.update(X=y, y=X, update_params=update_params)
            y = t.transform(X=y, y=X)

        return self

    def transform(self, Z, X=None):
        """Return transformed version of input series `Z`.

        Parameters
        ----------
        Z : pd.Series or pd.DataFrame
            A time series to apply the transformation on.
        X : pd.DataFrame, default=None
            Exogenous data used in transformation.

        Returns
        -------
        Zt : pd.Series or pd.DataFrame
            Transformed version of input series `Z`.
        """
        self.check_is_fitted()
        zt = check_series(Z)
        for _, transformer in self.transformers_pre_:
            zt = transformer.transform(zt, X)
        return zt

    def inverse_transform(self, Z, X=None):
        """Reverse transformation on input series `Z`.

        Parameters
        ----------
        Z : pd.Series or pd.DataFrame
            A time series to reverse the transformation on.
        X : pd.DataFrame, default=None
            Exogenous data used in transformation.

        Returns
        -------
        Z_inv : pd.Series or pd.DataFrame
            The reconstructed timeseries after the transformation has been reversed.
        """
        self.check_is_fitted()
        Z = check_series(Z)
        return self._get_inverse_transform(self.transformers_pre_, Z, X)

    def _predict_quantiles(self, fh, X=None, alpha=None):
        """Compute/return prediction quantiles for a forecast.

        private _predict_quantiles containing the core logic,
            called from predict_quantiles and possibly predict_interval

        State required:
            Requires state to be "fitted".

        Accesses in self:
            Fitted model attributes ending in "_"
            self.cutoff

        Parameters
        ----------
        fh : guaranteed to be ForecastingHorizon
            The forecasting horizon with the steps ahead to to predict.
        X : optional (default=None)
            guaranteed to be of a type in self.get_tag("X_inner_mtype")
            Exogeneous time series to predict from.
        alpha : list of float (guaranteed not None and floats in [0,1] interval)
            A list of probabilities at which quantile forecasts are computed.

        Returns
        -------
        pred_quantiles : pd.DataFrame
            Column has multi-index: first level is variable name from y in fit,
                second level being the quantile forecasts for each alpha.
                Quantile forecasts are calculated for each a in alpha.
            Row index is fh. Entries are quantile forecasts, for var in col index,
                at quantile probability in second-level col index, for each row index.
        """
        pred_int = self.forecaster_.predict_quantiles(fh=fh, X=X, alpha=alpha)
        pred_int_transformed = self._get_inverse_transform(
            self.transformers_pre_, pred_int, mode="proba"
        )
        return pred_int_transformed

    def _predict_interval(self, fh, X=None, coverage=None):
        """Compute/return prediction quantiles for a forecast.

        private _predict_interval containing the core logic,
            called from predict_interval and possibly predict_quantiles

        State required:
            Requires state to be "fitted".

        Accesses in self:
            Fitted model attributes ending in "_"
            self.cutoff

        Parameters
        ----------
        fh : guaranteed to be ForecastingHorizon
            The forecasting horizon with the steps ahead to to predict.
        X : optional (default=None)
            guaranteed to be of a type in self.get_tag("X_inner_mtype")
            Exogeneous time series to predict from.
        coverage : list of float (guaranteed not None and floats in [0,1] interval)
           nominal coverage(s) of predictive interval(s)

        Returns
        -------
        pred_int : pd.DataFrame
            Column has multi-index: first level is variable name from y in fit,
                second level coverage fractions for which intervals were computed.
                    in the same order as in input `coverage`.
                Third level is string "lower" or "upper", for lower/upper interval end.
            Row index is fh. Entries are forecasts of lower/upper interval end,
                for var in col index, at nominal coverage in second col index,
                lower/upper depending on third col index, for the row index.
                Upper/lower interval end forecasts are equivalent to
                quantile forecasts at alpha = 0.5 - c/2, 0.5 + c/2 for c in coverage.
        """
        pred_int = self.forecaster_.predict_interval(fh=fh, X=X, coverage=coverage)
        pred_int_transformed = self._get_inverse_transform(
            self.transformers_pre_, pred_int, mode="proba"
        )
        return pred_int_transformed
