#!/usr/bin/env python3 -u
# coding: utf-8
<<<<<<< HEAD
=======
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)
>>>>>>> 67c56be8b1e838f2628df829946f795b7dba9aed

__author__ = ["Markus LÃ¶ning"]
__all__ = ["BaseEstimator"]

from sklearn.base import BaseEstimator as _BaseEstimator
from sktime.exceptions import NotFittedError


class BaseEstimator(_BaseEstimator):

<<<<<<< HEAD
=======
    # def __init__(self, *args, **kwargs):
    #     # Including args and kwargs make the class cooperative, so that args
    #     # and kwargs are passed on to other parent classes when using
    #     # multiple inheritance
    #     self._is_fitted = False
    #     super(BaseEstimator, self).__init__(*args, **kwargs)

>>>>>>> 67c56be8b1e838f2628df829946f795b7dba9aed
    def __init__(self):
        self._is_fitted = False

    @property
    def is_fitted(self):
        """Has `fit` been called?"""
        return self._is_fitted

    def check_is_fitted(self):
<<<<<<< HEAD
        """Check if the forecaster has been fitted.
=======
        """Check if the estimator has been fitted.
>>>>>>> 67c56be8b1e838f2628df829946f795b7dba9aed

        Raises
        ------
        NotFittedError
<<<<<<< HEAD
            if the forecaster has not been fitted yet.
        """
        if not self.is_fitted:
            raise NotFittedError(f"This instance of {self.__class__.__name__} has not "
                                 f"been fitted yet; please call `fit` first.")
=======
            If the estimator has not been fitted yet.
        """
        if not self.is_fitted:
            raise NotFittedError(
                f"This instance of {self.__class__.__name__} has not "
                f"been fitted yet; please call `fit` first.")
>>>>>>> 67c56be8b1e838f2628df829946f795b7dba9aed
