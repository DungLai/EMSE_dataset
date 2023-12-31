#!/usr/bin/env python3 -u
# -*- coding: utf-8 -*-
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)
"""Test grid search CV."""

__author__ = ["mloning"]
__all__ = ["test_gscv", "test_rscv"]

import numpy as np
import pytest
from sklearn.model_selection import ParameterGrid, ParameterSampler

from sktime.datasets import load_longley
from sktime.exceptions import NotFittedError
from sktime.forecasting.arima import ARIMA
from sktime.forecasting.compose import TransformedTargetForecaster
from sktime.forecasting.model_evaluation import evaluate
from sktime.forecasting.model_selection import (
    ForecastingGridSearchCV,
    ForecastingRandomizedSearchCV,
    SingleWindowSplitter,
    SlidingWindowSplitter,
)
from sktime.forecasting.naive import NaiveForecaster
from sktime.forecasting.tests._config import (
    TEST_N_ITERS,
    TEST_OOS_FHS,
    TEST_RANDOM_SEEDS,
    TEST_WINDOW_LENGTHS_INT,
)
from sktime.forecasting.trend import PolynomialTrendForecaster
from sktime.performance_metrics.forecasting import (
    MeanAbsolutePercentageError,
    MeanSquaredError,
)
from sktime.transformations.series.detrend import Detrender

TEST_METRICS = [MeanAbsolutePercentageError(symmetric=True), MeanSquaredError()]


def _check_no_fitted_params_before_fitting(tuner):
    assert not tuner.is_fitted
    with pytest.raises(NotFittedError):
        tuner.get_fitted_params()


def _get_expected_scores(forecaster, cv, param_grid, y, X, scoring):
    scores = np.zeros(len(param_grid))
    for i, params in enumerate(param_grid):
        f = forecaster.clone()
        f.set_params(**params)
        out = evaluate(f, cv, y, X=X, scoring=scoring)
        scores[i] = out.loc[:, f"test_{scoring.name}"].mean()
    return scores


def _check_cv(forecaster, tuner, cv, param_grid, y, X, scoring):
    actual = tuner.cv_results_[f"mean_test_{scoring.name}"]

    expected = _get_expected_scores(forecaster, cv, param_grid, y, X, scoring)
    np.testing.assert_array_equal(actual, expected)

    # Check if best parameters are selected.
    best_idx = tuner.best_index_
    assert best_idx == actual.argmin()

    fitted_params = tuner.get_fitted_params()

    best_params = fitted_params["best_hyper_parameters"]
    assert best_params == param_grid[best_idx]

    # Check if best parameters are contained in best forecaster.
    best_forecaster_params = fitted_params["best_estimator"].get_params()
    assert best_params.items() <= best_forecaster_params.items()


NAIVE = NaiveForecaster(strategy="mean")
NAIVE_GRID = {"window_length": TEST_WINDOW_LENGTHS_INT}
PIPE = TransformedTargetForecaster(
    [
        ("transformer", Detrender(PolynomialTrendForecaster())),
        ("forecaster", ARIMA()),
    ]
)
PIPE_GRID = {
    "transformer__forecaster__degree": [1, 2],
    "forecaster__with_intercept": [True, False],
}
CVs = [
    *[SingleWindowSplitter(fh=fh) for fh in TEST_OOS_FHS],
    SlidingWindowSplitter(fh=1, initial_window=15),
]


@pytest.mark.parametrize(
    "forecaster, param_grid", [(NAIVE, NAIVE_GRID), (PIPE, PIPE_GRID)]
)
@pytest.mark.parametrize("scoring", TEST_METRICS)
@pytest.mark.parametrize("cv", CVs)
def test_gscv(forecaster, param_grid, cv, scoring):
    """Test ForecastingGridSearchCV."""
    y, X = load_longley()
    gscv = ForecastingGridSearchCV(
        forecaster, param_grid=param_grid, cv=cv, scoring=scoring
    )
    _check_no_fitted_params_before_fitting(gscv)

    gscv.fit(y, X)

    param_grid = ParameterGrid(param_grid)
    _check_cv(forecaster, gscv, cv, param_grid, y, X, scoring)


@pytest.mark.parametrize(
    "forecaster, param_grid", [(NAIVE, NAIVE_GRID), (PIPE, PIPE_GRID)]
)
@pytest.mark.parametrize("scoring", TEST_METRICS)
@pytest.mark.parametrize("cv", CVs)
@pytest.mark.parametrize("n_iter", TEST_N_ITERS)
@pytest.mark.parametrize("random_state", TEST_RANDOM_SEEDS)
def test_rscv(forecaster, param_grid, cv, scoring, n_iter, random_state):
    """Test ForecastingRandomizedSearchCV.

    Tests that ForecastingRandomizedSearchCV successfully searches the
    parameter distributions to identify the best parameter set
    """
    y, X = load_longley()
    rscv = ForecastingRandomizedSearchCV(
        forecaster,
        param_distributions=param_grid,
        cv=cv,
        scoring=scoring,
        n_iter=n_iter,
        random_state=random_state,
    )
    _check_no_fitted_params_before_fitting(rscv)

    rscv.fit(y, X)

    param_distributions = list(
        ParameterSampler(param_grid, n_iter, random_state=random_state)
    )
    _check_cv(forecaster, rscv, cv, param_distributions, y, X, scoring)
