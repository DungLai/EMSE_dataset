import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX
# SARIMAX is better maintained and offers the same functionality as standard ARIMA class
# https://github.com/statsmodels/statsmodels/issues/3884
from sklearn.utils.validation import check_is_fitted

from sktime.forecasters.base import BaseForecaster, DEFAULT_CLVL
from sktime.forecasters.base import BaseSingleSeriesForecaster
from sktime.forecasters.base import BaseUpdateableForecaster
from sktime.transformers.forecasting import Deseasonaliser
from sktime.utils.confidence import zscore
from sktime.utils.validation.forecasting import validate_sp
from sktime.utils.seasonality import seasonality_test
from sktime.utils.time_series import fit_trend

__all__ = [
    "ARIMAForecaster",
    "ExpSmoothingForecaster",
    "DummyForecaster",
    "ThetaForecaster"
]
__author__ = ['Markus LÃ¶ning', 'big-o@github']


class ARIMAForecaster(BaseUpdateableForecaster):
    """
    ARIMA (Auto-regressive Integrated Moving-average) forecaster.

    Parameters
    ----------
    order : tuple, optional (default=(1, 0, 0))
        The (p,d,q) order of the model for the number of AR parameters, differences, and MA parameters. d must be an
        integer indicating the integration order of the process, while p and q may either be an integers indicating the
        AR and MA orders (so that all lags up to those orders are included) or else iterables giving specific AR and /
        or MA lags to include. Default is an AR(1) model: (1,0,0).
    seasonal_order : tuple, optional (default=(0, 0, 0, 0))
        The (P,D,Q,s) order of the seasonal component of the model for the AR parameters, differences, MA parameters,
        and periodicity. d must be an integer indicating the integration order of the process, while p and q may either
        be an integers indicating the AR and MA orders (so that all lags up to those orders are included) or else
        iterables giving specific AR and / or MA lags to include. s is an integer giving the periodicity (number of
        periods in season), often it is 4 for quarterly data or 12 for monthly data. Default is no seasonal effect.
    trend : str{'n','c','t','ct'} or iterable, optional
        Parameter controlling the deterministic trend polynomial :math:`A(t)`.
        Can be specified as a string where 'c' indicates a constant (i.e. a
        degree zero component of the trend polynomial), 't' indicates a
        linear trend with time, and 'ct' is both. Can also be specified as an
        iterable defining the polynomial as in `numpy.poly1d`, where
        `[1,1,0,1]` would denote :math:`a + bt + ct^3`. Default is to not
        include a trend component.
    enforce_stationarity : boolean, optional
        Whether or not to transform the AR parameters to enforce stationarity
        in the autoregressive component of the model. Default is True.
    enforce_invertibility : boolean, optional
        Whether or not to transform the MA parameters to enforce invertibility
        in the moving average component of the model. Default is True.
    method : str, optional (default='lbfgs')
        The method determines which solver from scipy.optimize is used, and it can be chosen from
        among the following strings:
        - ânewtonâ for Newton-Raphson, ânmâ for Nelder-Mead
        - âbfgsâ for Broyden-Fletcher-Goldfarb-Shanno (BFGS)
        - âlbfgsâ for limited-memory BFGS with optional box constraints
        - âpowellâ for modified Powellâs method
        - âcgâ for conjugate gradient
        - âncgâ for Newton-conjugate gradient
        - âbasinhoppingâ for global basin-hopping solver
        The explicit arguments in fit are passed to the solver, with the exception of the basin-hopping solver.
        Each solver has several optional arguments that are not the same across solvers.
        See the notes section below (or scipy.optimize) for the available arguments and for the list of explicit
        arguments that the basin-hopping solver supports.
    maxiter : int, optional (default=1000)
        The maximum number of iterations to perfom in fitting the likelihood to the data.
    """

    def __init__(self, order=(1, 0, 0), seasonal_order=(0, 0, 0, 0), trend='n', enforce_stationarity=True,
                 enforce_invertibility=True, maxiter=1000, method='lbfgs', disp=0):
        # TODO add more constructor/fit options from statsmodels

        # Input checks.
        self._check_order(order, 3)
        self._check_order(seasonal_order, 4)

        self.order = order
        self.seasonal_order = seasonal_order
        self.trend = trend
        self.method = method
        self.enforce_stationarity = enforce_stationarity
        self.enforce_invertibility = enforce_invertibility
        self.maxiter = maxiter
        self.disp = disp
        super(ARIMAForecaster, self).__init__()

    def _fit(self, y, fh=None, X=None):
        """
        Internal fit.

        Parameters
        ----------
        y : pandas.Series
            Target time series to which to fit the forecaster.
        fh : array-like, optional (default=[1])
            The forecasters horizon with the steps ahead to to predict.
        X : pandas.DataFrame, shape=[n_obs, n_vars], optional (default=None)
            An optional 2-d dataframe of exogenous variables. If provided, these
            variables are used as additional features in the regression
            operation. This should not include a constant or trend. Note that
            if an ``ARIMA`` is fit on exogenous features, it must also be provided
            exogenous features for making predictions.

        Returns
        -------
        self : returns an instance of self.
        """
        # unnest series
        X = self._prepare_X(X)

        # fit estimator
        self._estimator = SARIMAX(y,
                                  exog=X,
                                  order=self.order,
                                  seasonal_order=self.seasonal_order,
                                  trend=self.trend,
                                  enforce_stationarity=self.enforce_stationarity,
                                  enforce_invertibility=self.enforce_invertibility)
        self._fitted_estimator = self._estimator.fit(maxiter=self.maxiter, method=self.method, disp=self.disp)
        return self

    def _update(self, y, X=None):
        """
        Internal update of forecasts using new data via Kalman smoothing/filtering of
        forecasts obtained from previously fitted forecaster.

        Parameters
        ----------
        y : pandas.Series
            Updated time series which to use for updating the previously fitted forecaster.
        X : pandas.DataFrame, shape=[n_obs, n_vars], optional (default=None)
            An optional 2-d dataframe of exogenous variables. If provided, these
            variables are used as additional features in the regression
            operation. This should not include a constant or trend. Note that
            if an ``ARIMA`` is fit on exogenous features, it must also be provided
            exogenous features for making predictions.

        Returns
        -------
        self : An instance of self
        """
        # TODO for updating see https://github.com/statsmodels/statsmodels/issues/2788 and
        #  https://github.com/statsmodels/statsmodels/issues/3318

        # unnest series
        # unnest series
        X = self._prepare_X(X)

        # Update estimator.
        estimator = SARIMAX(y,
                            exog=X,
                            order=self.order,
                            seasonal_order=self.seasonal_order,
                            trend=self.trend,
                            enforce_stationarity=self.enforce_stationarity,
                            enforce_invertibility=self.enforce_invertibility)
        estimator.initialize_known(self._fitted_estimator.predicted_state[:, -1],
                                   self._fitted_estimator.predicted_state_cov[:, :, -1])

        # Filter given fitted parameters.
        self._updated_estimator = estimator.smooth(self._fitted_estimator.params)
        return self

    def _predict(self, fh=None, X=None):
        """
        Internal predict using fitted estimator.

        Parameters
        ----------
        fh : array-like, optional (default=None)
            The forecasters horizon with the steps ahead to to predict. Default is one-step ahead forecast,
            i.e. np.array([1])
        X : pandas.DataFrame, shape=[n_obs, n_vars], optional (default=None)
            An optional 2-d dataframe of exogenous variables. If provided, these
            variables are used as additional features in the regression
            operation. This should not include a constant or trend. Note that if
            provided, the forecaster must also have been fitted on the exogenous
            features.

        Returns
        -------
        Predictions : pandas.Series, shape=(len(fh),)
            Returns series of predicted values.
        """

        # unnest series
        X = self._prepare_X(X)

        # Adjust forecasters horizon to time index seen in fit, (assume sorted forecasters horizon)
        fh = len(self._time_index) - 1 + fh
        start = fh[0]
        end = fh[-1]

        # Predict updated (pre-initialised) model with start and end values relative to end of train series
        if self._is_updated:
            y_pred = self._updated_estimator.predict()

        # Predict fitted model with start and end points relative to start of train series
        else:
            y_pred = self._fitted_estimator.predict(start=start, end=end, exog=X)

        # Forecast all periods from start to end of pred horizon, but only return given time points in pred horizon
        fh_idx = fh - np.min(fh)
        return y_pred.iloc[fh_idx]

    @staticmethod
    def _check_order(order, n):
        """Helper function to check passed order for ARIMA estimator.

        Parameters
        ----------
        order : tuple
            Estimator order
        n : int
            Length of order
        """
        if not (isinstance(order, tuple) and (len(order) == n)):
            raise ValueError(f'Order must be a tuple of length f{n}')

        if not all(np.issubdtype(type(k), np.integer) for k in order):
            raise ValueError(f'All values in order must be integers')


class ExpSmoothingForecaster(BaseSingleSeriesForecaster):
    """
    Holt-Winters exponential smoothing forecaster. Default settings use simple exponential smoothing
    without trend and seasonality components.

    Parameters
    ----------
    trend : str{"add", "mul", "additive", "multiplicative", None}, optional (default=None)
        Type of trend component.
    damped : bool, optional (default=None)
        Should the trend component be damped.
    seasonal : {"add", "mul", "additive", "multiplicative", None}, optional (default=None)
        Type of seasonal component.
    seasonal_periods : int, optional (default=None)
        The number of seasons to consider for the holt winters.
    smoothing_level : float, optional
        The alpha value of the simple exponential smoothing, if the value
        is set then this value will be used as the value.
    smoothing_slope : float, optional
        The beta value of the Holt's trend method, if the value is
        set then this value will be used as the value.
    smoothing_seasonal : float, optional
        The gamma value of the holt winters seasonal method, if the value
        is set then this value will be used as the value.
    damping_slope : float, optional
        The phi value of the damped method, if the value is
        set then this value will be used as the value.
    optimized : bool, optional
        Estimate model parameters by maximizing the log-likelihood
    use_boxcox : {True, False, 'log', float}, optional
        Should the Box-Cox transform be applied to the data first? If 'log'
        then apply the log. If float then use lambda equal to float.
    remove_bias : bool, optional
        Remove bias from forecast values and fitted values by enforcing
        that the average residual is equal to zero.
    use_basinhopping : bool, optional
        Using Basin Hopping optimizer to find optimal values

    References
    ----------
    [1] Hyndman, Rob J., and George Athanasopoulos. Forecasting: principles
        and practice. OTexts, 2014.
    """

    def __init__(self, trend=None, damped=False, seasonal=None, seasonal_periods=None, smoothing_level=None,
                 smoothing_slope=None, smoothing_seasonal=None, damping_slope=None, optimized=True,
                 use_boxcox=False, remove_bias=False, use_basinhopping=False):
        # Model params
        self.trend = trend
        self.damped = damped
        self.seasonal = seasonal
        self.seasonal_periods = seasonal_periods

        # Fit params
        self.smoothing_level = smoothing_level
        self.optimized = optimized
        self.smoothing_slope = smoothing_slope
        self.smooting_seasonal = smoothing_seasonal
        self.damping_slope = damping_slope
        self.use_boxcox = use_boxcox
        self.remove_bias = remove_bias
        self.use_basinhopping = use_basinhopping
        super(ExpSmoothingForecaster, self).__init__()

    def _fit(self, y, fh=None):
        """
        Internal fit.

        Parameters
        ----------
        y : pandas.Series
            Target time series to which to fit the forecaster.
        fh : array-like, optional (default=[1])
            The forecasters horizon with the steps ahead to to predict.
        Returns
        -------
        self : returns an instance of self.
        """

        # Fit forecaster.
        self.estimator = ExponentialSmoothing(y, trend=self.trend, damped=self.damped, seasonal=self.seasonal,
                                              seasonal_periods=self.seasonal_periods)
        self._fitted_estimator = self.estimator.fit(smoothing_level=self.smoothing_level, optimized=self.optimized,
                                                    smoothing_slope=self.smoothing_slope,
                                                    smoothing_seasonal=self.smooting_seasonal,
                                                    damping_slope=self.damping_slope,
                                                    use_boxcox=self.use_boxcox, remove_bias=self.remove_bias,
                                                    use_basinhopping=self.use_basinhopping)
        return self


class ThetaForecaster(ExpSmoothingForecaster):
    """
    Theta method of forecasting.

    The theta method as defined in [1]_ is equivalent to simple exponential smoothing
    (SES) with drift. This is demonstrated in [2]_.

    The series is tested for seasonality using the test outlined in A&N. If deemed
    seasonal, the series is seasonally adjusted using a classical multiplicative
    decomposition before applying the theta method. The resulting forecasts are then
    reseasonalized.

    In cases where SES results in a constant forecast, the theta forecaster will revert
    to predicting the SES constant plus a linear trend derived from the training data.

    Prediction intervals are computed using the underlying state space model.

    Parameters
    ----------

    smoothing_level : float, optional
        The alpha value of the simple exponential smoothing, if the value is set then
        this will be used, otherwise it will be estimated from the data.

    deseasonaliser : :class:`sktime.transformers.Deseasonaliser`, optional (default=None)
        A transformer to use for seasonal adjustments. Overrides the
        ``seasonal_periods`` parameter.

    seasonal_periods : int, optional (default=1)
        The number of observations that constitute a seasonal period for a
        multiplicative deseasonaliser, which is used if seasonality is detected in the
        training data. Ignored if a deseasonaliser transformer is provided. Default is
        1 (no seasonality).

    check_input : bool, optional (default=True)
        - If True, input are checked.
        - If False, input are not checked and assumed correct. Use with caution.

    Attributes
    ----------

    smoothing_level_ : float
        The estimated alpha value of the SES fit.

    drift_ : float
        The estimated drift of the fitted model.

    se_ : float
        The standard error of the predictions. Used to calculate prediction intervals.

    References
    ----------

    .. [1] `Assimakopoulos, V. and Nikolopoulos, K. The theta model: a decomposition
           approach to forecasting. International Journal of Forecasting 16, 521-530,
           2000.
           <https://www.sciencedirect.com/science/article/pii/S0169207000000662>`_

    .. [2] `Hyndman, Rob J., and Billah, Baki. Unmasking the Theta method.
           International J. Forecasting, 19, 287-290, 2003.
           <https://www.sciencedirect.com/science/article/pii/S0169207001001431>`_
    """

    def __init__(
        self,
        smoothing_level=None,
        deseasonaliser=None,
        seasonal_periods=1,
    ):
        self.deseasonaliser = deseasonaliser
        self.seasonal_periods = seasonal_periods
        self.smoothing_level = smoothing_level

        if deseasonaliser:
            self._deseasonaliser = deseasonaliser
        elif seasonal_periods is not None:
            self._deseasonaliser = Deseasonaliser(
                model="multiplicative", sp=seasonal_periods
            )
        else:
            raise ValueError(
                "One of 'seasonal_periods' or 'deseasonaliser' must be provided."
            )

        super(ThetaForecaster, self).__init__(
            smoothing_level=smoothing_level,
        )

    def _to_nested(self, y):
        nested = pd.DataFrame(pd.Series([y]))

        return nested

    def _fit(self, y, fh=None):
        """
        Internal fit.

        Parameters
        ----------

        y : pandas.Series
            Target time series to which to fit the forecaster.
        fh : array-like, optional (default=[1])
            The forecasters horizon with the steps ahead to to predict.

        Returns
        -------

        self : returns an instance of self.
        """

        if self._deseasonaliser.sp == 1:
            self._is_seasonal = False
        else:
            self._is_seasonal = seasonality_test(y, freq=self._deseasonaliser.sp)

        if self._is_seasonal:
            y_nested = self._to_nested(y)
            y = self._deseasonaliser.fit_transform(y_nested).iloc[0, 0]

        # Find theta lines.

        # Theta lines are just SES + drift.
        super()._fit(y, fh=fh)
        self.smoothing_level_ = self._fitted_estimator.params["smoothing_level"]

        # Drift calculated through least squares regression.
        coefs = fit_trend(y.values.reshape(1, -1), order=1)
        self.trend_ = coefs[0, 0] / 2

        return self

    def _predict(self, fh=None):
        """
        Internal predict.

        Parameters
        ----------

        fh : array-like
            The forecasters horizon with the steps ahead to to predict. Default is
            one-step ahead forecast, i.e. np.array([1]).

        Returns
        -------

        y_pred : pandas.Series
            Returns series of predicted values.
        """

        check_is_fitted(self, "_time_index")
        check_is_fitted(self, "smoothing_level_")
        check_is_fitted(self, "trend_")

        # SES
        y_pred = super()._predict(fh=fh)

        if np.isclose(self.smoothing_level_, 0.0):
            # SES was constant so revert to simple trend
            drift = self.trend_ * fh
        else:
            # Calculate drift from SES parameters
            n_obs = len(self._time_index)
            drift = self.trend_ * (fh +
                (1 - (1 - self.smoothing_level_) ** n_obs) / self.smoothing_level_
            )

        y_pred += drift

        if self._is_seasonal:
            # Reseasonalise.
            y_pred_nested = self._to_nested(y_pred)
            y_pred = self._deseasonaliser.inverse_transform(y_pred_nested).iloc[0, 0]

        return y_pred

    def _prediction_errors(self, fh, conf_lvl=DEFAULT_CLVL):
        check_is_fitted(self, "_time_index")
        check_is_fitted(self, "smoothing_level_")

        n_obs = len(self._time_index)
        self.sigma_ = np.sqrt(self._fitted_estimator.sse / (n_obs - 1))
        sem = self.sigma_ * np.sqrt(fh * self.smoothing_level_ ** 2 + 1)

        z = zscore(conf_lvl)

        # Adjust forecasters horizon to time index seen in fit, (assume sorted
        # forecasters horizon)
        fh = len(self._time_index) - 1 + fh

        return pd.Series(index=fh, data=z*sem)


class DummyForecaster(BaseForecaster):
    """
    Dummy forecaster for naive forecasters approaches.

    Parameters
    ----------
    strategy : str{'mean', 'last', 'linear'}, optional (default='last')
        Naive forecasters strategy
    sp : int
        Seasonal periodicity
    """

    def __init__(self, strategy='last', sp=None):

        # TODO add constant strategy
        allowed_strategies = ('mean', 'last', 'linear', 'seasonal_last')
        if strategy not in allowed_strategies:
            raise ValueError(f'Unknown strategy: {strategy}, expected one of {allowed_strategies}')

        if strategy == 'seasonal_last':
            if sp is None:
                raise ValueError("Seasonal periodicity (sp) has to be specified "
                                 "when the 'seasonal_last' strategy is used.")

        self.sp = validate_sp(sp)
        self.strategy = strategy
        self._y_pred = None
        super(DummyForecaster, self).__init__()

    def _fit(self, y, fh=None):
        """
        Internal fit.

        Parameters
        ----------
        y : pandas.Series
            Target time series to which to fit the forecaster.
        fh : array-like, optional (default=[1])
            The forecasters horizon with the steps ahead to to predict.

        Returns
        -------
        self : returns an instance of self.
        """

        if fh is None:
            raise ValueError(f"{self.__class__.__name__} requires to specify the forecasting horizon in `fit`")

        # Convert step-ahead prediction horizon into zero-based index
        self._fh = fh
        len_fh = len(fh)

        # Fit estimator.
        if self.strategy == 'mean':
            y_pred = np.repeat(np.mean(y), len_fh)

        elif self.strategy == 'last':
            y_pred = np.repeat(y.iloc[-1], len_fh)

        elif self.strategy == 'linear':
            # get start and end of forecast horizon
            fh = len(self._time_index) - 1 + fh
            start = fh[0]
            end = fh[-1]

            # fit linear model
            estimator = SARIMAX(y, order=(0, 0, 0), trend='t')
            fitted_estimator = estimator.fit()
            y_pred = fitted_estimator.predict(start=start, end=end)

            # select forecast steps
            fh_idx = fh - np.min(fh)
            y_pred = y_pred.iloc[fh_idx].values

        elif self.strategy == 'seasonal_last':
            # for seasonal periodicity of 1, forecast mean
            if self.sp == 1:
                y_pred = np.repeat(np.mean(y), len_fh)
            else:
                y_pred = y.iloc[-self.sp:(-self.sp + len_fh)]

        self._y_pred = y_pred
        return self

    def _predict(self, fh=None):
        """
        Internal predict.

        Parameters
        ----------
        fh : array-like
            The forecasters horizon with the steps ahead to to predict. Default is one-step ahead forecast,
            i.e. np.array([1])

        Returns
        -------
        y_pred : pandas.Series
            Returns series of predicted values.
        """
        y_pred = self._y_pred

        # return as series and add index
        time_index = self._time_index[-1] + fh
        return pd.Series(y_pred, index=time_index)
