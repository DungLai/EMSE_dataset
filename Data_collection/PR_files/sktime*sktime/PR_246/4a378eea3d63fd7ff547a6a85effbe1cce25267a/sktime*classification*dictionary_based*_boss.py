""" BOSS classifiers
dictionary based BOSS classifiers based on SFA transform. Contains a single
BOSS and a BOSS ensemble
"""

__author__ = "Matthew Middlehurst"
__all__ = ["BOSSEnsemble", "BOSSIndividual", "boss_distance"]

import math
import random
import sys
import time
from itertools import compress

import numpy as np
from sklearn.utils.multiclass import class_distribution
from sktime.classification.base import BaseClassifier
from sktime.transformers.series_as_features.dictionary_based import SFA
from sktime.utils.validation.series_as_features import check_X
from sktime.utils.validation.series_as_features import check_X_y


# TO DO: Make more efficient


class BOSSEnsemble(BaseClassifier):
    """ Bag of SFA Symbols (BOSS)

    Bag of SFA Symbols Ensemble: implementation of BOSS from Schafer:
    @article
    {schafer15boss,
     author = {Patrick SchÃ¤fer,
            title = {The BOSS is concerned with time series classification
            in the presence of noise},
            journal = {Data Mining and Knowledge Discovery},
            volume = {29},
            number= {6},
            year = {2015}
    }
    Overview: Input n series length m
    BOSS performs a gird search over a set of parameter values, evaluating
    each with a LOOCV. If then retains
    all ensemble members within 92% of the best. There are three primary
    parameters:
            alpha: alphabet size
            w: window length
            l: word length.
    for any combination, a single BOSS slides a window length w along the
    series. The w length window is shortened to
    an l length word through taking a Fourier transform and keeping the
    first l/2 complex coefficients. These l
    coefficents are then discretised into alpha possible values, to form a
    word length l. A histogram of words for each
    series is formed and stored. fit involves finding n histograms.

    predict uses 1 nearest neighbour with a bespoke distance function.

    For the Java version, see
    https://github.com/uea-machine-learning/tsml/blob/master/src/main/java
    /timeseriesweka/classifiers/dictionary_based/BOSS.java


    Parameters
    ----------
    randomised_ensemble     : bool, turns the option to just randomise the
    ensemble members rather than cross validate (default=False)
    n_parameter_samples     : int, if search is randomised, number of
    parameter combos to try
    random_state            : int or None, seed for random, integer,
    optional (default to no seed)
    threshold               : double [0,1]. retain all classifiers within
    threshold% of the best one, optional (default =0.92)
    max_ensemble_size       : int or None, retain a maximum number of
    classifiers, even if within threshold, optional (default = 500)
    alphabet_size           : range of alphabet sizes to try (default to
    single value, 4)
    max_win_len_prop        : maximum window length as a proportion of
    series length (default =1)
    time_limit              : time contract to limit build time in minutes (
    default=0, no limit)
    word_lengths            : search range for word lengths (default =[16,
    14, 12, 10, 8])
    alphabet_size           : range of alphabet size to search for (default,
    a single value a=4),
    min_window              : minimum window size, (default=10),
    norm_options            : search space for normalise, not normalise (
    default [True, False])

    Attributes
    ----------
    n_classes               : extracted from the data
    n_instances             : extracted from the data
    n_estimators           : The final number of classifiers used (
    <=max_ensemble_size)
    series_length           : length of all series (assumed equal)
    classifiers             : array of DecisionTree classifiers
    weights                 : weight of each classifier in the ensemble

    """

    def __init__(self,
                 randomised_ensemble=False,
                 n_parameter_samples=250,
                 random_state=None,
                 threshold=0.92,
                 max_ensemble_size=None,
                 max_win_len_prop=1,
                 time_limit=0.0,
                 word_lengths=None,
                 alphabet_size=4,
                 min_window=10,
                 norm_options=None
                 ):
        if word_lengths is None:
            word_lengths = [16, 14, 12, 10, 8]
        if norm_options is None:
            norm_options = [True, False]

        if max_ensemble_size is None:
            if randomised_ensemble:
                max_ensemble_size = 50
            else:
                max_ensemble_size = 500

        self.randomised_ensemble = randomised_ensemble
        self.n_parameter_samples = n_parameter_samples
        self.random_state = random_state
        random.seed(random_state)
        self.threshold = threshold
        self.max_ensemble_size = max_ensemble_size
        self.max_win_len_prop = max_win_len_prop
        self.time_limit = time_limit

        self.seed = 0
        self.classifiers = []
        self.weights = []
        self.weight_sum = 0
        self.n_classes = 0
        self.classes_ = []
        self.class_dictionary = {}
        self.n_estimators = 0
        self.series_length = 0
        self.n_instances = 0

        self.word_lengths = word_lengths
        self.norm_options = norm_options
        self.alphabet_size = alphabet_size
        self.min_window = min_window
        super(BOSSEnsemble, self).__init__()

    def fit(self, X, y):
        """Build an ensemble of BOSS classifiers from the training set (X,
        y), either through randomising over the para
         space to make a fixed size ensemble quickly or by creating a
         variable size ensemble of those within a threshold
         of the best
        Parameters
        ----------
        X : array-like or sparse matrix of shape = [n_instances, n_columns]
            The training input samples.  If a Pandas data frame is passed,
            it must have a single column. BOSS not configured
            to handle multivariate
        y : array-like, shape = [n_instances] The class labels.

        Returns
        -------
        self : object
        """

        X, y = check_X_y(X, y, enforce_univariate=True)

        self.time_limit = self.time_limit * 6e+10
        self.n_instances, self.series_length = X.shape[0], len(X.iloc[0, 0])
        self.n_classes = np.unique(y).shape[0]
        self.classes_ = class_distribution(np.asarray(y).reshape(-1, 1))[0][0]
        for index, classVal in enumerate(self.classes_):
            self.class_dictionary[classVal] = index

        # Window length parameter space dependent on series length

        max_window_searches = self.series_length / 4
        max_window = int(self.series_length * self.max_win_len_prop)
        win_inc = int((max_window - self.min_window) / max_window_searches)
        if win_inc < 1:
            win_inc = 1

        # cBOSS
        if self.randomised_ensemble:
            random.seed(self.seed)

            possible_parameters = self._unique_parameters(max_window, win_inc)
            num_classifiers = 0
            start_time = time.time_ns()
            train_time = 0
            subsample_size = int(self.n_instances * 0.7)
            lowest_acc = 0
            lowest_acc_idx = 0

            if self.time_limit > 0:
                self.n_parameter_samples = 0

            while (train_time < self.time_limit or num_classifiers <
                   self.n_parameter_samples) and len(possible_parameters) > 0:
                parameters = possible_parameters.pop(
                    random.randint(0, len(possible_parameters) - 1))

                subsample = np.random.randint(self.n_instances,
                                              size=subsample_size)
                X_subsample = X.iloc[subsample, :]
                y_subsample = y.iloc[subsample]

                boss = BOSSIndividual(parameters[0], parameters[1],
                                      self.alphabet_size, parameters[2])
                boss.fit(X_subsample, y_subsample)
                boss._clean()

                boss.accuracy = self._individual_train_acc(boss, y_subsample,
                                                           subsample_size,
                                                           lowest_acc)
                weight = math.pow(boss.accuracy, 4)

                if num_classifiers < self.max_ensemble_size:
                    if boss.accuracy < lowest_acc:
                        lowest_acc = boss.accuracy
                        lowest_acc_idx = num_classifiers
                    self.weights.append(weight)
                    self.classifiers.append(boss)

                elif boss.accuracy > lowest_acc:
                    self.weights[lowest_acc_idx] = weight
                    self.classifiers[lowest_acc_idx] = boss
                    lowest_acc, lowest_acc_idx = self._worst_ensemble_acc()

                num_classifiers += 1
                train_time = time.time_ns() - start_time
        # BOSS
        else:
            max_acc = -1
            min_max_acc = -1

            for i, normalise in enumerate(self.norm_options):
                for win_size in range(self.min_window, max_window + 1,
                                      win_inc):
                    boss = BOSSIndividual(win_size, self.word_lengths[0],
                                          self.alphabet_size, normalise)
                    boss.fit(X, y)

                    best_classifier_for_win_size = boss
                    best_acc_for_win_size = -1
                    best_word_len = self.word_lengths[0]

                    for n, word_len in enumerate(self.word_lengths):
                        if n > 0:
                            boss = boss._shorten_bags(word_len)

                        boss.accuracy = self._individual_train_acc(
                            boss, y, self.n_instances, best_acc_for_win_size)

                        if boss.accuracy >= best_acc_for_win_size:
                            best_acc_for_win_size = boss.accuracy
                            best_classifier_for_win_size = boss
                            best_word_len = word_len

                    if self._include_in_ensemble(best_acc_for_win_size,
                                                 max_acc,
                                                 min_max_acc,
                                                 len(self.classifiers)):
                        best_classifier_for_win_size._clean()
                        best_classifier_for_win_size._set_word_len(
                            best_word_len)
                        self.classifiers.append(best_classifier_for_win_size)

                        if best_acc_for_win_size > max_acc:
                            max_acc = best_acc_for_win_size
                            self.classifiers = list(compress(
                                self.classifiers, [
                                    classifier.accuracy >= max_acc *
                                    self.threshold for c, classifier in
                                    enumerate(self.classifiers)]))

                        min_max_acc, min_acc_ind = self._worst_ensemble_acc()

                        if len(self.classifiers) > self.max_ensemble_size:
                            del self.classifiers[min_acc_ind]
                            min_max_acc, min_acc_ind = \
                                self._worst_ensemble_acc()

            self.weights = [1 for n in range(len(self.classifiers))]

        self.n_estimators = len(self.classifiers)
        self.weight_sum = np.sum(self.weights)

        self._is_fitted = True
        return self

    def predict(self, X):
        return [self.classes_[int(np.argmax(prob))] for prob in
                self.predict_proba(X)]

    def predict_proba(self, X):
        self.check_is_fitted()
        X = check_X(X, enforce_univariate=True)

        sums = np.zeros((X.shape[0], self.n_classes))

        for n, clf in enumerate(self.classifiers):
            preds = clf.predict(X)
            for i in range(0, X.shape[0]):
                sums[i, self.class_dictionary.get(preds[i])] += self.weights[n]

        dists = sums / (np.ones(self.n_classes) * self.weight_sum)

        return dists

    def _include_in_ensemble(self, acc, max_acc, min_max_acc, size):
        if acc >= max_acc * self.threshold:
            if size >= self.max_ensemble_size:
                return acc > min_max_acc
            else:
                return True
        return False

    def _worst_ensemble_acc(self):
        min_acc = -1
        min_acc_idx = 0

        for c, classifier in enumerate(self.classifiers):
            if classifier.accuracy < min_acc:
                min_acc = classifier.accuracy
                min_acc_idx = c

        return min_acc, min_acc_idx

    def _get_train_probs(self, X):
        num_inst = X.shape[0]
        results = np.zeros((num_inst, self.n_classes))
        divisor = (np.ones(self.n_classes) * np.sum(self.weights))
        for i in range(num_inst):
            sums = np.zeros(self.n_classes)

            for n, clf in enumerate(self.classifiers):
                sums[self.class_dictionary.get(clf._train_predict(i), -1)] += \
                    self.weights[n]

            dists = sums / divisor
            for n in range(self.n_classes):
                results[i][n] = dists[n]

        return results

    def _find_ensemble_train_acc(self, X, y):
        num_inst = X.shape[0]
        results = np.zeros((2 + self.n_classes, num_inst + 1))
        correct = 0

        for i in range(num_inst):
            sums = np.zeros(self.n_classes)

            for n, clf in enumerate(self.classifiers):
                sums[self.class_dictionary.get(clf._train_predict(i), -1)] += \
                    self.weights[n]

            dists = sums / (np.ones(self.n_classes) * self.n_estimators)
            c = dists.argmax()

            if c == self.class_dictionary.get(y[i], -1):
                correct += 1

            results[0][i + 1] = self.class_dictionary.get(y[i], -1)
            results[1][i + 1] = c

            for n in range(self.n_classes):
                results[2 + n][i + 1] = dists[n]

        results[0][0] = correct / num_inst
        return results

    def _unique_parameters(self, max_window, win_inc):
        possible_parameters = [[win_size, word_len, normalise] for n, normalise
                               in enumerate(self.norm_options)
                               for win_size in
                               range(self.min_window, max_window + 1, win_inc)
                               for g, word_len in enumerate(self.word_lengths)]

        return possible_parameters

    def _individual_train_acc(self, boss, y, train_size, lowest_acc):
        correct = 0
        required_correct = int(lowest_acc * train_size)

        for i in range(train_size):
            if correct + train_size - i < required_correct:
                return -1

            c = boss._train_predict(i)

            if c == y[i]:
                correct += 1

        return correct / train_size


class BOSSIndividual(BaseClassifier):
    """ Single Bag of SFA Symbols (BOSS) classifier

    Bag of SFA Symbols Ensemble: implementation of BOSS from Schaffer :
    @article
    """

    def __init__(self,
                 window_size=10,
                 word_length=8,
                 alphabet_size=4,
                 norm=False
                 ):
        self.window_size = window_size
        self.word_length = word_length
        self.alphabet_size = alphabet_size
        self.norm = norm

        self.transformer = SFA(word_length, alphabet_size,
                               window_size=window_size, norm=norm,
                               remove_repeat_words=True,
                               save_words=True)
        self.transformed_data = []
        self.accuracy = 0

        self.class_vals = []
        self.num_classes = 0
        self.classes_ = []
        self.class_dictionary = {}
        super(BOSSIndividual, self).__init__()

    def fit(self, X, y):
        sfa = self.transformer.fit_transform(X)
        self.transformed_data = [series.to_dict() for series in sfa.iloc[:, 0]]

        self.class_vals = y
        self.num_classes = np.unique(y).shape[0]
        self.classes_ = class_distribution(np.asarray(y).reshape(-1, 1))[0][0]
        for index, classVal in enumerate(self.classes_):
            self.class_dictionary[classVal] = index

        self._is_fitted = True
        return self

    def predict(self, X):
        self.check_is_fitted()
        X = check_X(X, enforce_univariate=True)

        num_insts = X.shape[0]
        classes = np.zeros(num_insts, dtype=np.int_)

        test_bags = self.transformer.transform(X)
        test_bags = [series.to_dict() for series in test_bags.iloc[:, 0]]

        for i, test_bag in enumerate(test_bags):
            bestDist = sys.float_info.max
            nn = -1

            for n, bag in enumerate(self.transformed_data):
                dist = boss_distance(test_bag, bag, bestDist)

                if dist < bestDist:
                    bestDist = dist
                    nn = self.class_vals[n]

            classes[i] = nn

        return classes

    def predict_proba(self, X):
        preds = self.predict(X)
        dists = np.zeros((X.shape[0], self.num_classes))

        for i in range(0, X.shape[0]):
            dists[i, self.class_dictionary.get(preds[i])] += 1

        return dists

    def _train_predict(self, train_num):
        test_bag = self.transformed_data[train_num]
        best_dist = sys.float_info.max
        nn = -1

        for n, bag in enumerate(self.transformed_data):
            if n == train_num:
                continue

            dist = boss_distance(test_bag, bag, best_dist)

            if dist < best_dist:
                best_dist = dist
                nn = self.class_vals[n]

        return nn

    def _shorten_bags(self, word_len):
        newBOSS = BOSSIndividual(self.window_size, word_len,
                                 self.alphabet_size, self.norm)
        newBOSS.transform = self.transformer
        sfa = self.transformer._shorten_bags(word_len)
        newBOSS.transformed_data = [series.to_dict() for series in
                                    sfa.iloc[:, 0]]
        newBOSS.class_vals = self.class_vals

        return newBOSS

    def _clean(self):
        self.transformer.words = None
        self.transformer.save_words = False

    def _set_word_len(self, word_len):
        self.word_length = word_len
        self.transformer.word_length = word_len


def boss_distance(first, second, best_dist=sys.float_info.max):
    dist = 0

    if isinstance(first, dict):
        for word, val_a in first.items():
            val_b = second.get(word, 0)
            dist += (val_a - val_b) * (val_a - val_b)

            if dist > best_dist:
                return sys.float_info.max
    else:
        dist = np.sum([0 if first[n] == 0 else (first[n] - second[n]) * (
                first[n] - second[n])
                       for n in range(len(first))])

    return dist
