# -*- coding: utf-8 -*-
import sys

import numpy as np
import pandas as pd
import scipy.stats
from sktime.transformers.series_as_features.base import BaseSeriesAsFeaturesTransformer
from sktime.transformers.series_as_features.dictionary_based import PAA
from sktime.utils.data_container import from_nested_to_2d_numpy

#    TO DO: verify this returned pandas is consistent with sktime
#    definition. Timestamps?
from sktime.utils.validation.series_as_features import check_X

# from numba import types
# from numba.experimental import jitclass

__author__ = "Matthew Middlehurst"


class SAX(BaseSeriesAsFeaturesTransformer):
    """SAX (Symbolic Aggregate approXimation) Transformer, as described in
    Jessica Lin, Eamonn Keogh, Li Wei and Stefano Lonardi,
    "Experiencing SAX: a novel symbolic representation of time series"
    Data Mining and Knowledge Discovery, 15(2):107-144
    Overview: for each series:
        run a sliding window across the series
        for each window
            shorten the series with PAA (Piecewise Approximate Aggregation)
            discretise the shortened series into fixed bins
            form a word from these discrete values
    by default SAX produces a single word per series (window_size=0).
    SAX returns a pandas data frame where column 0 is the histogram (sparse
    pd.series)
    of each series.

    Parameters
    ----------
        word_length:         int, length of word to shorten window to (using
        PAA) (default 8)
        alphabet_size:       int, number of values to discretise each value
        to (default to 4)
        window_size:         int, size of window for sliding. Input series
        length for whole series transform (default to 12)
        remove_repeat_words: boolean, whether to use numerosity reduction (
        default False)
        save_words:          boolean, whether to use numerosity reduction (
        default False)

        return_pandas_data_series:          boolean, default = True
            set to true to return Pandas Series as a result of transform.
            setting to true reduces speed significantly but is required for
            automatic test.

    Attributes
    ----------
        words:      histor = []

    """

    def __init__(
        self,
        word_length=8,
        alphabet_size=4,
        window_size=12,
        remove_repeat_words=False,
        save_words=False,
        return_pandas_data_series=True,
    ):
        self.word_length = word_length
        self.alphabet_size = alphabet_size
        self.window_size = window_size
        self.remove_repeat_words = remove_repeat_words
        self.save_words = save_words
        self.return_pandas_data_series = return_pandas_data_series
        self.words = []

        super(SAX, self).__init__()

    def transform(self, X, y=None):
        """

        Parameters
        ----------
        X : nested pandas DataFrame of shape [n_instances, 1]
            Nested dataframe with univariate time-series in cells.

        Returns
        -------
        dims: Pandas data frame with first dimension in column zero
        """
        self.check_is_fitted()
        X = check_X(X, enforce_univariate=True)
        X = from_nested_to_2d_numpy(X, return_array=True)

        if self.alphabet_size < 2 or self.alphabet_size > 4:
            raise RuntimeError("Alphabet size must be an integer between 2 and 4")
        if self.word_length < 1 or self.word_length > 16:
            raise RuntimeError("Word length must be an integer between 1 and 16")

        breakpoints = self._generate_breakpoints()
        n_instances, series_length = X.shape

        bags = pd.DataFrame()
        dim = []

        for i in range(n_instances):
            bag = {}
            lastWord = -1

            words = []

            num_windows_per_inst = series_length - self.window_size + 1
            split = np.array(
                X[
                    i,
                    np.arange(self.window_size)[None, :]
                    + np.arange(num_windows_per_inst)[:, None],
                ]
            )

            split = scipy.stats.zscore(split, axis=1)

            paa = PAA(num_intervals=self.word_length)
            data = pd.DataFrame()
            data[0] = [pd.Series(x, dtype=np.float32) for x in split]
            patterns = paa.fit_transform(data)
            patterns = np.asarray([a.values for a in patterns.iloc[:, 0]])

            for n in range(patterns.shape[0]):
                pattern = patterns[n, :]
                word = self._create_word(pattern, breakpoints)
                words.append(word)
                lastWord = self._add_to_bag(bag, word, lastWord)

            if self.save_words:
                self.words.append(words)

            dim.append(pd.Series(bag) if self.return_pandas_data_series else bag)

        bags[0] = dim

        return bags

    def _create_word(self, pattern, breakpoints):
        word = 0
        for i in range(self.word_length):
            for bp in range(self.alphabet_size):
                if pattern[i] <= breakpoints[bp]:
                    word = (word << 2) | bp
                    break

        return word

    def _add_to_bag(self, bag, word, last_word):
        if self.remove_repeat_words and word == last_word:
            return False

        bag[word] = bag.get(word, 0) + 1

        return True

    def _generate_breakpoints(self):
        # Pre-made gaussian curve breakpoints from UEA TSC codebase
        return {
            2: [0, sys.float_info.max],
            3: [-0.43, 0.43, sys.float_info.max],
            4: [-0.67, 0, 0.67, sys.float_info.max],
            5: [-0.84, -0.25, 0.25, 0.84, sys.float_info.max],
            6: [-0.97, -0.43, 0, 0.43, 0.97, sys.float_info.max],
            7: [-1.07, -0.57, -0.18, 0.18, 0.57, 1.07, sys.float_info.max],
            8: [-1.15, -0.67, -0.32, 0, 0.32, 0.67, 1.15, sys.float_info.max],
            9: [-1.22, -0.76, -0.43, -0.14, 0.14, 0.43, 0.76, 1.22, sys.float_info.max],
            10: [
                -1.28,
                -0.84,
                -0.52,
                -0.25,
                0.0,
                0.25,
                0.52,
                0.84,
                1.28,
                sys.float_info.max,
            ],
        }[self.alphabet_size]


class _BitWord(object):
    # Used to represent a word for dictionary based classifiers such as BOSS
    # an BOP.
    # Can currently only handle an alphabet size of <= 4 and word length of
    # <= 16.
    # Current literature shows little reason to go beyond this, but the
    # class will need changes/expansions
    # if this is needed.
    # TODO a shift of 2 is only correct for alphabet size 4, log2(4)=2

    @staticmethod
    def create_bigram_word(word, other_word, length):
        return (word << length) | other_word

    @classmethod
    def shorten_word(cls, word, amount):
        # shorten a word by set amount of letters
        return cls.right_shift(word, amount * 2)

    @classmethod
    def word_list(cls, word, length):
        # list of input integers to obtain current word
        word_list = []
        shift = 32 - (length * 2)

        for _ in range(length - 1, -1, -1):
            word_list.append(cls.right_shift(word << shift, 32 - 2))
            shift += 2

        return word_list

    @staticmethod
    def right_shift(left, right):
        return (left % 0x100000000) >> right
