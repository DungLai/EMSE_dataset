# Copyright Contributors to the Pyro project.
# SPDX-License-Identifier: Apache-2.0

import copyreg
import operator
import warnings
from functools import reduce
from weakref import WeakValueDictionary

import funsor.ops as ops
from funsor.util import broadcast_shape, get_backend, get_tracing_state, quote

Domain = type


class ArrayType(Domain):
    """
    Base class of array-like domains.
    """
    _type_cache = WeakValueDictionary()

    def __getitem__(cls, dtype_shape):
        dtype, shape = dtype_shape

        # in some JAX versions, shape can be np.int64 type
        if get_tracing_state() or get_backend() == "jax":
            if dtype not in (None, "real"):
                dtype = int(dtype)
            if shape is not None:
                shape = tuple(map(int, shape))

        assert cls.dtype in (dtype, None)
        assert cls.shape in (shape, None)

        key = dtype, shape
        result = ArrayType._type_cache.get(key, None)
        if result is None:
            if dtype == "real":
                if shape:
                    assert all(isinstance(size, int) and size >= 0 for size in shape)
                    name = "Reals[{}]".format(",".join(map(str, shape)))
                else:
                    name = "Real"
                result = RealsType(name, (), {"shape": shape})
            elif isinstance(dtype, int):
                assert dtype >= 0
                name = "Bint[{}, {}]".format(dtype, ",".join(map(str, shape)))
                result = BintType(name, (), {"dtype": dtype, "shape": shape})
            else:
                raise ValueError("invalid dtype: {}".format(dtype))
            ArrayType._type_cache[key] = result
        return result

    def __subclasscheck__(cls, subcls):
        if not isinstance(subcls, type(subcls)):
            return False
        if cls.dtype not in (None, subcls.dtype):
            return False
        if cls.shape not in (None, subcls.shape):
            return False
        return True

    def __repr__(cls):
        return cls.__name__

    def __str__(cls):
        return cls.__name__

    @property
    def num_elements(cls):
        return reduce(operator.mul, cls.shape, 1)


class RealsType(ArrayType):
    dtype = "real"

    def __getitem__(cls, shape):
        return super().__getitem__(("real", shape))


class BintType(ArrayType):
    def __getitem__(cls, size_shape):
        if isinstance(size_shape, tuple):
            size, shape = size_shape[0], size_shape[1:]
        else:
            size, shape = size_shape, ()
        return super().__getitem__((size, shape))

    @property
    def size(cls):
        return cls.dtype

    def __iter__(cls):
        from funsor.terms import Number
        return (Number(i, cls.size) for i in range(cls.size))


def _pickle_array(cls):
    if cls in (Array, Real, Reals, Bint):
        return cls.__name__
    return operator.getitem, (Array, (cls.dtype, cls.shape))


copyreg.pickle(ArrayType, _pickle_array)
copyreg.pickle(RealsType, _pickle_array)
copyreg.pickle(BintType, _pickle_array)

# Singletons
Array = ArrayType("Array", (), {"dtype": None, "shape": None})

Real = Array["real", ()]
Reals = Array["real", None]
Reals.__doc__ = """
Type of a real-valued array with known shape::

    Reals[()] = Real  # scalar
    Reals[8]          # vector of length 8
    Reals[3,3]        # 3x3 matrix
"""

Bint = BintType("Bint", (), {"dtype": None, "shape": None})
Bint.__doc__ = """
Factory for bounded integer types::

    Bint[5]        # integers ranging in {0,1,2,3,4}
    Bint[2, 3, 3]  # 3x3 matrices with entries in {0,1}
"""


# DEPRECATED
def reals(*args):
    warnings.warn("reals(...) is deprecated, use Reals[...] instead",
                  DeprecationWarning)
    return Reals[args]


# DEPRECATED
def bint(size):
    warnings.warn("reals(...) is deprecated, use Reals[...] instead",
                  DeprecationWarning)
    return Bint[size]


@quote.register(BintType)
@quote.register(RealsType)
def _(arg, indent, out):
    out.append((indent, repr(arg)))


def find_domain(op, *domains):
    r"""
    Finds the :class:`Domain` resulting when applying ``op`` to ``domains``.
    :param callable op: An operation.
    :param Domain \*domains: One or more input domains.
    """
    assert callable(op), op
    assert all(isinstance(arg, Domain) for arg in domains)
    if len(domains) == 1:
        dtype = domains[0].dtype
        shape = domains[0].shape
        if op is ops.log or op is ops.exp:
            dtype = 'real'
        elif isinstance(op, ops.ReshapeOp):
            shape = op.shape
        elif isinstance(op, ops.AssociativeOp):
            shape = ()
        return reals(*shape) if dtype == "real" else bint(dtype)

    lhs, rhs = domains
    if isinstance(op, ops.GetitemOp):
        dtype = lhs.dtype
        shape = lhs.shape[:op.offset] + lhs.shape[1 + op.offset:]
        return reals(*shape) if dtype == "real" else bint(dtype)
    elif op == ops.matmul:
        assert lhs.shape and rhs.shape
        if len(rhs.shape) == 1:
            assert lhs.shape[-1] == rhs.shape[-1]
            shape = lhs.shape[:-1]
        elif len(lhs.shape) == 1:
            assert lhs.shape[-1] == rhs.shape[-2]
            shape = rhs.shape[:-2] + rhs.shape[-1:]
        else:
            assert lhs.shape[-1] == rhs.shape[-2]
            shape = broadcast_shape(lhs.shape[:-1], rhs.shape[:-2] + (1,)) + rhs.shape[-1:]
        return reals(*shape)

    if lhs.dtype == 'real' or rhs.dtype == 'real':
        dtype = 'real'
    elif op in (ops.add, ops.mul, ops.pow, ops.max, ops.min):
        dtype = op(lhs.dtype - 1, rhs.dtype - 1) + 1
    elif op in (ops.and_, ops.or_, ops.xor):
        dtype = 2
    elif lhs.dtype == rhs.dtype:
        dtype = lhs.dtype
    else:
        raise NotImplementedError('TODO')

    if lhs.shape == rhs.shape:
        shape = lhs.shape
    else:
        shape = broadcast_shape(lhs.shape, rhs.shape)
    return reals(*shape) if dtype == "real" else bint(dtype)


__all__ = [
    'Bint',
    'BintType',
    'Domain',
    'Real',
    'RealsType',
    'Reals',
    'bint',
    'find_domain',
    'reals',
]
