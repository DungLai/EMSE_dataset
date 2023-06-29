# -*- coding: utf-8 -*-
"""Lagging transformer."""
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)

__author__ = ["fkiraly"]

import pandas as pd

from sktime.transformations.base import BaseTransformer
from sktime.utils.multiindex import flatten_multiindex


class Lag(BaseTransformer):
    """Lagging transformer. Lags time series by one or multiple lags.

    Transforms a time series into a lagged version of itself.
    Multiple lags can be provided, as a list.
    Estimator-like wrapper of pandas.shift and integer index lagging.

    Lags can be provided as a simple offset, `lags`, or pair of (lag count, frequency),
    with lag count an int (`lags` arg) and frequency a `pandas` frequency descriptor.

    When multiple lags are provided, multiple column concatenated copies of the lagged
    time series will be created.
    Names of columns are lagname__variablename, where lagname describes the lag/freq.

    If data was provided in _fit or _update, Lag transformer memorizes those indices
    and uses them for computing lagged values.
    To use only data seen in transform, use the FitInTransform compositor.

    Parameters
    ----------
    lags : lag offset, or list of lag offsets, optional, default=0 (identity transform)
        a "lag offset" can be one of the following:
        int - number of periods to shift/lag
        time-like: DateOffset, tseries.offsets, or timedelta
            time delta offset to shift/lag
            requires time index of transformed data to be time-like (not int)
        str - time rule from pandas.tseries module, e.g., "EOM"
    freq : frequency descriptor of list of frequency descriptors, optional, default=None
        if passed, must be scalar, or list of equal length to "lags" argument
        elements in freq correspond to elements in lags
        if i-th element of freq is not None, i-th element of lags must be int
            this is called the "corresponding lags element" below
        "frequency descriptor" can be one of the following:
        time-like: DateOffset, tseries.offsets, or timedelta
            multiplied to corresponding "lags" element when shifting
        str - offset from pd.tseries module, e.g., "D", "M", or time rule, e.g., "EOM"
    index_out : str, optional, one of "shift", "original", "extend", default="extend"
        determines set of output indices in lagged time series
        "shift" - only shifted indices are retained.
            Will not create NA for single lag, but can create NA for multiple lags.
        "original" - only original indices are retained. Will usually create NA.
        "extend" - both original indices and shifted indices are retained.
            Will usually create NA, possibly many, if shifted/original do not intersect.
    flatten_transform_index : bool, optional (default=True)
        if True, columns of return DataFrame are flat, by "lagname__variablename"
        if False, columns are MultiIndex (lagname, variablename)
        has no effect if return mtype is one without column names

    Examples
    --------
    >>> from sktime.datasets import load_airline
    >>> from sktime.transformations.series.lag import Lag
    >>> X = load_airline()

    Single lag will yield a time series with the same variables:
    >>> t = Lag(2)
    >>> Xt = t.fit_transform(X)

    Multiple lags can be provided, this will result in multiple columns:
    >>> t = Lag([2, 4, -1])
    >>> Xt = t.fit_transform(X)

    The default setting of index_out will extend indices either side.
    To ensure that the index remains the same after transform, use index_out="original"
    >>> t = Lag([2, 4, -1], index_out="original")
    >>> Xt = t.fit_transform(X)

    The lag transformer may (and usually will) create NAs.
    (except when index_out="shift" and there is only a single lag, or in trivial cases)
    This may need to be handled, e.g., if a subsequent pipeline step does not accept NA.
    To deal with the NAs, pipeline with the Imputer:
    >>> from sktime.datasets import load_airline
    >>> from sktime.transformations.series.impute import Imputer
    >>> from sktime.transformations.series.lag import Lag
    >>> X = load_airline()
    >>>
    >>> t = Lag([2, 4, -1]) * Imputer("nearest")
    >>> Xt = t.fit_transform(X)
    """

    _tags = {
        "scitype:transform-input": "Series",
        # what is the scitype of X: Series, or Panel
        "scitype:transform-output": "Series",
        # what scitype is returned: Primitives, Series, Panel
        "scitype:instancewise": True,  # is this an instance-wise transform?
        "capability:inverse_transform": False,  # can the transformer inverse transform?
        "univariate-only": False,  # can the transformer handle multivariate X?
        "X_inner_mtype": "pd.DataFrame",  # which mtypes do _fit/_predict support for X?
        "y_inner_mtype": "None",  # which mtypes do _fit/_predict support for y?
        "fit_is_empty": False,  # is fit empty and can be skipped? Yes = True
        "transform-returns-same-time-index": False,
        # does transform return have the same time index as input X
        "skip-inverse-transform": True,  # is inverse-transform skipped when called?
        "capability:unequal_length": True,
        "capability:unequal_length:removes": False,
        "handles-missing-data": True,  # can estimator handle missing data?
        "capability:missing_values:removes": False,
    }

    # todo: add any hyper-parameters and components to constructor
    def __init__(
        self,
        lags=0,
        freq=None,
        index_out="extend",
        flatten_transform_index=True,
    ):

        self.lags = lags
        self.freq = freq
        self.index_out = index_out
        self.flatten_transform_index = flatten_transform_index

        if index_out not in ["shift", "extend", "original"]:
            raise ValueError(
                'index_out must be one of the strings "shift", "extend", "original"'
                f'but found "{index_out}"'
            )

        # _lags and _freq are list-coerced variants of lags, freq
        if not isinstance(lags, list):
            self._lags = [lags]
        else:
            self._lags = lags

        if not isinstance(freq, list):
            # if freq is a single value, expand it to length of lags
            self._freq = [freq] * len(self._lags)
        else:
            self._freq = freq

        msg = "freq must be a list of equal length to lags, or a scalar."
        assert len(self._lags) == len(self._freq), msg

        super(Lag, self).__init__()

        if index_out == "original":
            self.set_tags(**{"transform-returns-same-time-index": True})

    def _yield_shift_params(self):
        """Yield (periods, freq) pairs to pass to pandas.DataFrame.shift."""
        for lag, freq in zip(self._lags, self._freq):
            if not isinstance(lag, int):
                yield 1, lag
            elif lag is None:
                yield 1, freq
            else:
                yield lag, freq

    def _yield_shift_param_names(self):
        """Yield string representation of (periods, freq) pairs."""
        for lag, freq in self._yield_shift_params():
            if freq is None:
                name = str(lag)
            elif lag is None:
                name = str(freq)
            else:
                name = f"{lag}{freq}"
            name = "lag_" + name
            yield name

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
        # remember X for lagging across past data indices
        self._X = X

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
        index_out = self.index_out

        X_orig_idx = X.index
        X = X.combine_first(self._X).copy()

        shift_params = list(self._yield_shift_params())

        Xt_list = []

        for lag, freq in shift_params:
            # need to deal separately with RangeIndex
            # because shift always cuts off the end values
            INT_INDEX_TYPES = (pd.RangeIndex, pd.Int64Index)
            if isinstance(lag, int) and isinstance(X.index, INT_INDEX_TYPES):
                Xt = X.copy()
                Xt.index = X.index + lag
                X_orig_idx_shifted = X_orig_idx + lag
            else:
                X_orig_idx_shifted = X_orig_idx.shift(periods=lag, freq=freq)
                if isinstance(lag, int) and freq is None:
                    freq = "infer"
                Xt = X.copy().shift(periods=lag, freq=freq)
            # extend index to include original, if "extend" or "original"
            if index_out in ["extend", "original"]:
                X_idx = pd.DataFrame(index=X_orig_idx)
                Xt = Xt.combine_first(X_idx)
            # sub-set to original plus shifted, if "extend"
            # this is necessary, because we added indices from _X above
            if index_out == "extend":
                X_orig_idx_extended = X_orig_idx_shifted.union(X_orig_idx)
                Xt = Xt.loc[X_orig_idx_extended]
            # sub-set to original, if "original"
            if index_out == "original":
                Xt = Xt.loc[X_orig_idx]
            # sub-set to shifted index, if "shifted"
            # this is necessary, because we added indices from _X above
            if index_out == "shifted":
                Xt = Xt.loc[X_orig_idx_shifted]

            Xt_list.append(Xt)

        if len(Xt_list) == 1:
            Xt = Xt_list[0]
        else:
            lag_names = self._yield_shift_param_names()
            Xt = pd.concat(Xt_list, axis=1, keys=lag_names, names=["lag", "variable"])
            if self.flatten_transform_index:
                Xt.columns = flatten_multiindex(Xt.columns)

        return Xt

    # todo: consider implementing this, optional
    # if not implementing, delete the _inverse_transform method
    # inverse transform exists only if transform does not change scitype
    #  i.e., Series transformed to Series
    def _inverse_transform(self, X, y=None):
        """Inverse transform, inverse operation to transform.

        private _inverse_transform containing core logic, called from inverse_transform

        Parameters
        ----------
        X : Series or Panel of mtype X_inner_mtype
            if X_inner_mtype is list, _inverse_transform must support all types in it
            Data to be inverse transformed
        y : Series or Panel of mtype y_inner_mtype, optional (default=None)
            Additional data, e.g., labels for transformation

        Returns
        -------
        inverse transformed version of X
        """
        # implement here
        # IMPORTANT: avoid side effects to X, y
        #
        # type conventions are exactly those in _transform, reversed
        #
        # for example: if transform-output is "Series":
        #  return should be of same mtype as input, X_inner_mtype
        #  if multiple X_inner_mtype are supported, ensure same input/output
        #
        # todo: add the return mtype/scitype to the docstring, e.g.,
        #  Returns
        #  -------
        #  X_inv_transformed : Series of mtype pd.DataFrame
        #       inverse transformed version of X

    def _update(self, X, y=None):
        """Update transformer with X and y.

        private _update containing the core logic, called from update

        Parameters
        ----------
        X : Series or Panel of mtype X_inner_mtype
            if X_inner_mtype is list, _update must support all types in it
            Data to update transformer with
        y : Series or Panel of mtype y_inner_mtype, default=None
            Additional data, e.g., labels for tarnsformation

        Returns
        -------
        self: reference to self
        """
        self._X = X.combine_first(self._X)

    # todo: return default parameters, so that a test instance can be created
    #   required for automated unit and integration testing of estimator
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
        params1 = {"lags": 2, "index_out": "original"}
        params2 = {"lags": [-1, 4]}
        params3 = {"lags": [-1, 0, 1], "index_out": "shift"}

        return [params1, params2, params3]