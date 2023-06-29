# -*- coding: utf-8 -*-

"""Base class for all feature or spell implementations

In Geomancer, all feature transform primitives are of the class :code:`Spell`.
When defining your own feature primitive, simply create a class that inherits
from :code:`Spell`:

    >>> from geomancer.spells.base import Spell
    >>> class MyNewFeature(Spell):
    >>>     def __init__(self):
    >>>         super(MyNewFeature, self).__init__()

All methods must be implemented in order to not raise a
:code:`NotImplementedError`.
"""

import abc
from loguru import logger

class Spell(abc.ABC):
    """Base class for all feature/spell implementations"""

    @property
    @logger.catch
    def query(self):
        """Defines the BigQuery query for the particular feature"""
        raise NotImplementedError

    @staticmethod
    def cast(on, df, **kwargs):
        """Applies the feature transform to an input DataFrame"""
        raise NotImplementedError




