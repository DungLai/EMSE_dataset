# Copyright Contributors to the Pyro project.
# SPDX-License-Identifier: Apache-2.0

import copyreg
import functools
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
        assert dtype is not None
        assert shape is not None

        # in some JAX versions, shape can be np.int64 type
        if get_tracing_state() or get_backend() == "jax":
            if dtype not in (None, "real"):
                dtype = int(dtype)
            if shape is not None:
                shape = tuple(map(int, shape))

        assert cls.dtype in (None, dtype)
        assert cls.shape in (None, shape)
        key = dtype, shape
        result = ArrayType._type_cache.get(key, None)
        if result is None:
            if dtype == "real":
                assert all(isinstance(size, int) and size >= 0 for size in shape)
                name = (
                    "Reals[{}]".format(",".join(map(str, shape))) if shape else "Real"
                )
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
        if not isinstance(subcls, ArrayType):
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

    @property
    def is_concrete(cls):
        # FIXME this should simply be isinstance(cls, Domain)
        return cls.dtype is not None and cls.shape is not None


class BintType(ArrayType):
    def __getitem__(cls, size_shape):
        if isinstance(size_shape, tuple):
            size, shape = size_shape[0], size_shape[1:]
        else:
            size, shape = size_shape, ()
        return super().__getitem__((size, shape))

    def __subclasscheck__(cls, subcls):
        if not isinstance(subcls, BintType):
            return False
        if cls.dtype not in (None, subcls.dtype):
            return False
        if cls.shape not in (None, subcls.shape):
            return False
        return True

    @property
    def size(cls):
        return cls.dtype

    def __iter__(cls):
        from funsor.terms import Number

        return (Number(i, cls.size) for i in range(cls.size))


class RealsType(ArrayType):
    dtype = "real"

    def __getitem__(cls, shape):
        if not isinstance(shape, tuple):
            shape = (shape,)
        return super().__getitem__(("real", shape))

    def __subclasscheck__(cls, subcls):
        if not isinstance(subcls, RealsType):
            return False
        if cls.dtype not in (None, subcls.dtype):
            return False
        if cls.shape not in (None, subcls.shape):
            return False
        return True


def _pickle_array(cls):
    if cls in (Array, Bint, Real, Reals):
        return cls.__name__
    return operator.getitem, (Array, (cls.dtype, cls.shape))


copyreg.pickle(ArrayType, _pickle_array)
copyreg.pickle(BintType, _pickle_array)
copyreg.pickle(RealsType, _pickle_array)


class Array(metaclass=ArrayType):
    """
    Generic factory for :class:`Reals` or :class:`Bint`.

        Arary["real", (3, 3)] = Reals[3, 3]
        Array["real", ()] = Real
    """

    dtype = None
    shape = None


class Bint(metaclass=BintType):
    """
    Factory for bounded integer types::

        Bint[5]           # integers ranging in {0,1,2,3,4}
        Bint[2, 3, 3]     # 3x3 matrices with entries in {0,1}
    """

    dtype = None
    shape = None


class Reals(metaclass=RealsType):
    """
    Type of a real-valued array with known shape::

        Reals[()] = Real  # scalar
        Reals[8]          # vector of length 8
        Reals[3, 3]       # 3x3 matrix
    """

    shape = None


Real = Reals[()]


# DEPRECATED
def reals(*args):
    warnings.warn(
        "reals(...) is deprecated, use Real or Reals[...] instead", DeprecationWarning
    )
    return Reals[args]


# DEPRECATED
def bint(size):
    warnings.warn("bint(...) is deprecated, use Bint[...] instead", DeprecationWarning)
    return Bint[size]


class ProductDomain(Domain):

    _type_cache = WeakValueDictionary()

    def __getitem__(cls, arg_domains):
        try:
            return ProductDomain._type_cache[arg_domains]
        except KeyError:
            assert isinstance(arg_domains, tuple)
            assert all(isinstance(arg_domain, Domain) for arg_domain in arg_domains)
            subcls = type("Product_", (Product,), {"__args__": arg_domains})
            ProductDomain._type_cache[arg_domains] = subcls
            return subcls

    def __repr__(cls):
        return "Product[{}]".format(", ".join(map(repr, cls.__args__)))

    @property
    def __origin__(cls):
        return Product

    @property
    def shape(cls):
        return (len(cls.__args__),)


class Product(tuple, metaclass=ProductDomain):
    """like typing.Tuple, but works with issubclass"""

    __args__ = NotImplemented


@quote.register(BintType)
@quote.register(RealsType)
def _(arg, indent, out):
    out.append((indent, repr(arg)))


@functools.singledispatch
def find_domain(op, *domains):
    r"""
    Finds the :class:`Domain` resulting when applying ``op`` to ``domains``.
    :param callable op: An operation.
    :param Domain \*domains: One or more input domains.
    """
    raise NotImplementedError


@find_domain.register(ops.UnaryOp)
def _find_domain_pointwise_unary_generic(op, domain):
    if isinstance(domain, ArrayType):
        return Array[domain.dtype, domain.shape]
    raise NotImplementedError


@find_domain.register(ops.LogOp)
@find_domain.register(ops.ExpOp)
def _find_domain_log_exp(op, domain):
    return Array["real", domain.shape]


@find_domain.register(ops.SumOp)
def _find_domain_sum(op, domain):
    # Canonicalize dim.
    dim = op.defaults.get("dim", None)
    ndims = len(domain.shape)
    if dim is None:
        dims = set(range(ndims))
    elif isinstance(dim, int):
        dims = {dim % ndims}
    else:
        dims = {i % ndims for i in dim}

    # Compute shape.
    if op.defaults.get("keepdims", False):
        shape = tuple(1 if i in dims else size for i, size in enumerate(domain.shape))
    else:
        shape = tuple(size for i, size in enumerate(domain.shape) if i not in dims)

    # Compute domain.
    if domain.dtype == "real":
        dtype = "real"
    else:
        raise NotImplementedError("TODO")

    return Array[dtype, shape]


@find_domain.register(ops.ReshapeOp)
def _find_domain_reshape(op, domain):
    return Array[domain.dtype, op.defaults["shape"]]


@find_domain.register(ops.GetitemOp)
def _find_domain_getitem(op, lhs_domain, rhs_domain):
    if isinstance(lhs_domain, ArrayType):
        offset = op.defaults["offset"]
        dtype = lhs_domain.dtype
        shape = lhs_domain.shape[:offset] + lhs_domain.shape[1 + offset :]
        return Array[dtype, shape]
    elif isinstance(lhs_domain, ProductDomain):
        # XXX should this return a Union?
        raise NotImplementedError(
            "Cannot statically infer domain from: " f"{lhs_domain}[{rhs_domain}]"
        )


@find_domain.register(ops.BinaryOp)
def _find_domain_pointwise_binary_generic(op, lhs, rhs):
    if (
        isinstance(lhs, ArrayType)
        and isinstance(rhs, ArrayType)
        and lhs.dtype == rhs.dtype
    ):
        return Array[lhs.dtype, broadcast_shape(lhs.shape, rhs.shape)]
    raise NotImplementedError("TODO")


@find_domain.register(ops.FloordivOp)
def _find_domain_floordiv(op, lhs, rhs):
    if isinstance(lhs, ArrayType) and isinstance(rhs, ArrayType):
        shape = broadcast_shape(lhs.shape, rhs.shape)
        if isinstance(lhs.dtype, int) and isinstance(rhs.dtype, int):
            size = (lhs.size - 1) // (rhs.size - 1) + 1
            return Array[size, shape]
        if lhs.dtype == "real" and rhs.dtype == "real":
            return Reals[shape]
    raise NotImplementedError("TODO")


@find_domain.register(ops.ModOp)
def _find_domain_mod(op, lhs, rhs):
    if isinstance(lhs, ArrayType) and isinstance(rhs, ArrayType):
        shape = broadcast_shape(lhs.shape, rhs.shape)
        if isinstance(lhs.dtype, int) and isinstance(rhs.dtype, int):
            dtype = max(0, rhs.dtype - 1)
            return Array[dtype, shape]
        if lhs.dtype == "real" and rhs.dtype == "real":
            return Reals[shape]
    raise NotImplementedError("TODO")


@find_domain.register(ops.MatmulOp)
def _find_domain_matmul(op, lhs, rhs):
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
    return Reals[shape]


@find_domain.register(ops.AssociativeOp)
def _find_domain_associative_generic(op, *domains):

    assert 1 <= len(domains) <= 2

    if len(domains) == 1:
        return Array[domains[0].dtype, ()]

    lhs, rhs = domains
    if lhs.dtype == "real" or rhs.dtype == "real":
        dtype = "real"
    elif op in (ops.add, ops.mul, ops.pow, ops.max, ops.min):
        dtype = op(lhs.dtype - 1, rhs.dtype - 1) + 1
    elif op in (ops.and_, ops.or_, ops.xor):
        dtype = 2
    elif lhs.dtype == rhs.dtype:
        dtype = lhs.dtype
    else:
        raise NotImplementedError("TODO")

    shape = broadcast_shape(lhs.shape, rhs.shape)
    return Array[dtype, shape]


@find_domain.register(ops.WrappedTransformOp)
def _transform_find_domain(op, domain):
    fn = op.defaults["fn"]
    shape = fn.forward_shape(domain.shape)
    return Array[domain.dtype, shape]


@find_domain.register(ops.LogAbsDetJacobianOp)
def _transform_log_abs_det_jacobian(op, domain, codomain):
    # TODO do we need to handle batch shape here?
    return Real


@find_domain.register(ops.StackOp)
def _find_domain_stack(op, parts):
    shape = broadcast_shape(*(x.shape for x in parts))
    dim = op.defaults["dim"]
    if dim >= 0:
        dim = dim - len(shape) - 1
    assert dim < 0
    split = dim + len(shape) + 1
    shape = shape[:split] + (len(parts),) + shape[split:]
    output = Array[parts[0].dtype, shape]
    return output


@find_domain.register(ops.EinsumOp)
def _find_domain_einsum(op, operands):
    equation = op.defaults["equation"]
    ein_inputs, ein_output = equation.split("->")
    ein_inputs = ein_inputs.split(",")
    size_dict = {}
    for ein_input, x in zip(ein_inputs, operands):
        assert x.dtype == "real"
        assert len(ein_input) == len(x.shape)
        for name, size in zip(ein_input, x.shape):
            other_size = size_dict.setdefault(name, size)
            if other_size != size:
                raise ValueError(
                    "Size mismatch at {}: {} vs {}".format(name, size, other_size)
                )
    return Reals[tuple(size_dict[d] for d in ein_output)]


__all__ = [
    "Bint",
    "BintType",
    "Domain",
    "Real",
    "RealsType",
    "Reals",
    "bint",
    "find_domain",
    "reals",
]
