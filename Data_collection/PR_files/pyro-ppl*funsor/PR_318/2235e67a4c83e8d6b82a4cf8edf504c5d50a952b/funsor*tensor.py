# Copyright Contributors to the Pyro project.
# SPDX-License-Identifier: Apache-2.0

import functools
import itertools
import warnings
from collections import OrderedDict
from contextlib import contextmanager
from functools import reduce

import numpy as np
import opt_einsum
from multipledispatch import dispatch
from multipledispatch.variadic import Variadic

import funsor.ops as ops
from funsor.delta import Delta
from funsor.domains import Domain, bint, find_domain, reals
from funsor.ops import GetitemOp, MatmulOp, Op, ReshapeOp
from funsor.terms import (
    Binary,
    Funsor,
    FunsorMeta,
    Lambda,
    Number,
    Slice,
    Unary,
    Variable,
    eager,
    substitute,
    to_data,
    to_funsor
)
from funsor.util import getargspec, get_backend, get_tracing_state, is_nn_module, quote


def get_default_prototype():
    backend = get_backend()
    if backend == "torch":
        import torch

        return torch.tensor([])
    else:
        return np.array([])


def _nameof(fn):
    return getattr(fn, '__name__', type(fn).__name__)


@contextmanager
def ignore_jit_warnings():
    with warnings.catch_warnings():
        if get_backend() == "torch":
            import torch

            warnings.filterwarnings("ignore", category=torch.jit.TracerWarning)
        yield


class TensorMeta(FunsorMeta):
    """
    Wrapper to fill in default args and convert between OrderedDict and tuple.
    """
    def __call__(cls, data, inputs=None, dtype="real"):
        if inputs is None:
            inputs = tuple()
        elif isinstance(inputs, OrderedDict):
            inputs = tuple(inputs.items())
        return super(TensorMeta, cls).__call__(data, inputs, dtype)


class Tensor(Funsor, metaclass=TensorMeta):
    """
    Funsor backed by a PyTorch Tensor or a NumPy ndarray.

    This follows the :mod:`torch.distributions` convention of arranging
    named "batch" dimensions on the left and remaining "event" dimensions
    on the right. The output shape is determined by all remaining dims.
    For example::

        data = torch.zeros(5,4,3,2)
        x = Tensor(data, OrderedDict([("i", bint(5)), ("j", bint(4))]))
        assert x.output == reals(3, 2)

    Operators like ``matmul`` and ``.sum()`` operate only on the output shape,
    and will not change the named inputs.

   :param numeric_array data: A PyTorch tensor or NumPy ndarray.
    :param OrderedDict inputs: An optional mapping from input name (str) to
        datatype (:class:`~funsor.domains.Domain` ). Defaults to empty.
    :param dtype: optional output datatype. Defaults to "real".
    :type dtype: int or the string "real".
    """
    def __init__(self, data, inputs=None, dtype="real"):
        assert ops.is_numeric_array(data)
        assert isinstance(inputs, tuple)
        if not get_tracing_state():
            assert len(inputs) <= len(data.shape)
            for (k, d), size in zip(inputs, data.shape):
                assert d.dtype == size
        inputs = OrderedDict(inputs)
        output = Domain(data.shape[len(inputs):], dtype)
        fresh = frozenset(inputs.keys())
        bound = frozenset()
        super(Tensor, self).__init__(inputs, output, fresh, bound)
        self.data = data

    def __repr__(self):
        if self.output != "real":
            return 'Tensor({}, {}, {})'.format(self.data, self.inputs, repr(self.dtype))
        elif self.inputs:
            return 'Tensor({}, {})'.format(self.data, self.inputs)
        else:
            return 'Tensor({})'.format(self.data)

    def __str__(self):
        if self.dtype != "real":
            return 'Tensor({}, {}, {})'.format(self.data, self.inputs, repr(self.dtype))
        elif self.inputs:
            return 'Tensor({}, {})'.format(self.data, self.inputs)
        else:
            return str(self.data)

    def __int__(self):
        return int(self.data)

    def __float__(self):
        return float(self.data)

    def __bool__(self):
        return bool(self.data)

    def item(self):
        return self.data.item()

    def clamp_finite(self):
        finfo = ops.finfo(self.data)
        data = ops.clamp(self.data, finfo.min, finfo.max)
        return Tensor(data, self.inputs, self.dtype)

    @property
    def requires_grad(self):
        # NB: numpy does not have attribute requires_grad
        return getattr(self.data, "requires_grad", None)

    def align(self, names):
        assert isinstance(names, tuple)
        assert all(name in self.inputs for name in names)
        if not names or names == tuple(self.inputs):
            return self

        inputs = OrderedDict((name, self.inputs[name]) for name in names)
        inputs.update(self.inputs)
        old_dims = tuple(self.inputs)
        new_dims = tuple(inputs)
        permutation = tuple(old_dims.index(d) for d in new_dims)
        permutation = permutation + tuple(range(len(permutation), len(permutation) + len(self.output.shape)))
        data = ops.permute(self.data, permutation)
        return Tensor(data, inputs, self.dtype)

    def eager_subs(self, subs):
        assert isinstance(subs, tuple)
        subs = OrderedDict((k, to_funsor(v, self.inputs[k]))
                           for k, v in subs if k in self.inputs)
        if not subs:
            return self

        # Handle renaming to enable cons hashing, and
        # handle slicing to avoid copying data.
        if any(isinstance(v, (Variable, Slice)) for v in subs.values()):
            slices = None
            inputs = OrderedDict()
            for i, (k, d) in enumerate(self.inputs.items()):
                if k in subs:
                    v = subs[k]
                    if isinstance(v, Variable):
                        del subs[k]
                        k = v.name
                    elif isinstance(v, Slice):
                        del subs[k]
                        k = v.name
                        d = v.inputs[v.name]
                        if slices is None:
                            slices = [slice(None)] * len(self.data.shape)
                        slices[i] = v.slice
                inputs[k] = d
            data = self.data[tuple(slices)] if slices else self.data
            result = Tensor(data, inputs, self.dtype)
            return result.eager_subs(tuple(subs.items()))

        # materialize after checking for renaming case
        subs = OrderedDict((k, self.materialize(v)) for k, v in subs.items())

        # Compute result shapes.
        inputs = OrderedDict()
        for k, domain in self.inputs.items():
            if k in subs:
                inputs.update(subs[k].inputs)
            else:
                inputs[k] = domain

        # Construct a dict with each input's positional dim,
        # counting from the right so as to support broadcasting.
        total_size = len(inputs) + len(self.output.shape)  # Assumes only scalar indices.
        new_dims = {}
        for k, domain in inputs.items():
            assert not domain.shape
            new_dims[k] = len(new_dims) - total_size

        # Use advanced indexing to construct a simultaneous substitution.
        index = []
        for k, domain in self.inputs.items():
            if k in subs:
                v = subs.get(k)
                if isinstance(v, Number):
                    index.append(int(v.data))
                else:
                    # Permute and expand v.data to end up at new_dims.
                    assert isinstance(v, Tensor)
                    v = v.align(tuple(k2 for k2 in inputs if k2 in v.inputs))
                    assert isinstance(v, Tensor)
                    v_shape = [1] * total_size
                    for k2, size in zip(v.inputs, v.data.shape):
                        v_shape[new_dims[k2]] = size
                    index.append(v.data.reshape(tuple(v_shape)))
            else:
                # Construct a [:] slice for this preserved input.
                offset_from_right = -1 - new_dims[k]
                index.append(ops.new_arange(self.data, domain.dtype).reshape(
                    (-1,) + (1,) * offset_from_right))

        # Construct a [:] slice for the output.
        for i, size in enumerate(self.output.shape):
            offset_from_right = len(self.output.shape) - i - 1
            index.append(ops.new_arange(self.data, size).reshape(
                (-1,) + (1,) * offset_from_right))

        data = self.data[tuple(index)]
        return Tensor(data, inputs, self.dtype)

    def eager_unary(self, op):
        dtype = find_domain(op, self.output).dtype
        if op in REDUCE_OP_TO_NUMERIC:
            batch_dim = len(self.data.shape) - len(self.output.shape)
            data = self.data.reshape(self.data.shape[:batch_dim] + (-1,))
            data = REDUCE_OP_TO_NUMERIC[op](data, -1)
            return Tensor(data, self.inputs, dtype)
        return Tensor(op(self.data), self.inputs, dtype)

    def eager_reduce(self, op, reduced_vars):
        if op in REDUCE_OP_TO_NUMERIC:
            numeric_op = REDUCE_OP_TO_NUMERIC[op]
            assert isinstance(reduced_vars, frozenset)
            self_vars = frozenset(self.inputs)
            reduced_vars = reduced_vars & self_vars
            if reduced_vars == self_vars and not self.output.shape:
                return Tensor(numeric_op(self.data, None), dtype=self.dtype)

            # Reduce one dim at a time.
            data = self.data
            offset = 0
            for k, domain in self.inputs.items():
                if k in reduced_vars:
                    assert not domain.shape
                    data = numeric_op(data, offset)
                else:
                    offset += 1
            inputs = OrderedDict((k, v) for k, v in self.inputs.items()
                                 if k not in reduced_vars)
            return Tensor(data, inputs, self.dtype)
        return super(Tensor, self).eager_reduce(op, reduced_vars)

    # TODO: support a `key` kwarg to get samples from numpyro distributions
    def unscaled_sample(self, sampled_vars, sample_inputs):
        assert self.output == reals()
        sampled_vars = sampled_vars.intersection(self.inputs)
        if not sampled_vars:
            return self

        # Partition inputs into sample_inputs + batch_inputs + event_inputs.
        sample_inputs = OrderedDict((k, d) for k, d in sample_inputs.items()
                                    if k not in self.inputs)
        sample_shape = tuple(int(d.dtype) for d in sample_inputs.values())
        batch_inputs = OrderedDict((k, d) for k, d in self.inputs.items() if k not in sampled_vars)
        event_inputs = OrderedDict((k, d) for k, d in self.inputs.items() if k in sampled_vars)
        be_inputs = batch_inputs.copy()
        be_inputs.update(event_inputs)
        sb_inputs = sample_inputs.copy()
        sb_inputs.update(batch_inputs)

        # Sample all variables in a single Categorical call.
        logits = align_tensor(be_inputs, self)
        batch_shape = logits.shape[:len(batch_inputs)]
        flat_logits = logits.reshape(batch_shape + (-1,))
        sample_shape = tuple(d.dtype for d in sample_inputs.values())

        backend = get_backend()
        if backend == "torch":
            import torch

            flat_sample = torch.distributions.Categorical(logits=flat_logits).sample(sample_shape)
        elif backend == "jax":
            import jax
            import numpyro

            # TODO: use unscaled_sample key instead of random key here, this won't work under jit
            key = jax.random.PRNGKey(np.random.randint(0, np.iinfo(np.int32).max))
            flat_sample = numpyro.distributions.Categorical(logits=flat_logits).sample(key, sample_shape)
        else:  # default numpy backend
            assert backend == "numpy"
            shape = sample_shape + flat_logits.shape[:-1]
            logit_max = np.amax(flat_logits, -1, keepdims=True)
            probs = np.exp(flat_logits - logit_max)
            probs = probs / np.sum(probs, -1, keepdims=True)
            s = np.cumsum(probs, -1)
            r = np.random.rand(*shape)
            flat_sample = np.sum(s < np.expand_dims(r, -1), axis=-1)

        assert flat_sample.shape == sample_shape + batch_shape
        results = []
        mod_sample = flat_sample
        for name, domain in reversed(list(event_inputs.items())):
            size = domain.dtype
            point = Tensor(mod_sample % size, sb_inputs, size)
            mod_sample = mod_sample / size
            results.append(Delta(name, point))

        # Account for the log normalizer factor.
        # Derivation: Let f be a nonnormalized distribution (a funsor), and
        #   consider operations in linear space (source code is in log space).
        #   Let x0 ~ f/|f| be a monte carlo sample from a normalized f/|f|.
        #                              f(x0) / |f|      # dice numerator
        #   Let g = delta(x=x0) |f| -----------------
        #                           detach(f(x0)/|f|)   # dice denominator
        #                       |detach(f)| f(x0)
        #         = delta(x=x0) -----------------  be a dice approximation of f.
        #                         detach(f(x0))
        #   Then g is an unbiased estimator of f in value and all derivatives.
        #   In the special case f = detach(f), we can simplify to
        #       g = delta(x=x0) |f|.
        if (backend == "torch" and flat_logits.requires_grad) or backend == "jax":
            # Apply a dice factor to preserve differentiability.
            index = [ops.new_arange(self.data, n).reshape((n,) + (1,) * (len(flat_logits.shape) - i - 2))
                     for i, n in enumerate(flat_logits.shape[:-1])]
            index.append(flat_sample)
            log_prob = flat_logits[tuple(index)]
            assert log_prob.shape == flat_sample.shape
            results.append(Tensor(ops.logsumexp(ops.detach(flat_logits), -1) +
                                  (log_prob - ops.detach(log_prob)), sb_inputs))
        else:
            # This is the special case f = detach(f).
            results.append(Tensor(ops.logsumexp(flat_logits, -1), batch_inputs))

        return reduce(ops.add, results)

    def new_arange(self, name, *args, **kwargs):
        """
        Helper to create a named :func:`torch.arange` or :func:`np.arange` funsor.
        In some cases this can be replaced by a symbolic
        :class:`~funsor.terms.Slice` .

        :param str name: A variable name.
        :param int start:
        :param int stop:
        :param int step: Three args following :py:class:`slice` semantics.
        :param int dtype: An optional bounded integer type of this slice.
        :rtype: Tensor
        """
        start = 0
        step = 1
        dtype = None
        if len(args) == 1:
            stop = args[0]
            dtype = kwargs.pop("dtype", stop)
        elif len(args) == 2:
            start, stop = args
            dtype = kwargs.pop("dtype", stop)
        elif len(args) == 3:
            start, stop, step = args
            dtype = kwargs.pop("dtype", stop)
        elif len(args) == 4:
            start, stop, step, dtype = args
        else:
            raise ValueError
        if step <= 0:
            raise ValueError
        stop = min(dtype, max(start, stop))
        data = ops.new_arange(self.data, start, stop, step)
        inputs = OrderedDict([(name, bint(len(data)))])
        return Tensor(data, inputs, dtype=dtype)

    def materialize(self, x):
        """
        Attempt to convert a Funsor to a :class:`~funsor.terms.Number` or
        :class:`Tensor` by substituting :func:`arange` s into its free variables.

        :arg Funsor x: A funsor.
        :rtype: Funsor
        """
        assert isinstance(x, Funsor)
        if isinstance(x, (Number, Tensor)):
            return x
        subs = []
        for name, domain in x.inputs.items():
            if isinstance(domain.dtype, int):
                subs.append((name, self.new_arange(name, domain.dtype)))
        subs = tuple(subs)
        return substitute(x, subs)


@to_funsor.register(np.ndarray)
@to_funsor.register(np.generic)
def tensor_to_funsor(x, output=None, dim_to_name=None):
    if not dim_to_name:
        output = output if output is not None else reals(*x.shape)
        result = Tensor(x, dtype=output.dtype)
        if result.output != output:
            raise ValueError("Invalid shape: expected {}, actual {}"
                             .format(output.shape, result.output.shape))
        return result
    else:
        assert output is not None  # TODO attempt to infer output
        assert all(isinstance(k, int) and k < 0 and isinstance(v, str)
                   for k, v in dim_to_name.items())
        # logic very similar to pyro.ops.packed.pack
        # this should not touch memory, only reshape
        # pack the tensor according to the dim => name mapping in inputs
        packed_inputs = OrderedDict()
        for dim, size in zip(range(len(x.shape) - len(output.shape)), x.shape):
            name = dim_to_name.get(dim + len(output.shape) - len(x.shape), None)
            if name is not None and size > 1:
                packed_inputs[name] = bint(size)
        shape = tuple(d.size for d in packed_inputs.values()) + output.shape
        if x.shape != shape:
            x = x.reshape(shape)
        return Tensor(x, packed_inputs, dtype=output.dtype)


def align_tensor(new_inputs, x, expand=False):
    r"""
    Permute and add dims to a tensor to match desired ``new_inputs``.

    :param OrderedDict new_inputs: A target set of inputs.
    :param funsor.terms.Funsor x: A :class:`Tensor` or
        :class:`~funsor.terms.Number` .
    :param bool expand: If False (default), set result size to 1 for any input
        of ``x`` not in ``new_inputs``; if True expand to ``new_inputs`` size.
    :return: a number or :class:`torch.Tensor` or :class:`np.ndarray` that can be broadcast to other
        tensors with inputs ``new_inputs``.
    :rtype: int or float or torch.Tensor or np.ndarray
    """
    assert isinstance(new_inputs, OrderedDict)
    assert isinstance(x, (Number, Tensor))
    assert all(isinstance(d.dtype, int) for d in x.inputs.values())

    data = x.data
    if isinstance(x, Number):
        return data

    old_inputs = x.inputs
    if old_inputs == new_inputs:
        return data

    # Permute squashed input dims.
    x_keys = tuple(old_inputs)
    data = ops.permute(data, tuple(x_keys.index(k) for k in new_inputs if k in old_inputs) +
                       tuple(range(len(old_inputs), len(data.shape))))

    # Unsquash multivariate input dims by filling in ones.
    data = data.reshape(tuple(old_inputs[k].dtype if k in old_inputs else 1 for k in new_inputs) +
                        x.output.shape)

    # Optionally expand new dims.
    if expand:
        data = ops.expand(data, tuple(d.dtype for d in new_inputs.values()) + x.output.shape)
    return data


def align_tensors(*args, **kwargs):
    r"""
    Permute multiple tensors before applying a broadcasted op.

    This is mainly useful for implementing eager funsor operations.

    :param funsor.terms.Funsor \*args: Multiple :class:`Tensor` s and
        :class:`~funsor.terms.Number` s.
    :param bool expand: Whether to expand input tensors. Defaults to False.
    :return: a pair ``(inputs, tensors)`` where tensors are all
        :class:`torch.Tensor` s or :class:`np.ndarray` s
        that can be broadcast together to a single data
        with given ``inputs``.
    :rtype: tuple
    """
    expand = kwargs.pop('expand', False)
    assert not kwargs
    inputs = OrderedDict()
    for x in args:
        inputs.update(x.inputs)
    tensors = [align_tensor(inputs, x, expand=expand) for x in args]
    return inputs, tensors


@to_data.register(Tensor)
def tensor_to_data(x, name_to_dim=None):
    if not name_to_dim or not x.inputs:
        if x.inputs:
            raise ValueError(f"cannot convert Tensor to data due to lazy inputs: {set(x.inputs)}")
        return x.data
    else:
        assert all(isinstance(k, str) and isinstance(v, int) and v < 0
                   for k, v in name_to_dim.items())
        # logic very similar to pyro.ops.packed.unpack
        # first collapse input domains into single dimensions
        data = x.data.reshape(tuple(d.dtype for d in x.inputs.values()) + x.output.shape)
        # permute packed dimensions to correct order
        unsorted_dims = [name_to_dim[name] for name in x.inputs]
        dims = sorted(unsorted_dims)
        permutation = [unsorted_dims.index(dim) for dim in dims] + \
            list(range(len(dims), len(dims) + len(x.output.shape)))
        data = data.permute(*permutation)
        # expand
        batch_shape = [1] * -min(dims)
        for dim, size in zip(dims, data.shape):
            batch_shape[dim] = size
        return data.reshape(tuple(batch_shape) + x.output.shape)


@eager.register(Binary, Op, Tensor, Number)
def eager_binary_tensor_number(op, lhs, rhs):
    data = op(lhs.data, rhs.data)
    return Tensor(data, lhs.inputs, lhs.dtype)


@eager.register(Binary, Op, Number, Tensor)
def eager_binary_number_tensor(op, lhs, rhs):
    data = op(lhs.data, rhs.data)
    return Tensor(data, rhs.inputs, rhs.dtype)


@eager.register(Binary, Op, Tensor, Tensor)
def eager_binary_tensor_tensor(op, lhs, rhs):
    # Compute inputs and outputs.
    dtype = find_domain(op, lhs.output, rhs.output).dtype
    if lhs.inputs == rhs.inputs:
        inputs = lhs.inputs
        lhs_data, rhs_data = lhs.data, rhs.data
    else:
        inputs, (lhs_data, rhs_data) = align_tensors(lhs, rhs)

    # Reshape to support broadcasting of output shape.
    if inputs:
        lhs_dim = len(lhs.shape)
        rhs_dim = len(rhs.shape)
        if lhs_dim < rhs_dim:
            cut = len(lhs_data.shape) - lhs_dim
            shape = lhs_data.shape
            shape = shape[:cut] + (1,) * (rhs_dim - lhs_dim) + shape[cut:]
            lhs_data = lhs_data.reshape(shape)
        elif rhs_dim < lhs_dim:
            cut = len(rhs_data.shape) - rhs_dim
            shape = rhs_data.shape
            shape = shape[:cut] + (1,) * (lhs_dim - rhs_dim) + shape[cut:]
            rhs_data = rhs_data.reshape(shape)

    data = op(lhs_data, rhs_data)
    return Tensor(data, inputs, dtype)


@eager.register(Binary, MatmulOp, Tensor, Tensor)
def eager_binary_tensor_tensor(op, lhs, rhs):
    # Compute inputs and outputs.
    dtype = find_domain(op, lhs.output, rhs.output).dtype
    if lhs.inputs == rhs.inputs:
        inputs = lhs.inputs
        lhs_data, rhs_data = lhs.data, rhs.data
    else:
        inputs, (lhs_data, rhs_data) = align_tensors(lhs, rhs)
    if len(lhs.shape) == 1:
        lhs_data = ops.unsqueeze(lhs_data, -2)
    if len(rhs.shape) == 1:
        rhs_data = ops.unsqueeze(rhs_data, -1)

    # Reshape to support broadcasting of output shape.
    if inputs:
        lhs_dim = max(2, len(lhs.shape))
        rhs_dim = max(2, len(rhs.shape))
        if lhs_dim < rhs_dim:
            cut = len(lhs_data.shape) - lhs_dim
            shape = lhs_data.shape
            shape = shape[:cut] + (1,) * (rhs_dim - lhs_dim) + shape[cut:]
            lhs_data = lhs_data.reshape(shape)
        elif rhs_dim < lhs_dim:
            cut = len(rhs_data.shape) - rhs_dim
            shape = rhs_data.shape
            shape = shape[:cut] + (1,) * (lhs_dim - rhs_dim) + shape[cut:]
            rhs_data = rhs_data.reshape(shape)

    data = op(lhs_data, rhs_data)
    if len(lhs.shape) == 1:
        data = data.squeeze(-2)
    if len(rhs.shape) == 1:
        data = data.squeeze(-1)
    return Tensor(data, inputs, dtype)


@eager.register(Unary, ReshapeOp, Tensor)
def eager_reshape_tensor(op, arg):
    if arg.shape == op.shape:
        return arg
    batch_shape = arg.data.shape[:len(arg.data.shape) - len(arg.shape)]
    data = arg.data.reshape(batch_shape + op.shape)
    return Tensor(data, arg.inputs, arg.dtype)


@eager.register(Binary, GetitemOp, Tensor, Number)
def eager_getitem_tensor_number(op, lhs, rhs):
    index = [slice(None)] * (len(lhs.inputs) + op.offset)
    index.append(rhs.data)
    index = tuple(index)
    data = lhs.data[index]
    return Tensor(data, lhs.inputs, lhs.dtype)


@eager.register(Binary, GetitemOp, Tensor, Variable)
def eager_getitem_tensor_variable(op, lhs, rhs):
    assert op.offset < len(lhs.output.shape)
    assert rhs.output == bint(lhs.output.shape[op.offset])
    assert rhs.name not in lhs.inputs

    # Convert a positional event dimension to a named batch dimension.
    inputs = lhs.inputs.copy()
    inputs[rhs.name] = rhs.output
    data = lhs.data
    target_dim = len(lhs.inputs)
    source_dim = target_dim + op.offset
    if target_dim != source_dim:
        perm = list(range(len(data.shape)))
        del perm[source_dim]
        perm.insert(target_dim, source_dim)
        data = ops.permute(data, perm)
    return Tensor(data, inputs, lhs.dtype)


@eager.register(Binary, GetitemOp, Tensor, Tensor)
def eager_getitem_tensor_tensor(op, lhs, rhs):
    assert op.offset < len(lhs.output.shape)
    assert rhs.output == bint(lhs.output.shape[op.offset])

    # Compute inputs and outputs.
    if lhs.inputs == rhs.inputs:
        inputs, lhs_data, rhs_data = lhs.inputs, lhs.data, rhs.data
    else:
        inputs, (lhs_data, rhs_data) = align_tensors(lhs, rhs)
    if len(lhs.output.shape) > 1:
        rhs_data = rhs_data.reshape(rhs_data.shape + (1,) * (len(lhs.output.shape) - 1))

    # Perform advanced indexing.
    lhs_data_dim = len(lhs_data.shape)
    target_dim = lhs_data_dim - len(lhs.output.shape) + op.offset
    index = [None] * lhs_data_dim
    for i in range(target_dim):
        index[i] = ops.new_arange(lhs_data, lhs_data.shape[i]).reshape((-1,) + (1,) * (lhs_data_dim - i - 2))
    index[target_dim] = rhs_data
    for i in range(1 + target_dim, lhs_data_dim):
        index[i] = ops.new_arange(lhs_data, lhs_data.shape[i]).reshape((-1,) + (1,) * (lhs_data_dim - i - 1))
    data = lhs_data[tuple(index)]
    return Tensor(data, inputs, lhs.dtype)


@eager.register(Lambda, Variable, Tensor)
def eager_lambda(var, expr):
    inputs = expr.inputs.copy()
    if var.name in inputs:
        inputs.pop(var.name)
        inputs[var.name] = var.output
        data = align_tensor(inputs, expr)
        inputs.pop(var.name)
    else:
        data = expr.data
        shape = data.shape
        dim = len(shape) - len(expr.output.shape)
        data = data.reshape(shape[:dim] + (1,) + shape[dim:])
        data = ops.expand(data, shape[:dim] + (var.dtype,) + shape[dim:])
    return Tensor(data, inputs, expr.dtype)


@dispatch(str, Variadic[Tensor])
def eager_stack_homogeneous(name, *parts):
    assert parts
    output = parts[0].output
    part_inputs = OrderedDict()
    for part in parts:
        assert part.output == output
        assert name not in part.inputs
        part_inputs.update(part.inputs)

    shape = tuple(d.size for d in part_inputs.values()) + output.shape
    data = ops.stack(0, *[ops.expand(align_tensor(part_inputs, part), shape)
                          for part in parts])
    inputs = OrderedDict([(name, bint(len(parts)))])
    inputs.update(part_inputs)
    return Tensor(data, inputs, dtype=output.dtype)


@dispatch(str, str, Variadic[Tensor])
def eager_cat_homogeneous(name, part_name, *parts):
    assert parts
    output = parts[0].output
    inputs = OrderedDict([(part_name, None)])
    for part in parts:
        assert part.output == output
        assert part_name in part.inputs
        inputs.update(part.inputs)

    tensors = []
    for part in parts:
        inputs[part_name] = part.inputs[part_name]
        shape = tuple(d.size for d in inputs.values()) + output.shape
        tensors.append(ops.expand(align_tensor(inputs, part), shape))
    del inputs[part_name]

    dim = 0
    tensor = ops.cat(dim, *tensors)
    inputs = OrderedDict([(name, bint(tensor.shape[dim]))] + list(inputs.items()))
    return Tensor(tensor, inputs, dtype=output.dtype)


class LazyTuple(tuple):
    def __call__(self, *args, **kwargs):
        return LazyTuple(x(*args, **kwargs) for x in self)


class Function(Funsor):
    r"""
    Funsor wrapped by a native PyTorch or NumPy function.

    Functions are assumed to support broadcasting and can be eagerly evaluated
    on funsors with free variables of int type (i.e. batch dimensions).

    :class:`Function` s are usually created via the :func:`function` decorator.

    :param callable fn: A native PyTorch or NumPy function to wrap.
    :param funsor.domains.Domain output: An output domain.
    :param Funsor args: Funsor arguments.
    """
    def __init__(self, fn, output, args):
        assert callable(fn)
        assert not isinstance(fn, Function)
        assert isinstance(args, tuple)
        inputs = OrderedDict()
        for arg in args:
            assert isinstance(arg, Funsor)
            inputs.update(arg.inputs)
        super(Function, self).__init__(inputs, output)
        self.fn = fn
        self.args = args

    def __repr__(self):
        return '{}({}, {}, {})'.format(type(self).__name__, _nameof(self.fn),
                                       repr(self.output), repr(self.args))

    def __str__(self):
        return '{}({}, {}, {})'.format(type(self).__name__, _nameof(self.fn),
                                       str(self.output), str(self.args))


@quote.register(Function)
def _(arg, indent, out):
    out.append((indent, f"Function({_nameof(arg.fn)},"))
    quote.inplace(arg.output, indent + 1, out)
    i, line = out[-1]
    out[-1] = i, line + ","
    quote.inplace(arg.args, indent + 1, out)
    i, line = out[-1]
    out[-1] = i, line + ")"


@eager.register(Function, object, Domain, tuple)
def eager_function(fn, output, args):
    if not all(isinstance(arg, (Number, Tensor)) for arg in args):
        return None  # defer to default implementation
    inputs, tensors = align_tensors(*args)
    data = fn(*tensors)
    result = Tensor(data, inputs, dtype=output.dtype)
    assert result.output == output
    return result


def _select(fn, i, *args):
    result = fn(*args)
    assert isinstance(result, tuple)
    return result[i]


def _nested_function(fn, args, output):
    if isinstance(output, Domain):
        return Function(fn, output, args)
    elif isinstance(output, tuple):
        result = []
        for i, output_i in enumerate(output):
            fn_i = functools.partial(_select, fn, i)
            fn_i.__name__ = f"{_nameof(fn)}_{i}"
            result.append(_nested_function(fn_i, args, output_i))
        return LazyTuple(result)
    raise ValueError("Invalid output: {}".format(output))


class _Memoized(object):
    def __init__(self, fn):
        self.fn = fn
        self._cache = None

    def __call__(self, *args):
        if self._cache is not None:
            old_args, old_result = self._cache
            if all(x is y for x, y in zip(args, old_args)):
                return old_result
        result = self.fn(*args)
        self._cache = args, result
        return result

    @property
    def __name__(self):
        return _nameof(self.fn)


def _function(inputs, output, fn):
    if is_nn_module(fn):
        names = getargspec(fn.forward)[0][1:]
    else:
        names = getargspec(fn)[0]
    args = tuple(Variable(name, domain) for (name, domain) in zip(names, inputs))
    assert len(args) == len(inputs)
    if not isinstance(output, Domain):
        assert isinstance(output, tuple)
        # Memoize multiple-output functions so that invocations can be shared among
        # all outputs. This is not foolproof, but does work in simple situations.
        fn = _Memoized(fn)
    return _nested_function(fn, args, output)


def function(*signature):
    r"""
    Decorator to wrap a PyTorch/NumPy function.

    Example::

        @funsor.torch.function(reals(3,4), reals(4,5), reals(3,5))
        def matmul(x, y):
            return torch.matmul(x, y)

        @funsor.torch.function(reals(10), reals(10, 10), reals())
        def mvn_log_prob(loc, scale_tril, x):
            d = torch.distributions.MultivariateNormal(loc, scale_tril)
            return d.log_prob(x)

    To support functions that output nested tuples of tensors, specify a nested
    tuple of output types, for example::

        @funsor.torch.function(reals(8), (reals(), bint(8)))
        def max_and_argmax(x):
            return torch.max(x, dim=-1)

    :param \*signature: A sequence if input domains followed by a final output
        domain or nested tuple of output domains.
    """
    assert signature
    inputs, output = signature[:-1], signature[-1]
    assert all(isinstance(d, Domain) for d in inputs)
    assert isinstance(output, (Domain, tuple))
    return functools.partial(_function, inputs, output)


class Einsum(Funsor):
    """
    Wrapper around :func:`torch.einsum` or :func:`np.einsum` to operate on real-valued Funsors.

    Note this operates only on the ``output`` tensor. To perform sum-product
    contractions on named dimensions, instead use ``+`` and
    :class:`~funsor.terms.Reduce`.

    :param str equation: An :func:`torch.einsum` or :func:`np.einsum` equation.
    :param tuple operands: A tuple of input funsors.
    """
    def __init__(self, equation, operands):
        assert isinstance(equation, str)
        assert isinstance(operands, tuple)
        assert all(isinstance(x, Funsor) for x in operands)
        ein_inputs, ein_output = equation.split('->')
        ein_inputs = ein_inputs.split(',')
        size_dict = {}
        inputs = OrderedDict()
        assert len(ein_inputs) == len(operands)
        for ein_input, x in zip(ein_inputs, operands):
            assert x.dtype == 'real'
            inputs.update(x.inputs)
            assert len(ein_input) == len(x.output.shape)
            for name, size in zip(ein_input, x.output.shape):
                other_size = size_dict.setdefault(name, size)
                if other_size != size:
                    raise ValueError("Size mismatch at {}: {} vs {}"
                                     .format(name, size, other_size))
        output = reals(*(size_dict[d] for d in ein_output))
        super(Einsum, self).__init__(inputs, output)
        self.equation = equation
        self.operands = operands

    def __repr__(self):
        return 'Einsum({}, {})'.format(repr(self.equation), repr(self.operands))

    def __str__(self):
        return 'Einsum({}, {})'.format(repr(self.equation), str(self.operands))


@eager.register(Einsum, str, tuple)
def eager_einsum(equation, operands):
    if all(isinstance(x, Tensor) for x in operands):
        # Make new symbols for inputs of operands.
        inputs = OrderedDict()
        for x in operands:
            inputs.update(x.inputs)
        symbols = set(equation)
        get_symbol = iter(map(opt_einsum.get_symbol, itertools.count()))
        new_symbols = {}
        for k in inputs:
            symbol = next(get_symbol)
            while symbol in symbols:
                symbol = next(get_symbol)
            symbols.add(symbol)
            new_symbols[k] = symbol

        # Manually broadcast using einsum symbols.
        assert '.' not in equation
        ins, out = equation.split('->')
        ins = ins.split(',')
        ins = [''.join(new_symbols[k] for k in x.inputs) + x_out
               for x, x_out in zip(operands, ins)]
        out = ''.join(new_symbols[k] for k in inputs) + out
        equation = ','.join(ins) + '->' + out

        data = ops.einsum(equation, *[x.data for x in operands])
        return Tensor(data, inputs)

    return None  # defer to default implementation


def tensordot(x, y, dims):
    """
    Wrapper around :func:`torch.tensordot` or :func:`np.tensordot`
    to operate on real-valued Funsors.

    Note this operates only on the ``output`` tensor. To perform sum-product
    contractions on named dimensions, instead use ``+`` and
    :class:`~funsor.terms.Reduce`.

    Arguments should satisfy::

        len(x.shape) >= dims
        len(y.shape) >= dims
        dims == 0 or x.shape[-dims:] == y.shape[:dims]

    :param Funsor x: A left hand argument.
    :param Funsor y: A y hand argument.
    :param int dims: The number of dimension of overlap of output shape.
    :rtype: Funsor
    """
    assert dims >= 0
    assert len(x.shape) >= dims
    assert len(y.shape) >= dims
    assert dims == 0 or x.shape[-dims:] == y.shape[:dims]
    x_start, x_end = 0, len(x.output.shape)
    y_start = x_end - dims
    y_end = y_start + len(y.output.shape)
    symbols = 'abcdefghijklmnopqrstuvwxyz'
    equation = '{},{}->{}'.format(symbols[x_start:x_end],
                                  symbols[y_start:y_end],
                                  symbols[x_start:y_start] + symbols[x_end:y_end])
    return Einsum(equation, (x, y))


def stack(parts, dim=0):
    """
    Wrapper around :func:`torch.stack` or :func:`np.stack` to operate on real-valued Funsors.

    Note this operates only on the ``output`` tensor. To stack funsors in a
    new named dim, instead use :class:`~funsor.terms.Stack`.

    :param tuple parts: A tuple of funsors.
    :param int dim: A torch dim along which to stack.
    :rtype: Funsor
    """
    assert isinstance(dim, int)
    assert isinstance(parts, tuple)
    assert len(set(x.output for x in parts)) == 1
    shape = parts[0].output.shape
    if dim >= 0:
        dim = dim - len(shape) - 1
    assert dim < 0
    split = dim + len(shape) + 1
    shape = shape[:split] + (len(parts),) + shape[split:]
    output = Domain(shape, parts[0].dtype)
    fn = functools.partial(ops.stack, dim)
    return Function(fn, output, parts)


REDUCE_OP_TO_NUMERIC = {
    ops.add: ops.sum,
    ops.mul: ops.prod,
    ops.and_: ops.all,
    ops.or_: ops.any,
    ops.logaddexp: ops.logsumexp,
    ops.sample: ops.logsumexp,
    ops.min: ops.amin,
    ops.max: ops.amax,
}


__all__ = [
    'Einsum',
    'Function',
    'REDUCE_OP_TO_NUMERIC',
    'Tensor',
    'align_tensor',
    'align_tensors',
    'function',
    'ignore_jit_warnings',
    'stack',
    'tensordot',
]
