# -*- coding: utf-8 -*-
"""Test scenarios for classification and regression.

Contains TestScenario concrete children to run in tests for classifiers/regressirs.
"""

__author__ = ["fkiraly"]

__all__ = ["scenarios_classification", "scenarios_regression"]

from copy import deepcopy
from inspect import isclass

from sktime.base import BaseObject
from sktime.classification.base import BaseClassifier
from sktime.regression.base import BaseRegressor
from sktime.utils._testing.panel import _make_classification_y, _make_panel_X
from sktime.utils._testing.scenarios import TestScenario

# random seed for generating data to keep scenarios exactly reproducible
RAND_SEED = 42


class ClassifierTestScenario(TestScenario, BaseObject):
    """Generic test scenario for classifiers."""

    def get_args(self, key, obj=None, deepcopy_args=True):
        """Return args for key. Can be overridden for dynamic arg generation.

        If overridden, must not have any side effects on self.args
            e.g., avoid assignments args[key] = x without deepcopying self.args first

        Parameters
        ----------
        key : str, argument key to construct/retrieve args for
        obj : obj, optional, default=None. Object to construct args for.
        deepcopy_args : bool, optional, default=True. Whether to deepcopy return.

        Returns
        -------
        args : argument dict to be used for a method, keyed by `key`
            names for keys need not equal names of methods these are used in
                but scripted method will look at key with same name as default
        """
        # use same args for predict-like functions as for predict
        if key in ["predict_proba", "decision_function"]:
            key = "predict"

        args = self.args[key]

        if deepcopy_args:
            args = deepcopy(args)

        return args

    def is_applicable(self, obj):
        """Check whether scenario is applicable to obj.

        Parameters
        ----------
        obj : class or object to check against scenario

        Returns
        -------
        applicable: bool
            True if self is applicable to obj, False if not
        """

        def get_tag(obj, tag_name):
            if isclass(obj):
                return obj.get_class_tag(tag_name)
            else:
                return obj.get_tag(tag_name)

        regr_or_classf = (BaseClassifier, BaseRegressor)

        # applicable only if obj inherits from BaseClassifier or BaseRegressor
        #   currently we test both classifiers and regressors using these scenarios
        if not isinstance(obj, regr_or_classf) and not issubclass(obj, regr_or_classf):
            return False

        # if X is multivariate, applicable only if can handle multivariate
        is_multivariate = not self.get_tag("X_univariate")

        if is_multivariate and not get_tag(obj, "capability:multivariate"):
            return False

        return True


y = _make_classification_y(n_instances=10, random_state=RAND_SEED)
X = _make_panel_X(n_instances=10, n_timepoints=20, random_state=RAND_SEED, y=y)
X_test = _make_panel_X(n_instances=5, n_timepoints=20, random_state=RAND_SEED)

X_multivariate = _make_panel_X(
    n_instances=10, n_columns=2, n_timepoints=20, random_state=RAND_SEED, y=y
)
X_test_multivariate = _make_panel_X(
    n_instances=5, n_columns=2, n_timepoints=20, random_state=RAND_SEED
)


class ClassifierFitPredict(ClassifierTestScenario):
    """Fit/predict with univariate panel X and labels y."""

    _tags = {"X_univariate": True, "is_enabled": True, "n_classes": 2}

    args = {
        "fit": {"y": y, "X": X},
        "predict": {"X": X_test},
    }
    default_method_sequence = ["fit", "predict", "predict_proba", "decision_function"]
    default_arg_sequence = ["fit", "predict", "predict", "predict"]


class ClassifierFitPredictMultivariate(ClassifierTestScenario):
    """Fit/predict with multivariate panel X and labels y."""

    _tags = {"X_univariate": False, "is_enabled": True, "n_classes": 2}

    args = {
        "fit": {"y": y, "X": X_multivariate},
        "predict": {"X": X_test_multivariate},
    }
    default_method_sequence = ["fit", "predict", "predict_proba", "decision_function"]
    default_arg_sequence = ["fit", "predict", "predict", "predict"]


scenarios_classification = [
    ClassifierFitPredict,
    ClassifierFitPredictMultivariate,
]

# we use the same scenarios for regression, as in the old test suite
scenarios_regression = [
    ClassifierFitPredict,
    ClassifierFitPredictMultivariate,
]
