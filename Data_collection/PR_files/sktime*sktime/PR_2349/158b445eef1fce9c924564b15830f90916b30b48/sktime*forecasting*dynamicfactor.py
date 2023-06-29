# -*- coding: utf-8 -*-
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)

"""Implements DynamicFactor Model."""

from statsmodels.tsa.statespace.dynamic_factor import DynamicFactor as _DynamicFactor

from sktime.forecasting.base.adapters import _StatsModelsAdapter
from sktime.utils.validation._dependencies import _check_soft_dependencies

_all_ = ["DynamicFactor"]
__author__ = ["Ris-Bali"]

_check_soft_dependencies("dynamicfactor", severity="warning")


class DynamicFactor(_StatsModelsAdapter):
    """Dynamic Factor Foracster.

    Direct interface for `statsmodels.tsa.statespace.dynamic_factor

    Parameters
    ----------
    k_factors : int
        The number of unobserved factors.
    factor_order : int
        The order of vector autoregression followed by factors.
    error_cov_type : {'scalar','diagonal','unstructured'} ,default = 'diagonal'
        The structure of the covariance matrix of the observation error term, where
        âunstructuredâ puts no restrictions on the matrix, âdiagonalâ requires it
        to be any diagonal matrix (uncorrelated errors), and âscalarâ requires it
        to be a scalar times the identity matrix.
    error_order : int , default = 0
        The order of the vector autoregression followed by the observation error
        component. Default is None, corresponding to white noise errors.
    error_var : bool , default = False , optional
        Whether or not to model the errors jointly via a vector autoregression,
         rather than as individual autoregression.
    enforce_stationarity : bool default = True
        Whether or not to model the AR parameters to enforce stationarity in the
         autoregressive component of the model.
    start_params :array_like ,default = None
        Initial guess of the solution for the loglikelihood maximization.
    transformed : bool, default = True
        Whether or not start_params is already transformed.
    includes_fixed : bool , default = False
        If parameters were previously fixed with the fix_params method, this argument
         describes whether or not start_params also includes the fixed parameters,
          in addition to the free parameters.
    cov_type : {'opg','oim','approx','robust','robust_approx','none'},default = 'opg'
        âopgâ for the outer product of gradient estimator

        âoimâ for the observed information matrix estimator, calculated
        using the method of Harvey (1989)

        âapproxâ for the observed information matrix estimator, calculated using
         a numerical approximation of the Hessian matrix.

        ârobustâ for an approximate (quasi-maximum likelihood) covariance matrix
         that may be valid even in the presence of some misspecifications.
          Intermediate calculations use the âoimâ method.

        ârobust_approxâ is the same as ârobustâ except that the intermediate
        calculations use the âapproxâ method.

        ânoneâ for no covariance matrix calculation
    cov_kwds :dict or None , default = None
        âapprox_complex_stepâ : bool, optional - If True, numerical approximations are
         computed using complex-step methods. If False, numerical approximations are
         computed using finite difference methods. Default is True.

        âapprox_centeredâ : bool, optional - If True, numerical approximations computed
        using finite difference methods use a centered approximation. Default is False.
    method : str , 'lbfgs'
        ânewtonâ for Newton-Raphson

        ânmâ for Nelder-Mead

        âbfgsâ for Broyden-Fletcher-Goldfarb-Shanno (BFGS)

        âlbfgsâ for limited-memory BFGS with optional box constraints

        âpowellâ for modified Powellâs method

        âcgâ for conjugate gradient

        âncgâ for Newton-conjugate gradient

        âbasinhoppingâ for global basin-hopping solver

    maxiter : int , optional ,default = 50
        The maximum number of iterations to perform.
    full_output : bool , default = 1
        Set to True to have all available output in the
        Results objectâs mle_retvals attribute.
        The output is dependent on the solver.
    disp : bool ,   defualt = 5
        Set to True to print convergence messages.
    callback : callable callback(xk) , default = None
        Called after each iteration, as callback(xk),
        where xk is the current parameter vector.
    return_params : bool ,default = False
        Whether or not to return only the array of maximizing parameters.
    optim_score : {'harvey','approx'} , default = None
        The method by which the score vector is calculated. âharveyâ uses the method
        from Harvey (1989), âapproxâ uses either finite difference or
        complex step differentiation depending upon the value of optim_complex_step,
        and None uses the built-in gradient approximation of the optimizer.
    optim_complex_step : bool , default = True
        Whether or not to use complex step differentiation
        when approximating the score; if False, finite difference approximation is used.
    optim_hessian : {'opg','oim','approx'} , default = None
        âopgâ uses outer product of gradients, âoimâ uses the information
        matrix formula from Harvey (1989), and âapproxâ uses numerical approximation.
    low_memory : bool , default = False
        If set to True, techniques are applied to substantially reduce memory usage.
        If used, some features of the results object will not be available
        (including smoothed results and in-sample prediction),
        although out-of-sample forecasting is possible.

    References
    ----------
    [1] LÃ¼tkepohl, Helmut. 2007. New Introduction to Multiple Time Series Analysis.
    Berlin: Springer.

    """

    _tags = {
        "scitype:y": "multivariate",
        "ignores-exogeneous-X": True,
        "handles-missing-data": True,
        "y_inner_mtype": "pd.Series",
        "X_inner_mtype": "pd.DataFrame",
        "requires-fh-in-fit": False,
        "X-y-must-have-same-index": True,
        "enforce_index_type": None,
        "capability:pred_int": False,
    }

    def __init__(
        self,
        k_factors,
        factor_order,
        exog=None,
        error_cov_type="diagonal",
        error_order=0,
        error_var=False,
        enforce_stationarity=True,
        start_params=None,
        transformed=True,
        includes_fixed=False,
        cov_type=None,
        cov_kwds=None,
        method="ibfgs",
        maxiter=50,
        full_output=1,
        disp=5,
        callback=None,
        return_params=False,
        optim_score=None,
        optim_complex_step=None,
        optim_hessian=None,
        flags=None,
        low_memory=False,
    ):

        self.k_factors = k_factors
        self.factor_order = factor_order
        self.error_cov_type = error_cov_type
        self.error_order = error_order
        self.error_var = error_var
        self.enforce_stationarity = enforce_stationarity
        self.satrt_params = start_params
        self.transformed = transformed
        self.includes_fixed = includes_fixed
        self.cov_type = cov_type
        self.cov_kwds = cov_kwds
        self.method = method
        self.maxiter = maxiter
        self.full_output = full_output
        self.disp = disp
        self.callback = callback
        self.return_params = return_params
        self.optim_score = optim_score
        self.optim_complex_step = optim_complex_step
        self.optim_hessian = optim_hessian
        self.flags = flags
        self.low_memory = low_memory

        super(DynamicFactor, self).__init__()

    def _fit(self, y, X=None, fh=None):
        self._forecaster = _DynamicFactor(
            y,
            k_factors=self.k_factors,
            factor_order=self.factor_order,
            exog=self.exog,
            error_order=self.error_order,
            error_var=self.error_var,
            error_cov_type=self.error_cov_type,
            enforce_stationarity=self.enforce_stationarity,
        )

        self._fitted_forecaster = self._forecaster.fit(
            start_params=self.satrt_params,
            transformed=self.transformed,
            includes_fixed=self.includes_fixed,
            cov_type=self.cov_type,
            cov_kwds=self.cov_kwds,
            method=self.method,
            maxiter=self.maxiter,
            full_output=self.full_output,
            disp=self.disp,
            callback=self.callback,
            return_params=self.return_params,
            optim_score=self.optim_score,
            optim_complex_step=self.optim_complex_step,
            optim_hessian=self.optim_hessian,
            flags=self.flags,
            low_memory=self.low_memory,
        )
