import pytest
import numpy as np
import pandas as pd
from numpy.testing import assert_array_equal

from sktime.forecasting import ExpSmoothingForecaster
from sktime.datasets import load_shampoo_sales
from sktime.performance_metrics.forecasting import smape_score
from sktime.utils.validation.forecasting import validate_fh

__author__ = ["Markus LÃ¶ning", "big-o@github"]


# forecast horizons
FHS = ([1], [1, 3], np.array([1]), np.array([1, 3]), np.arange(5)+1)

# load test data
y = load_shampoo_sales()


# test default forecasters output for different forecasters horizons
@pytest.mark.filterwarnings('ignore::FutureWarning')
@pytest.mark.parametrize("fh", FHS)
def test_fhs(fh):
    m = ExpSmoothingForecaster()

    m.fit(y, fh=fh)
    y_pred = m.predict(fh=fh)

    # adjust for default value
    fh = validate_fh(fh)

    # test length of output
    assert len(y_pred) == len(fh)

    # test index
    assert_array_equal(y_pred.index.values, y.index[-1] + fh)


@pytest.mark.filterwarnings('ignore::FutureWarning')
def test_set_params():
    params = {"trend": "additive"}

    m = ExpSmoothingForecaster(**params)
    m.fit(y, fh=1)
    expected = m.predict()

    m = ExpSmoothingForecaster()
    m.set_params(**params)
    m.fit(y, fh=1)
    y_pred = m.predict()

    assert_array_equal(y_pred, expected)


@pytest.mark.filterwarnings('ignore::FutureWarning')
def test_score():
    m = ExpSmoothingForecaster()
    train = y.iloc[:30]
    test = y.iloc[30:]
    fh = np.arange(len(test)) + 1
    m.fit(train, fh=fh)
    y_pred = m.predict(fh=fh)
    expected = smape_score(y_pred, test)
    assert m.score(test, fh=fh) == expected
