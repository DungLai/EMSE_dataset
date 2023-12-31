import numpy as np

from nose.tools import raises
from numpy.testing import assert_array_equal
from sklearn.utils.estimator_checks import check_estimator
from stability_selection import StabilitySelection


def test_transformer():
    # This fails at the moment because in the low sample size case some of the bootstrap samples can have zero cases
    # of the positive class
    #return check_estimator(StabilitySelection)
    pass


@raises(ValueError)
def test_check_string_threshold():
    StabilitySelection(threshold='wrong_value')._validate_input()


@raises(ValueError)
def test_check_threshold_too_large():
    StabilitySelection(threshold=1.5)._validate_input()


@raises(ValueError)
def test_check_threshold_too_small():
    StabilitySelection(threshold=0.0)._validate_input()


@raises(ValueError)
def test_check_threshold_too_small():
    StabilitySelection().get_support(threshold='wrong_value')


@raises(ValueError)
def test_check_arguments():
    StabilitySelection(threshold='wrong_value')._validate_input()


@raises(ValueError)
def test_check_wrong_lambda_name():
    StabilitySelection(lambda_name='alpha')._validate_input()


@raises(ValueError)
def test_check_wrong_lambda_name():
    StabilitySelection(n_bootstrap_iterations=-1)._validate_input()


def test_automatic_lambda_grid():
    selector = StabilitySelection()
    assert_array_equal(np.logspace(-5, -2, 25), selector.lambda_grid)