import numpy as np
import pandas as pd
from sklearn.utils import check_random_state
from sktime.transformers.series_as_features.base import \
    BaseSeriesAsFeaturesTransformer
from sktime.utils.data_container import concat_nested_arrays
from sktime.utils.data_container import get_time_index
from sktime.utils.data_container import tabularize
from sktime.utils.time_series import compute_relative_to_n_timepoints
from sktime.utils.validation import is_int
from sktime.utils.validation.series_as_features import check_X
from sktime.utils.load_data import load_from_tsfile_to_dataframe as load_ts


class IntervalSegmenter(BaseSeriesAsFeaturesTransformer):
    """
    Interval segmentation transformer.

    Parameters
    ----------
    intervals : int, np.ndarray or list of np.ndarrays with one for each
    column of input data.
        Intervals to generate.
        - If int, intervals are generated.
        - If ndarray, 2d np.ndarray [n_intervals, 2] with rows giving
        intervals, the first column giving start points,
        and the second column giving end points of intervals
    """

    def __init__(self, intervals=10):
        self.intervals = intervals
        self._time_index = []
        self.input_shape_ = ()
        super(IntervalSegmenter, self).__init__()

    def fit(self, X, y=None):
        """
        Fit transformer, generating random interval indices.

        Parameters
        ----------
        X : pandas DataFrame of shape [n_samples, n_features]
            Input data
        y : pandas Series, shape (n_samples, ...), optional
            Targets for supervised learning.

        Returns
        -------
        self : an instance of self.
        """
        X = check_X(X, enforce_univariate=True)

        self.input_shape_ = X.shape

        # Retrieve time-series indexes from each column.
        self._time_index = get_time_index(X)

        if isinstance(self.intervals, np.ndarray):
            self.intervals_ = self.intervals

        elif is_int(self.intervals):
            self.intervals_ = np.array_split(self._time_index, self.intervals)

        else:
            raise ValueError(
                f"Intervals must be either an integer, an array with "
                f"start and end points, but found: {self.intervals}")
        self._is_fitted = True
        return self

    def transform(self, X, y=None):
        """
        Transform X, segments time-series in each column into random
        intervals using interval indices generated
        during `fit`.

        Parameters
        ----------
        X : nested pandas DataFrame of shape [n_samples, n_features]
            Nested dataframe with time-series in cells.

        Returns
        -------
        Xt : pandas DataFrame
          Transformed pandas DataFrame with same number of rows and one
          column for each generated interval.
        """

        # Check inputs.
        self.check_is_fitted()
        X = check_X(X)

        # Check that the input is of the same shape as the one passed
        # during fit.
        if X.shape[1] != self.input_shape_[1]:
            raise ValueError(
                'Number of columns of input is different from what was seen'
                'in `fit`')
        # # Input validation
        # if not all([np.array_equal(fit_idx, trans_idx)
        #             for trans_idx, fit_idx in zip(check_equal_index(X),
        #             self._time_index)]):
        #     raise ValueError('Indexes of input time-series are different
        #     from what was seen in `fit`')

        # Segment into intervals.
        # TODO generalise to non-equal-index cases
        intervals = []
        colname = X.columns[0]
        colnames = []
        # Tabularise assuming series
        arr = tabularize(X, return_array=True)
        # have equal indexes in any given column
        for start, end in self.intervals_:
            interval = arr[:, start:end]
            intervals.append(interval)
            colnames.append(f"{colname}_{start}_{end}")

        # Return nested pandas DataFrame.
        Xt = pd.DataFrame(concat_nested_arrays(intervals, return_arrays=True))
        Xt.columns = colnames
        return Xt


class RandomIntervalSegmenter(IntervalSegmenter):
    """Transformer that segments time-series into random intervals with
    random starting points and lengths. Some
    intervals may overlap and may be duplicates.

    Parameters
    ----------
    n_intervals : str, int or float
        Number of intervals to generate.
        - If "log", log of m is used where m is length of time series.
        - If "sqrt", sqrt of m is used.
        - If "random", random number of intervals is generated.
        - If int, n_intervals intervals are generated.
        - If float, int(n_intervals * m) is used with n_intervals giving the
        fraction of intervals of the
        time series length.

        For all arguments relative to the length of the time series,
        the generated number of intervals is
        always at least 1.

        Default is "sqrt".

    random_state : int, RandomState instance or None, optional (default=None)
        If int, random_state is the seed used by the random number generator;
        If RandomState instance, random_state is the random number generator;
        If None, the random number generator is the RandomState instance used
        by `np.random`.
    """

    def __init__(self, n_intervals='sqrt', min_length=2, random_state=None):
        self.min_length = min_length
        self.n_intervals = n_intervals
        self.random_state = random_state
        super(RandomIntervalSegmenter, self).__init__()

    def fit(self, X, y=None):
        """
        Fit transformer, generating random interval indices.

        Parameters
        ----------
        X : pandas DataFrame of shape [n_samples, n_features]
            Input data
        y : pandas Series, shape (n_samples, ...), optional
            Targets for supervised learning.

        Returns
        -------
        self : RandomIntervalSegmenter
            This estimator
        """
        if not isinstance(self.min_length, int):
            raise ValueError(f"Min_lenght must be an integer, but found: "
                             f"{type(self.min_length)}")
        if self.min_length < 1:
            raise ValueError(f"Min_lenght must be an positive integer (>= 1), "
                             f"but found: {self.min_length}")
        X = check_X(X)
        self.input_shape_ = X.shape

        # Retrieve time-series indexes from each column.
        # TODO generalise to columns with series of unequal length
        self._time_index = get_time_index(X)

        # Compute random intervals for each column.
        # TODO if multiple columns are passed, introduce option to compute
        #  one set of shared intervals,
        #  or rely on ColumnTransformer?
        if self.n_intervals == 'random':
            self.intervals_ = self._rand_intervals_rand_n(self._time_index)
        else:
            self.intervals_ = self._rand_intervals_fixed_n(
                self._time_index,
                n_intervals=self.n_intervals)
        self._is_fitted = True
        return self

    def _rand_intervals_rand_n(self, x):
        """
        Compute a random number of intervals from index (x) with
        random starting points and lengths. Intervals are unique, but may
        overlap.

        Parameters
        ----------
        x : array_like, shape = [n_observations]

        Returns
        -------
        intervals : array-like, shape = [n, 2]
            2d array containing start and end points of intervals

        References
        ----------
        ..[1] Deng, Houtao, et al. "A time series forest for classification
        and feature extraction."
            Information Sciences 239 (2013): 142-153.
        """
        rng = check_random_state(self.random_state)
        starts = []
        ends = []
        n_timepoints = x.shape[0]  # series length
        W = rng.randint(1, n_timepoints, size=int(np.sqrt(n_timepoints)))
        for w in W:
            size = n_timepoints - w + 1
            start = rng.randint(size, size=int(np.sqrt(size)))
            starts.extend(start)
            for s in start:
                end = s + w
                ends.append(end)
        return np.column_stack([starts, ends])

    def _rand_intervals_fixed_n(self, x, n_intervals):
        """
        Compute a fixed number (n) of intervals from index (x) with
        random starting points and lengths. Intervals may overlap and may
        not be unique.

        Parameters
        ----------
        x : array_like, shape = [n_observations,]
            Array containing the time-series index.
        n_intervals : 'sqrt', 'log', float or int

        Returns
        -------
        intervals : array-like, shape = [n, 2]
            2d array containing start and end points of intervals
        """
        rng = check_random_state(self.random_state)
        n_timepoints = len(x)
        # compute number of random intervals relative to series length (m)
        # TODO use smarter dispatch at construction to avoid evaluating
        #  if-statements here each time function is called
        n_intervals = compute_relative_to_n_timepoints(n_timepoints,
                                                       n=n_intervals)

        # get start and end points of intervals
        starts = rng.randint(n_timepoints - self.min_length + 1,
                             size=n_intervals)
        if n_intervals == 1:
            starts = [starts]  # make it an iterable
        ends = [start + rng.randint(self.min_length,
                                    n_timepoints - start + 1) for start
                in starts]
        return np.column_stack([starts, ends])
        