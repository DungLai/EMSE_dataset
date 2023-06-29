#!/usr/bin/env python3 -u
# coding: utf-8

__author__ = ["Markus LÃ¶ning"]
__all__ = ["check_estimator"]

import numbers
import types
from copy import deepcopy
from inspect import signature

import joblib
import numpy as np
import pytest
from sklearn import clone
from sklearn.utils.estimator_checks import \
    check_get_params_invariance as _check_get_params_invariance
from sklearn.utils.estimator_checks import \
    check_set_params as _check_set_params
from sklearn.utils.testing import set_random_state
from sktime.base import BaseEstimator
from sktime.classification.base import BaseClassifier
from sktime.classification.base import is_classifier
from sktime.exceptions import NotFittedError
from sktime.forecasting.base import BaseForecaster
from sktime.forecasting.base import is_forecaster
from sktime.regression.base import BaseRegressor
from sktime.regression.base import is_regressor
from sktime.transformers.base import BaseTransformer
from sktime.transformers.base import is_transformer
from sktime.utils.testing.construct import _construct_instance
from sktime.utils.testing.forecasting import make_forecasting_problem
from sktime.utils.testing.inspect import _get_args
from sktime.utils.testing.series_as_features import make_classification_problem
from sktime.utils.testing.series_as_features import make_regression_problem

# TODO add to NON_STATE_CHANGING_METHODS: transform, inverse_transform,
#  decision_function
NON_STATE_CHANGING_METHODS = ["predict", "predict_proba"]


def check_estimator(Estimator):
    for check in yield_estimator_checks():
        check(Estimator)


def yield_estimator_checks():
    checks = [
        check_inheritance,
        # check_meta_estimator,
        check_has_common_interface,
        check_constructor,
        check_get_params,
        check_set_params,
        check_clone,
        check_repr,
        check_fit_updates_state,
        check_fit_returns_self,
        check_raises_not_fitted_error,
        check_fit_idempotent,
        check_fit_does_not_overwrite_hyper_params,
        check_non_state_changing_methods_do_not_change_state,
    ]
    for check in checks:
        yield check


def check_meta_estimators(Estimator):
    if hasattr(Estimator, "_required_parameters"):
        params = Estimator._required_parameters
        assert isinstance(params, list)
        assert all([isinstance(param, str) for param in params])


def check_inheritance(Estimator):
    # check that inherits from one and only one task-specific estimator

    # class checks
    base_classes = [
        BaseClassifier,
        BaseRegressor,
        BaseForecaster,
        BaseTransformer
    ]
    assert issubclass(Estimator, BaseEstimator)
    assert sum([issubclass(Estimator, base_class) for base_class in
                base_classes]) == 1

    # instance type checks
    is_type_checks = [
        is_classifier,
        is_regressor,
        is_forecaster,
        is_transformer
    ]
    estimator = _construct_instance(Estimator)
    assert isinstance(estimator, BaseEstimator)
    assert sum([is_type_check(estimator) for is_type_check in
                is_type_checks]) == 1


def check_has_common_interface(Estimator):
    # check class for type of attribute
    assert isinstance(Estimator.is_fitted, property)

    # check instance
    estimator = _construct_instance(Estimator)
    common_attrs = [
        "fit",
        "check_is_fitted",
        "is_fitted",
        "_is_fitted",
        "set_params",
        "get_params"
    ]
    for attr in common_attrs:
        assert hasattr(estimator, attr)
    assert (hasattr(estimator, "predict")
            or hasattr(estimator, "transform"))


def check_get_params(Estimator):
    estimator = _construct_instance(Estimator)
    params = estimator.get_params()
    assert isinstance(params, dict)
    _check_get_params_invariance(estimator.__class__.__name__, estimator)


def check_set_params(Estimator):
    # check set_params returns self
    estimator = _construct_instance(Estimator)
    params = estimator.get_params()
    assert estimator.set_params(**params) is estimator
    _check_set_params(estimator.__class__.__name__, estimator)


def check_clone(Estimator):
    estimator = _construct_instance(Estimator)
    clone(estimator)


def check_repr(Estimator):
    estimator = _construct_instance(Estimator)
    repr(estimator)


def check_constructor(Estimator):
    estimator = _construct_instance(Estimator)

    # Check that init does not construct object of other class than itself
    assert isinstance(estimator, Estimator)

    # Ensure that each parameter is set in init
    init_params = _get_args(type(estimator).__init__)
    invalid_attr = set(init_params) - set(vars(estimator)) - {"self"}
    assert not invalid_attr, (
            "Estimator %s should store all parameters"
            " as an attribute during init. Did not find "
            "attributes %s."
            % (estimator.__class__.__name__, sorted(invalid_attr)))

    # Ensure that init does nothing but set parameters
    # No logic/interaction with other parameters
    def param_filter(p):
        """Identify hyper parameters of an estimator"""
        return (p.name != 'self' and
                p.kind != p.VAR_KEYWORD and
                p.kind != p.VAR_POSITIONAL)

    init_params = [p for p in signature(estimator.__init__).parameters.values()
                   if param_filter(p)]

    params = estimator.get_params()

    required_params = getattr(estimator, '_required_parameters', [])
    init_params = [param for param in init_params if
                   param not in required_params]

    for param in init_params:
        assert param.default != param.empty, (
                "parameter %s for %s has no default value"
                % (param.name, estimator.__class__.__name__))
        if type(param.default) is type:
            assert param.default in [np.float64, np.int64]
        else:
            assert (type(param.default) in
                    [str, int, float, bool, tuple, type(None),
                     np.float64, types.FunctionType, joblib.Memory])

        param_value = params[param.name]
        if isinstance(param_value, np.ndarray):
            np.testing.assert_array_equal(param_value, param.default)
        else:
            if bool(isinstance(param_value, numbers.Real) and np.isnan(
                    param_value)):
                # Allows to set default parameters to np.nan
                assert param_value is param.default, param.name
            else:
                assert param_value == param.default, param.name


def check_fit_updates_state(Estimator):
    is_fitted_states = ["_is_fitted", "is_fitted"]

    estimator = _construct_instance(Estimator)
    # check it's not fitted before calling fit
    for state in is_fitted_states:
        assert not getattr(estimator, state), (
            f"Estimator: {estimator} does not initiate state: {state} to "
            f"False")

    fit_args = _make_args(estimator, "fit")
    estimator.fit(*fit_args)

    # check states are updated after calling fit
    for state in is_fitted_states:
        assert getattr(estimator, state), (
            f"Estimator: {estimator} does not update state: {state} "
            f"during fit")


def check_fit_returns_self(Estimator):
    estimator = _construct_instance(Estimator)
    fit_args = _make_args(estimator, "fit")
    assert estimator.fit(*fit_args) is estimator, (
        f"Estimator: {estimator} does not return self when calling "
        f"fit")


def check_raises_not_fitted_error(Estimator):
    estimator = _construct_instance(Estimator)

    # call methods without prior fitting and check that they raise our
    # NotFittedError
    for method in NON_STATE_CHANGING_METHODS:
        if hasattr(estimator, method):
            args = _make_args(estimator, method)
            with pytest.raises(NotFittedError):
                getattr(estimator, method)(*args)


def check_fit_idempotent(Estimator):
    estimator = _construct_instance(Estimator)
    set_random_state(estimator)

    # Fit for the first time
    fit_args = _make_args(estimator, "fit")
    estimator.fit(*fit_args)

    results = dict()
    args = dict()
    for method in NON_STATE_CHANGING_METHODS:
        if hasattr(estimator, method):
            args[method] = _make_args(estimator, method)
            results[method] = getattr(estimator, method)(*args[method])

    # Fit again
    set_random_state(estimator)
    estimator.fit(*fit_args)

    for method in NON_STATE_CHANGING_METHODS:
        if hasattr(estimator, method):
            new_result = getattr(estimator, method)(*args[method])
            np.testing.assert_array_almost_equal(
                results[method], new_result,
                err_msg=f"Idempotency check failed for method {method}")


def check_fit_does_not_overwrite_hyper_params(Estimator):
    estimator = _construct_instance(Estimator)
    set_random_state(estimator)

    # Make a physical copy of the original estimator parameters before fitting.
    params = estimator.get_params()
    original_params = deepcopy(params)

    # Fit the model
    fit_args = _make_args(estimator, "fit")
    estimator.fit(*fit_args)

    # Compare the state of the model parameters with the original parameters
    new_params = estimator.get_params()
    for param_name, original_value in original_params.items():
        new_value = new_params[param_name]

        # We should never change or mutate the internal state of input
        # parameters by default. To check this we use the joblib.hash function
        # that introspects recursively any subobjects to compute a checksum.
        # The only exception to this rule of immutable constructor parameters
        # is possible RandomState instance but in this check we explicitly
        # fixed the random_state params recursively to be integer seeds.
        assert joblib.hash(new_value) == joblib.hash(original_value), (
                "Estimator %s should not change or mutate "
                " the parameter %s from %s to %s during fit."
                % (estimator.__class__.__name__, param_name, original_value,
                   new_value))


def check_non_state_changing_methods_do_not_change_state(Estimator):
    estimator = _construct_instance(Estimator)
    set_random_state(estimator)

    fit_args = _make_args(estimator, "fit")
    estimator.fit(*fit_args)

    for method in NON_STATE_CHANGING_METHODS:
        if hasattr(estimator, method):
            args = _make_args(estimator, method)
            dict_before = estimator.__dict__.copy()
            getattr(estimator, method)(args)
            assert estimator.__dict__ == dict_before, (
                f"Estimator: {estimator} changes __dict__ during {method}")


def _make_args(estimator, method, *args, **kwargs):
    if method == "fit":
        return _make_fit_args(estimator, *args, **kwargs)

    elif method == "predict":
        return _make_predict_args(estimator, *args, **kwargs)

    else:
        raise ValueError(f"Method: {method} not supported")


def _make_fit_args(estimator, random_state=None):
    if is_forecaster(estimator):
        y = make_forecasting_problem(random_state=random_state)
        fh = 1
        return y, fh

    elif is_classifier(estimator):
        return make_classification_problem(random_state=random_state)

    elif is_regressor(estimator):
        return make_regression_problem(random_state=random_state)

    else:
        raise ValueError(f"Estimator type: {type(estimator)} not supported")


def _make_predict_args(estimator, random_state=None):
    if is_forecaster(estimator):
        fh = 1
        return fh

    elif is_classifier(estimator):
        X, y = make_classification_problem(random_state=random_state)
        return X

    elif is_regressor(estimator):
        X, y = make_regression_problem(random_state=random_state)
        return X

    else:
        raise ValueError("estimator type not supported")