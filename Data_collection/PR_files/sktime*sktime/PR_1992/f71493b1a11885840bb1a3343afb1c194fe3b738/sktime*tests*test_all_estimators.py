# -*- coding: utf-8 -*-
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)
"""Suite of tests for all estimators.

adapted from scikit-learn's estimator_checks
"""

__author__ = ["mloning", "fkiraly"]

import numbers
import pickle
import types
from copy import deepcopy
from inspect import getfullargspec, isclass, signature

import joblib
import numpy as np
import pytest
from sklearn import clone
from sklearn.utils._testing import set_random_state
from sklearn.utils.estimator_checks import (
    check_get_params_invariance as _check_get_params_invariance,
)
from sklearn.utils.estimator_checks import check_set_params as _check_set_params

from sktime.base import BaseEstimator
from sktime.dists_kernels._base import (
    BasePairwiseTransformer,
    BasePairwiseTransformerPanel,
)
from sktime.exceptions import NotFittedError
from sktime.registry import all_estimators
from sktime.tests._config import (
    EXCLUDE_ESTIMATORS,
    EXCLUDED_TESTS,
    NON_STATE_CHANGING_METHODS,
    VALID_ESTIMATOR_BASE_TYPES,
    VALID_ESTIMATOR_TAGS,
    VALID_ESTIMATOR_TYPES,
    VALID_TRANSFORMER_TYPES,
)
from sktime.utils._testing._conditional_fixtures import (
    create_conditional_fixtures_and_names,
)
from sktime.utils._testing.deep_equals import deep_equals
from sktime.utils._testing.estimator_checks import (
    _assert_array_almost_equal,
    _assert_array_equal,
    _get_args,
    _has_capability,
    _list_required_methods,
    _make_args,
)
from sktime.utils._testing.scenarios_getter import retrieve_scenarios


class BaseFixtureGenerator:
    """Fixture generator for base testing functionality in sktime.

    Test classes inheriting from this and not overriding pytest_generate_tests
        will have estimator and scenario fixtures parameterized out of the box.

    Descendants can override:
        estimator_type_filter: str, class variable; None or scitype string
            e.g., "forecaster", "transformer", "classifier", see BASE_CLASS_SCITYPE_LIST
            which estimators are being retrieved and tested
        fixture_sequence: list of str
            sequence of fixture variable names in conditional fixture generation
        _generate_[variable]: object methods, all (test_name: str, **kwargs) -> list
            generating list of fixtures for fixture variable with name [variable]
                to be used in test with name test_name
            can optionally use values for fixtures earlier in fixture_sequence,
                these must be input as kwargs in a call
        is_excluded: static method (test_name: str, est: class) -> bool
            whether test with name test_name should be excluded for estimator est
                should be used only for encoding general rules, not individual skips
                individual skips should go on the EXCLUDED_TESTS list in _config
            requires _generate_estimator_class and _generate_estimator_instance as is
        _excluded_scenario: static method (test_name: str, scenario) -> bool
            whether scenario should be skipped in test with test_name test_name
            requires _generate_estimator_scenario as is

    Fixtures parameterized
    ----------------------
    estimator_class: estimator inheriting from BaseObject
        ranges over all estimator classes not excluded by EXCLUDED_TESTS
    estimator_instance: instance of estimator inheriting from BaseObject
        ranges over all estimator classes not excluded by EXCLUDED_TESTS
        instances are generated by create_test_instance class method
    scenario: instance of TestScenario
        ranges over all scenarios returned by retrieve_scenarios
    """

    # class variables which can be overridden by descendants

    # which estimator types are generated; None=all, or scitype string like "forecaster"
    estimator_type_filter = None

    # which sequence the conditional fixtures are generated in
    fixture_sequence = ["estimator_class", "estimator_instance", "scenario"]

    def pytest_generate_tests(self, metafunc):
        """Test parameterization routine for pytest.

        This uses create_conditional_fixtures_and_names and generator_dict
        to create the fixtures for a mark.parameterize decoration of all tests.
        """
        # get name of the test
        test_name = metafunc.function.__name__

        fixture_sequence = ["estimator_class", "estimator_instance", "scenario"]

        fixture_vars = getfullargspec(metafunc.function)[0]

        (
            fixture_param_str,
            fixture_prod,
            fixture_names,
        ) = create_conditional_fixtures_and_names(
            test_name=test_name,
            fixture_vars=fixture_vars,
            generator_dict=self.generator_dict(),
            fixture_sequence=fixture_sequence,
        )

        metafunc.parametrize(fixture_param_str, fixture_prod, ids=fixture_names)

    def _all_estimators(self):
        """Retrieve list of all estimator classes of type self.estimator_type_filter."""
        return all_estimators(
            estimator_types=getattr(self, "estimator_type_filter", None),
            return_names=False,
            exclude_estimators=EXCLUDE_ESTIMATORS,
        )

    def generator_dict(self):
        """Return dict with methods _generate_[variable] collected in a dict.

        The returned dict is the one required by create_conditional_fixtures_and_names,
            used in this _conditional_fixture plug-in to pytest_generate_tests, above.

        Returns
        -------
        generator_dict : dict, with keys [variable], where
            [variable] are all strings such that self has a static method
                named _generate_[variable](test_name: str, **kwargs)
            value at [variable] is a reference to _generate_[variable]
        """
        gens = [attr for attr in dir(self) if attr.startswith("_generate_")]
        vars = [gen.replace("_generate_", "") for gen in gens]

        generator_dict = dict()
        for var, gen in zip(vars, gens):
            generator_dict[var] = getattr(self, gen)

        return generator_dict

    @staticmethod
    def is_excluded(test_name, est):
        """Shorthand to check whether test test_name is excluded for estimator est."""
        return test_name in EXCLUDED_TESTS.get(est.__name__, [])

    # the following functions define fixture generation logic for pytest_generate_tests
    # each function is of signature (test_name:str, **kwargs) -> List of fixtures
    # function with name _generate_[fixture_var] returns list of values for fixture_var
    #   where fixture_var is a fixture variable used in tests
    # the list is conditional on values of other fixtures which can be passed in kwargs

    def _generate_estimator_class(self, test_name, **kwargs):
        """Return estimator class fixtures.

        Fixtures parameterized
        ----------------------
        estimator_class: estimator inheriting from BaseObject
            ranges over all estimator classes not excluded by EXCLUDED_TESTS
        """
        estimator_classes_to_test = [
            est
            for est in self._all_estimators()
            if not self.is_excluded(test_name, est)
        ]
        estimator_names = [est.__name__ for est in estimator_classes_to_test]

        return estimator_classes_to_test, estimator_names

    def _generate_estimator_instance(self, test_name, **kwargs):
        """Return estimator instance fixtures.

        Fixtures parameterized
        ----------------------
        estimator_instance: instance of estimator inheriting from BaseObject
            ranges over all estimator classes not excluded by EXCLUDED_TESTS
            instances are generated by create_test_instance class method
        """
        # call _generate_estimator_class to get all the classes
        estimator_classes_to_test, _ = self._generate_estimator_class(
            test_name=test_name
        )

        # create instances from the classes
        estimator_instances_to_test = []
        estimator_instance_names = []
        # retrieve all estimator parameters if multiple, construct instances
        for est in estimator_classes_to_test:
            all_instances_of_est, instance_names = est.create_test_instances_and_names()
            estimator_instances_to_test += all_instances_of_est
            estimator_instance_names += instance_names

        return estimator_instances_to_test, estimator_instance_names

    def _generate_scenario(self, test_name, **kwargs):
        """Return estimator test scenario.

        Fixtures parameterized
        ----------------------
        scenario: instance of TestScenario
            ranges over all scenarios returned by retrieve_scenarios
        """
        if "estimator_class" in kwargs.keys():
            obj = kwargs["estimator_class"]
        elif "estimator_instance" in kwargs.keys():
            obj = kwargs["estimator_instance"]
        else:
            return []

        scenarios = retrieve_scenarios(obj)
        scenarios = [s for s in scenarios if not self._excluded_scenario(test_name, s)]
        scenario_names = [type(scen).__name__ for scen in scenarios]

        return scenarios, scenario_names

    @staticmethod
    def _excluded_scenario(test_name, scenario):
        """Skip list generator for scenarios to skip in test_name.

        Arguments
        ---------
        test_name : str, name of test
        scenario : instance of TestScenario, to be used in test

        Returns
        -------
        bool, whether scenario should be skipped in test_name
        """
        # for forecasters tested in test_methods_do_not_change_state
        #   if fh is not passed in fit, then this test would fail
        #   since fh will be stored in predict through fh handling
        #   as there are scenarios which pass it early and everything else is the same
        #   we skip those scenarios
        if test_name == "test_methods_do_not_change_state":
            if not scenario.get_tag("fh_passed_in_fit", True, raise_error=False):
                return True

        # this line excludes all scenarios that are not 1:1 to the "pre-scenario" state
        #   pre-refactor, all tests pass, so all post-refactor tests should with below
        # comment out to run the full test suite with new scenarios
        if not scenario.get_tag("pre-refactor", False, raise_error=False):
            return True

        return False


class QuickTester:
    """Mixin class which adds the run_tests method to run tests on one estimator."""

    def run_tests(
        self, est, return_exceptions=True, tests_to_run=None, fixtures_to_run=None
    ):  # noqa: E501
        """Run all tests on one single estimator.

        All tests in self are run on the following estimator type fixtures:
            if est is a class, then estimator_class = est, and
                estimator_instance loops over est.create_test_instance()
            if est is an object, then estimator_class = est.__class__, and
                estimator_instance = est

        Parameters
        ----------
        est : estimator class or estimator instance
        return_exception : bool, optional, default=True
            whether to return exceptions/failures, or raise them
                if True: returns exceptions in results
                if False: raises exceptions as they occur
        tests_to_run : str or list of str, names of tests to run. default = all tests
            sub-sets tests that are run to the tests given here.
        fixtures_to_run : str or list of str, pytest test-fixture combination codes.
            which test-fixture combinations to run. Default = run all of them.
            sub-sets tests and fixtures to run to the list given here.
            If both tests_to_run and fixtures_to_run are provided, runs the *union*,
            i.e., all test-fixture combinations for tests in tests_to_run,
                plus all test-fixture combinations in fixtures_to_run.

        Returns
        -------
        results : dict of results of the tests in self
            keys are test/fixture strings, identical as in pytest, e.g., test[fixture]
            entries are the string "PASSED" if the test passed,
                or the exception raised if the test did not pass
            returned only if all tests pass, or return_exceptions=True

        Raises
        ------
        if return_exception=False, raises any exception produced by the tests directly

        Examples
        --------
        >>> from sktime.forecasting.naive import NaiveForecaster
        >>> from sktime.tests.test_all_estimators import TestAllEstimators
        >>> TestAllEstimators().run_tests(
        ...     NaiveForecaster,
        ...     tests_to_run=["test_create_test_instance", "test_required_params"]
        ... )
        {'test_required_params[NaiveForecaster]': 'PASSED', 'test_create_test_instance[NaiveForecaster]': 'PASSED'}
        >>> TestAllEstimators().run_tests(
        ...     NaiveForecaster, fixtures_to_run="test_repr[NaiveForecaster-2]"
        ... )
        {'test_repr[NaiveForecaster-2]': 'PASSED'}
        """
        tests_to_run = self._check_None_str_or_list_of_str(
            tests_to_run, var_name="tests_to_run"
        )
        fixtures_to_run = self._check_None_str_or_list_of_str(
            fixtures_to_run, var_name="fixtures_to_run"
        )

        # retrieve tests from self
        test_names = [attr for attr in dir(self) if attr.startswith("test")]

        # we override the generator_dict, by replacing it with temp_generator_dict:
        #  the only estimator (class or instance) is est, this is overridden
        #  the remaining fixtures are generated conditionally, without change
        temp_generator_dict = deepcopy(self.generator_dict())

        if isclass(est):
            estimator_class = est
        else:
            estimator_class = type(est)

        def _generate_estimator_class(test_name, **kwargs):
            return [estimator_class], [estimator_class.__name__]

        def _generate_estimator_instance(test_name, **kwargs):
            return [est], [estimator_class.__name__]

        def _generate_estimator_instance_cls(test_name, **kwargs):
            return estimator_class.create_test_instances_and_names()

        temp_generator_dict["estimator_class"] = _generate_estimator_class

        if not isclass(est):
            temp_generator_dict["estimator_instance"] = _generate_estimator_instance
        else:
            temp_generator_dict["estimator_instance"] = _generate_estimator_instance_cls
        # override of generator_dict end, temp_generator_dict is now prepared

        # sub-setting to specific tests to run, if tests or fixtures were speified
        if tests_to_run is None and fixtures_to_run is None:
            test_names_subset = test_names
        else:
            test_names_subset = []
            if tests_to_run is not None:
                test_names_subset += list(set(test_names).intersection(tests_to_run))
            if fixtures_to_run is not None:
                # fixture codes contain the test as substring until the first "["
                tests_from_fixt = [fixt.split("[")[0] for fixt in fixtures_to_run]
                test_names_subset += list(set(test_names).intersection(tests_from_fixt))
            test_names_subset = list(set(test_names_subset))

        # the below loops run all the tests and collect the results here:
        results = dict()
        # loop A: we loop over all the tests
        for test_name in test_names_subset:

            test_fun = getattr(self, test_name)
            fixture_sequence = self.fixture_sequence

            # all arguments except the first one (self)
            fixture_vars = getfullargspec(test_fun)[0][1:]
            fixture_vars = [var for var in fixture_sequence if var in fixture_vars]

            # this call retrieves the conditional fixtures
            #  for the test test_name, and the estimator
            _, fixture_prod, fixture_names = create_conditional_fixtures_and_names(
                test_name=test_name,
                fixture_vars=fixture_vars,
                generator_dict=temp_generator_dict,
                fixture_sequence=fixture_sequence,
            )

            # loop B: for each test, we loop over all fixtures
            for params, fixt_name in zip(fixture_prod, fixture_names):

                # this is needed because pytest unwraps 1-tuples automatically
                # but subsequent code assumes params is k-tuple, no matter what k is
                if len(fixture_vars) == 1:
                    params = (params,)
                key = f"{test_name}[{fixt_name}]"
                args = dict(zip(fixture_vars, params))

                # we subset to test-fixtures to run by this, if given
                #  key is identical to the pytest test-fixture string identifier
                if fixtures_to_run is not None and key not in fixtures_to_run:
                    continue

                if return_exceptions:
                    try:
                        test_fun(**args)
                        results[key] = "PASSED"
                    except Exception as err:
                        results[key] = err
                else:
                    test_fun(**args)
                    results[key] = "PASSED"

        return results

    @staticmethod
    def _check_None_str_or_list_of_str(obj, var_name="obj"):
        """Check that obj is None, str, or list of str, and coerce to list of str."""
        if obj is not None:
            msg = f"{var_name} must be None, str, or list of str"
            if isinstance(obj, str):
                obj = [obj]
            if not isinstance(obj, list):
                raise ValueError(msg)
            if not np.all(isinstance(x, str) for x in obj):
                raise ValueError(msg)
        return obj


class TestAllEstimators(BaseFixtureGenerator, QuickTester):
    """Package level tests for all sktime estimators."""

    def test_create_test_instance(self, estimator_class):
        """Check first that create_test_instance logic works."""
        estimator = estimator_class.create_test_instance()

        # Check that init does not construct object of other class than itself
        assert isinstance(estimator, estimator_class), (
            "object returned by create_test_instance must be an instance of the class, "
            f"found {type(estimator)}"
        )

    def test_create_test_instances_and_names(self, estimator_class):
        """Check that create_test_instances_and_names works."""
        estimators, names = estimator_class.create_test_instances_and_names()

        assert isinstance(estimators, list), (
            "first return of create_test_instances_and_names must be a list, "
            f"found {type(estimators)}"
        )
        assert isinstance(names, list), (
            "second return of create_test_instances_and_names must be a list, "
            f"found {type(names)}"
        )

        assert np.all(isinstance(est, estimator_class) for est in estimators), (
            "list elements of first return returned by create_test_instances_and_names "
            "all must be an instance of the class"
        )

        assert np.all(isinstance(name, names) for name in names), (
            "list elements of second return returned by create_test_instances_and_names"
            " all must be strings"
        )

        assert len(estimators) == len(names), (
            "the two lists returned by create_test_instances_and_names must have "
            "equal length"
        )

    def test_required_params(self, estimator_class):
        """Check required parameter interface."""
        Estimator = estimator_class
        # Check common meta-estimator interface
        if hasattr(Estimator, "_required_parameters"):
            required_params = Estimator._required_parameters

            assert isinstance(required_params, list), (
                f"For estimator: {Estimator}, `_required_parameters` must be a "
                f"tuple, but found type: {type(required_params)}"
            )

            assert all([isinstance(param, str) for param in required_params]), (
                f"For estimator: {Estimator}, elements of `_required_parameters` "
                f"list must be strings"
            )

            # check if needless parameters are in _required_parameters
            init_params = [
                par.name for par in signature(Estimator.__init__).parameters.values()
            ]
            in_required_but_not_init = [
                param for param in required_params if param not in init_params
            ]
            if len(in_required_but_not_init) > 0:
                raise ValueError(
                    f"Found parameters in `_required_parameters` which "
                    f"are not in `__init__`: "
                    f"{in_required_but_not_init}"
                )

    def test_estimator_tags(self, estimator_class):
        """Check conventions on estimator tags."""
        Estimator = estimator_class

        assert hasattr(Estimator, "get_class_tags")
        all_tags = Estimator.get_class_tags()
        assert isinstance(all_tags, dict)
        assert all(isinstance(key, str) for key in all_tags.keys())
        if hasattr(Estimator, "_tags"):
            tags = Estimator._tags
            msg = f"_tags must be a dict, but found {type(tags)}"
            assert isinstance(tags, dict), msg
            assert len(tags) > 0, "_tags is empty"
            assert all(
                tag in VALID_ESTIMATOR_TAGS for tag in tags.keys()
            ), "Some tags in _tags are invalid"

        # Avoid ambiguous class attributes
        ambiguous_attrs = ("tags", "tags_")
        for attr in ambiguous_attrs:
            assert not hasattr(Estimator, attr), (
                f"Please avoid using the {attr} attribute to disambiguate it from "
                f"estimator tags."
            )

    def test_inheritance(self, estimator_class):
        """Check that estimator inherits from BaseEstimator."""
        assert issubclass(estimator_class, BaseEstimator), (
            f"Estimator: {estimator_class} " f"is not a sub-class of " f"BaseEstimator."
        )
        Estimator = estimator_class
        # Usually estimators inherit only from one BaseEstimator type, but in some cases
        # they may be predictor and transformer at the same time (e.g. pipelines)
        n_base_types = sum(
            issubclass(Estimator, cls) for cls in VALID_ESTIMATOR_BASE_TYPES
        )

        assert 2 >= n_base_types >= 1

        # If the estimator inherits from more than one base estimator type, we check if
        # one of them is a transformer base type
        if n_base_types > 1:
            assert issubclass(Estimator, VALID_TRANSFORMER_TYPES)

    def test_has_common_interface(self, estimator_class):
        """Check estimator implements the common interface."""
        estimator = estimator_class

        # Check class for type of attribute
        assert isinstance(estimator.is_fitted, property)

        required_methods = _list_required_methods(estimator_class)

        for attr in required_methods:
            assert hasattr(
                estimator, attr
            ), f"Estimator: {estimator.__name__} does not implement attribute: {attr}"

        if hasattr(estimator, "inverse_transform"):
            assert hasattr(estimator, "transform")
        if hasattr(estimator, "predict_proba"):
            assert hasattr(estimator, "predict")

    def test_get_params(self, estimator_instance):
        """Check that get_params works correctly."""
        estimator = estimator_instance
        params = estimator.get_params()
        assert isinstance(params, dict)
        _check_get_params_invariance(estimator.__class__.__name__, estimator)

    def test_set_params(self, estimator_instance):
        """Check that set_params works correctly."""
        estimator = estimator_instance
        params = estimator.get_params()
        assert estimator.set_params(**params) is estimator
        _check_set_params(estimator.__class__.__name__, estimator)

    def test_clone(self, estimator_instance):
        """Check we can call clone from scikit-learn."""
        estimator = estimator_instance
        clone(estimator)

    def test_repr(self, estimator_instance):
        """Check we can call repr."""
        estimator = estimator_instance
        repr(estimator)

    def check_constructor(self, estimator_class):
        """Check that the constructor behaves correctly."""
        estimator = estimator_class.create_test_instance()

        # Ensure that each parameter is set in init
        init_params = _get_args(type(estimator).__init__)
        invalid_attr = set(init_params) - set(vars(estimator)) - {"self"}
        assert not invalid_attr, (
            "Estimator %s should store all parameters"
            " as an attribute during init. Did not find "
            "attributes `%s`." % (estimator.__class__.__name__, sorted(invalid_attr))
        )

        # Ensure that init does nothing but set parameters
        # No logic/interaction with other parameters
        def param_filter(p):
            """Identify hyper parameters of an estimator."""
            return p.name != "self" and p.kind not in [p.VAR_KEYWORD, p.VAR_POSITIONAL]

        init_params = [
            p
            for p in signature(estimator.__init__).parameters.values()
            if param_filter(p)
        ]

        params = estimator.get_params()

        # Filter out required parameters with no default value and parameters
        # set for running tests
        required_params = getattr(estimator, "_required_parameters", tuple())

        test_params = estimator_class.get_test_params()
        if isinstance(test_params, list):
            test_params = test_params[0]
        test_params = test_params.keys()

        init_params = [
            param
            for param in init_params
            if param.name not in required_params and param.name not in test_params
        ]

        for param in init_params:
            assert param.default != param.empty, (
                "parameter `%s` for %s has no default value and is not "
                "included in `_required_parameters`"
                % (param.name, estimator.__class__.__name__)
            )
            if type(param.default) is type:
                assert param.default in [np.float64, np.int64]
            else:
                assert type(param.default) in [
                    str,
                    int,
                    float,
                    bool,
                    tuple,
                    type(None),
                    np.float64,
                    types.FunctionType,
                    joblib.Memory,
                ]

            param_value = params[param.name]
            if isinstance(param_value, np.ndarray):
                np.testing.assert_array_equal(param_value, param.default)
            else:
                if bool(
                    isinstance(param_value, numbers.Real) and np.isnan(param_value)
                ):
                    # Allows to set default parameters to np.nan
                    assert param_value is param.default, param.name
                else:
                    assert param_value == param.default, param.name

    def test_fit_updates_state(self, estimator_instance, scenario):
        """Check fit/update state change."""
        # Check that fit updates the is-fitted states
        attrs = ["_is_fitted", "is_fitted"]

        estimator = estimator_instance

        assert hasattr(
            estimator, "_is_fitted"
        ), f"Estimator: {estimator.__name__} does not set_is_fitted in construction"

        # Check is_fitted attribute is set correctly to False before fit, at init
        for attr in attrs:
            assert not getattr(
                estimator, attr
            ), f"Estimator: {estimator} does not initiate attribute: {attr} to False"

        fitted_estimator = scenario.run(estimator_instance, method_sequence=["fit"])

        # Check 0s_fitted attribute is updated correctly to False after calling fit
        for attr in attrs:
            assert getattr(
                fitted_estimator, attr
            ), f"Estimator: {estimator} does not update attribute: {attr} during fit"

    def test_fit_returns_self(self, estimator_instance, scenario):
        """Check that fit returns self."""
        fit_return = scenario.run(estimator_instance, method_sequence=["fit"])
        assert (
            fit_return is estimator_instance
        ), f"Estimator: {estimator_instance} does not return self when calling fit"

    def test_raises_not_fitted_error(self, estimator_instance, scenario):
        """Check that we raise appropriate error for unfitted estimators."""
        # pairwise transformers are exempted from this test, since they have no fitting
        PWTRAFOS = (BasePairwiseTransformer, BasePairwiseTransformerPanel)
        excepted = isinstance(estimator_instance, PWTRAFOS)
        if excepted:
            return None

        # call methods without prior fitting and check that they raise our
        # NotFittedError
        for method in NON_STATE_CHANGING_METHODS:
            if _has_capability(estimator_instance, method):
                with pytest.raises(NotFittedError, match=r"has not been fitted"):
                    scenario.run(estimator_instance, method_sequence=[method])

    def test_fit_idempotent(self, estimator_instance, scenario):
        """Check that calling fit twice is equivalent to calling it once."""
        estimator = estimator_instance

        # todo: may have to rework this, due to "if estimator has param"
        for method in NON_STATE_CHANGING_METHODS:
            if _has_capability(estimator, method):
                set_random_state(estimator)
                results = scenario.run(
                    estimator,
                    method_sequence=["fit", method],
                    return_all=True,
                    deepcopy_return=True,
                )

                estimator = results[0]
                set_random_state(estimator)

                results_2nd = scenario.run(
                    estimator,
                    method_sequence=["fit", method],
                    return_all=True,
                    deepcopy_return=True,
                )

                _assert_array_almost_equal(
                    results[1],
                    results_2nd[1],
                    # err_msg=f"Idempotency check failed for method {method}",
                )

    def test_fit_does_not_overwrite_hyper_params(self, estimator_instance, scenario):
        """Check that we do not overwrite hyper-parameters in fit."""
        estimator = estimator_instance
        set_random_state(estimator)

        # Make a physical copy of the original estimator parameters before fitting.
        params = estimator.get_params()
        original_params = deepcopy(params)

        # Fit the model
        fitted_est = scenario.run(estimator_instance, method_sequence=["fit"])

        # Compare the state of the model parameters with the original parameters
        new_params = fitted_est.get_params()
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
                % (estimator.__class__.__name__, param_name, original_value, new_value)
            )

    def test_methods_do_not_change_state(self, estimator_instance, scenario):
        """Check that non-state-changing methods do not change state.

        Check that methods that are not supposed to change attributes of the
        estimators do not change anything (including hyper-parameters and
        fitted parameters)
        """
        estimator = estimator_instance
        set_random_state(estimator)

        for method in NON_STATE_CHANGING_METHODS:
            if _has_capability(estimator, method):

                # dict_before = copy of dictionary of estimator before predict, post fit
                _ = scenario.run(estimator, method_sequence=["fit"])
                dict_before = estimator.__dict__.copy()

                # dict_after = dictionary of estimator after predict and fit
                _ = scenario.run(estimator, method_sequence=[method])
                dict_after = estimator.__dict__

                if method == "transform" and estimator.get_class_tag(
                    "fit-in-transform"
                ):
                    # Some transformations fit during transform, as they apply
                    # some transformation to each series passed to transform,
                    # so transform will actually change the state of these estimator.
                    continue

                if method == "predict" and estimator.get_class_tag("fit-in-predict"):
                    # Some annotators fit during predict, as they apply
                    # some apply annotation to each series passed to predict,
                    # so predict will actually change the state of these annotators.
                    continue

                # old logic uses equality without auto-msg, keep comment until refactor
                # is_equal = dict_after == dict_before
                is_equal, msg = deep_equals(dict_after, dict_before, return_msg=True)
                assert is_equal, (
                    f"Estimator: {type(estimator).__name__} changes __dict__ "
                    f"during {method}, "
                    f"reason/location of discrepancy (x=after, y=before): {msg}"
                )

    def test_methods_have_no_side_effects(self, estimator_instance, scenario):
        """Check that calling methods has no side effects on args."""
        estimator = estimator_instance

        set_random_state(estimator)

        # Fit the model, get args before and after
        _, args_after = scenario.run(
            estimator, method_sequence=["fit"], return_args=True
        )
        fit_args_after = args_after[0]
        fit_args_before = scenario.args["fit"]

        assert deep_equals(
            fit_args_before, fit_args_after
        ), f"Estimator: {estimator} has side effects on arguments of fit"

        for method in NON_STATE_CHANGING_METHODS:
            if _has_capability(estimator, method):
                # Fit the model, get args before and after
                _, args_after = scenario.run(
                    estimator, method_sequence=[method], return_args=True
                )
                method_args_after = args_after[0]
                method_args_before = scenario.get_args(method, estimator)

                assert deep_equals(
                    method_args_after, method_args_before
                ), f"Estimator: {estimator} has side effects on arguments of {method}"

    def test_persistence_via_pickle(self, estimator_instance):
        """Check that we can pickle all estimators."""
        estimator = estimator_instance
        set_random_state(estimator)
        fit_args = _make_args(estimator, "fit")
        estimator.fit(*fit_args)

        # Generate results before pickling
        results = {}
        args = {}
        for method in NON_STATE_CHANGING_METHODS:
            if _has_capability(estimator, method):
                args[method] = _make_args(estimator, method)
                results[method] = getattr(estimator, method)(*args[method])

        # Pickle and unpickle
        pickled_estimator = pickle.dumps(estimator)
        unpickled_estimator = pickle.loads(pickled_estimator)

        # Compare against results after pickling
        for method, value in results.items():
            unpickled_result = getattr(unpickled_estimator, method)(*args[method])
            _assert_array_almost_equal(
                value,
                unpickled_result,
                decimal=6,
                err_msg="Results are not the same after pickling",
            )

    # todo: this needs to be diagnosed and fixed - temporary skip
    @pytest.mark.skip(reason="hangs on mac and unix remote tests")
    def test_multiprocessing_idempotent(self, estimator_class, scenario):
        """Test that single and multi-process run results are identical.

        Check that running an estimator on a single process is no different to running
        it on multiple processes. We also check that we can set n_jobs=-1 to make use
        of all CPUs. The test is not really necessary though, as we rely on joblib for
        parallelization and can trust that it works as expected.
        """
        estimator = estimator_class.create_test_instance()
        params = estimator.get_params()

        if "n_jobs" in params:
            for method in NON_STATE_CHANGING_METHODS:
                if _has_capability(estimator, method):
                    # run on a single process
                    # -----------------------
                    estimator = estimator_class.create_test_instance()
                    estimator.set_params(n_jobs=1)
                    set_random_state(estimator)
                    result_single_process = scenario.run(
                        estimator, method_sequence=["fit", method]
                    )

                    # run on multiple processes
                    # -------------------------
                    estimator = estimator_class.create_test_instance()
                    estimator.set_params(n_jobs=-1)
                    set_random_state(estimator)
                    result_multiple_process = scenario.run(
                        estimator, method_sequence=["fit", method]
                    )
                    _assert_array_equal(
                        result_single_process,
                        result_multiple_process,
                        err_msg="Results are not equal for n_jobs=1 and n_jobs=-1",
                    )

    def test_valid_estimator_class_tags(self, estimator_class):
        """Check that Estimator class tags are in VALID_ESTIMATOR_TAGS."""
        for tag in estimator_class.get_class_tags().keys():
            assert tag in VALID_ESTIMATOR_TAGS

    def test_valid_estimator_tags(self, estimator_instance):
        """Check that Estimator tags are in VALID_ESTIMATOR_TAGS."""
        for tag in estimator_instance.get_tags().keys():
            assert tag in VALID_ESTIMATOR_TAGS

    def _get_err_msg(estimator):
        return (
            f"Invalid estimator type: {type(estimator)}. Valid estimator types are: "
            f"{VALID_ESTIMATOR_TYPES}"
        )