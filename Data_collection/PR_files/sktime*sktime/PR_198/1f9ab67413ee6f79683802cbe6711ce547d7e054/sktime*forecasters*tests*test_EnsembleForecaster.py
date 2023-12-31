import pytest
import numpy as np
from numpy.testing import assert_array_equal

from sktime.forecasters import DummyForecaster, EnsembleForecaster
from sktime.forecasters import ExpSmoothingForecaster
from sktime.forecasters import ARIMAForecaster
from sktime.datasets import load_shampoo_sales
from sktime.utils.validation.forecasting import validate_fh

__author__ = "Markus LÃ¶ning"


# forecasters
FORECASTERS = (DummyForecaster, ExpSmoothingForecaster, ARIMAForecaster)

# forecast horizons
FHS = (np.array([1]), np.array([1, 3]), np.arange(1, 5))

# load test data
y = load_shampoo_sales()

# test default forecasters output for different forecasters horizons
@pytest.mark.parametrize("fh", FHS)
def test_EnsembleForecaster_fhs(fh):
    estimators = [
        ('ses', ExpSmoothingForecaster()),
        ('last', DummyForecaster(strategy='last'))
    ]
    m = EnsembleForecaster(estimators=estimators)
    m.fit(y, fh=fh)
    y_pred = m.predict()

    # test length of output
    assert len(y_pred) == len(fh)

    # test index
    assert_array_equal(y_pred.index.values, y.index[-1] + fh)


