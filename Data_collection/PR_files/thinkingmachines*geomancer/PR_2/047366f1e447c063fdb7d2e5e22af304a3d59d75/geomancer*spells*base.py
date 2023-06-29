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

class Spell(abc.ABC):
    """Base class for all feature/spell implementations"""
    pass




