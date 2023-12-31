# Copyright Contributors to the Pyro project.
# SPDX-License-Identifier: Apache-2.0

import functools
import itertools
from collections import OrderedDict, defaultdict
from functools import reduce
from typing import Tuple, Union

import opt_einsum
from multipledispatch.variadic import Variadic

import funsor.ops as ops
from funsor.affine import affine_inputs
from funsor.delta import Delta
from funsor.domains import find_domain
from funsor.gaussian import Gaussian
from funsor.interpreter import interpretation, recursion_reinterpret
from funsor.ops import DISTRIBUTIVE_OPS, AssociativeOp, NullOp, nullop
from funsor.tensor import Tensor
from funsor.terms import (
    Align,
    Binary,
    Funsor,
    Lebesgue,
    Number,
    Reduce,
    Subs,
    Unary,
    Variable,
    eager,
    normalize,
    reflect,
    to_funsor
)
from funsor.util import broadcast_shape, get_backend, quote


class Contraction(Funsor):
    """
    Declarative representation of a finitary sum-product operation.

    After normalization via the :func:`~funsor.terms.normalize` interpretation
    contractions will canonically order their terms by type::

        Delta, Number, Tensor, Gaussian
    """
    def __init__(self, red_op, bin_op, reduced_vars, terms):
        terms = (terms,) if isinstance(terms, Funsor) else terms
        assert isinstance(red_op, AssociativeOp)
        assert isinstance(bin_op, AssociativeOp)
        assert all(isinstance(v, Funsor) for v in terms)
        assert isinstance(reduced_vars, frozenset)
        assert all(isinstance(v, str) for v in reduced_vars)
        assert isinstance(terms, tuple) and len(terms) > 0

        assert not (isinstance(red_op, NullOp) and isinstance(bin_op, NullOp))
        if isinstance(red_op, NullOp):
            assert not reduced_vars
        elif isinstance(bin_op, NullOp):
            assert len(terms) == 1
        else:
            assert reduced_vars and len(terms) > 1
            assert (red_op, bin_op) in DISTRIBUTIVE_OPS

        inputs = OrderedDict()
        for v in terms:
            inputs.update((k, d) for k, d in v.inputs.items() if k not in reduced_vars)

        if bin_op is nullop:
            output = terms[0].output
        else:
            output = reduce(lambda lhs, rhs: find_domain(bin_op, lhs, rhs),
                            [v.output for v in reversed(terms)])
        fresh = frozenset()
        bound = reduced_vars
        super(Contraction, self).__init__(inputs, output, fresh, bound)
        self.red_op = red_op
        self.bin_op = bin_op
        self.terms = terms
        self.reduced_vars = reduced_vars

    def unscaled_sample(self, sampled_vars, sample_inputs, rng_key=None):
        sampled_vars = sampled_vars.intersection(self.inputs)
        if not sampled_vars:
            return self

        if self.red_op in (ops.logaddexp, nullop):
            if self.bin_op in (ops.nullop, ops.logaddexp):
                if rng_key is not None:
                    import jax
                    rng_keys = jax.random.split(rng_key, len(self.terms))
                else:
                    rng_keys = [None] * len(self.terms)

                # Design choice: we sample over logaddexp reductions, but leave logaddexp
                # binary choices symbolic.
                terms = [
                    term.unscaled_sample(sampled_vars.intersection(term.inputs), sample_inputs)
                    for term, rng_key in zip(self.terms, rng_keys)]
                return Contraction(self.red_op, self.bin_op, self.reduced_vars, *terms)

            if self.bin_op is ops.add:
                if rng_key is not None:
                    import jax
                    rng_keys = jax.random.split(rng_key)
                else:
                    rng_keys = [None] * 2

                # Sample variables greedily in order of the terms in which they appear.
                for term in self.terms:
                    greedy_vars = sampled_vars.intersection(term.inputs)
                    if greedy_vars:
                        break
                greedy_terms, terms = [], []
                for term in self.terms:
                    (terms if greedy_vars.isdisjoint(term.inputs) else greedy_terms).append(term)
                if len(greedy_terms) == 1:
                    term = greedy_terms[0]
                    terms.append(term.unscaled_sample(greedy_vars, sample_inputs, rng_keys[0]))
                    result = Contraction(self.red_op, self.bin_op, self.reduced_vars, *terms)
                elif (len(greedy_terms) == 2 and
                        isinstance(greedy_terms[0], Tensor) and
                        isinstance(greedy_terms[1], Gaussian)):
                    discrete, gaussian = greedy_terms
                    term = discrete + gaussian.log_normalizer
                    terms.append(gaussian)
                    terms.append(-gaussian.log_normalizer)
                    terms.append(term.unscaled_sample(greedy_vars, sample_inputs, rng_keys[0]))
                    result = Contraction(self.red_op, self.bin_op, self.reduced_vars, *terms)
                else:
                    raise NotImplementedError('Unhandled case: {}'.format(
                        ', '.join(str(type(t)) for t in greedy_terms)))
                return result.unscaled_sample(sampled_vars - greedy_vars, sample_inputs, rng_keys[1])

        raise TypeError("Cannot sample through ops ({}, {})".format(self.red_op, self.bin_op))

    def align(self, names):
        assert isinstance(names, tuple)
        assert all(name in self.inputs for name in names)
        new_terms = tuple(t.align(tuple(n for n in names if n in t.inputs)) for t in self.terms)
        result = Contraction(self.red_op, self.bin_op, self.reduced_vars, *new_terms)
        if not names == tuple(result.inputs):
            return Align(result, names)  # raise NotImplementedError("TODO align all terms")
        return result

    def _alpha_convert(self, alpha_subs):
        reduced_vars = frozenset(alpha_subs.get(k, k) for k in self.reduced_vars)
        bound_types = {}
        for term in self.terms:
            bound_types.update({k: term.inputs[k] for k in self.bound.intersection(term.inputs)})
        alpha_subs = {k: to_funsor(v, bound_types[k]) for k, v in alpha_subs.items()}
        red_op, bin_op, _, terms = super()._alpha_convert(alpha_subs)
        return red_op, bin_op, reduced_vars, terms


GaussianMixture = Contraction[Union[ops.LogAddExpOp, NullOp], ops.AddOp, frozenset,
                              Tuple[Union[Tensor, Number], Gaussian]]


@quote.register(Contraction)
def _(arg, indent, out):
    line = "{}({}, {},".format(
        type(arg).__name__, repr(arg.red_op), repr(arg.bin_op))
    out.append((indent, line))
    quote.inplace(arg.reduced_vars, indent + 1, out)
    i, line = out[-1]
    out[-1] = i, line + ","
    quote.inplace(arg.terms, indent + 1, out)
    i, line = out[-1]
    out[-1] = i, line + ")"


@recursion_reinterpret.register(Contraction)
def recursion_reinterpret_contraction(x):
    return type(x)(*map(recursion_reinterpret, (x.red_op, x.bin_op, x.reduced_vars) + x.terms))


@eager.register(Contraction, AssociativeOp, AssociativeOp, frozenset, Variadic[Funsor])
def eager_contraction_generic_to_tuple(red_op, bin_op, reduced_vars, *terms):
    return eager(Contraction, red_op, bin_op, reduced_vars, terms)


@eager.register(Contraction, AssociativeOp, AssociativeOp, frozenset, tuple)
def eager_contraction_generic_recursive(red_op, bin_op, reduced_vars, terms):
    # push down leaf reductions
    terms, reduced_vars, leaf_reduced = list(terms), frozenset(reduced_vars), False
    for i, v in enumerate(terms):
        unique_vars = reduced_vars.intersection(v.inputs) - \
            frozenset().union(*(reduced_vars.intersection(vv.inputs) for vv in terms if vv is not v))
        if unique_vars:
            result = v.reduce(red_op, unique_vars)
            if result is not normalize(Contraction, red_op, nullop, unique_vars, (v,)):
                terms[i] = result
                reduced_vars -= unique_vars
                leaf_reduced = True

    if leaf_reduced:
        return Contraction(red_op, bin_op, reduced_vars, *terms)

    # exploit associativity to recursively evaluate this contraction
    # a bit expensive, but handles interpreter-imposed directionality constraints
    terms = tuple(terms)
    for i, lhs in enumerate(terms[0:-1]):
        for j_, rhs in enumerate(terms[i+1:]):
            j = i + j_ + 1
            unique_vars = reduced_vars.intersection(lhs.inputs, rhs.inputs) - \
                frozenset().union(*(reduced_vars.intersection(vv.inputs)
                                    for vv in terms[:i] + terms[i+1:j] + terms[j+1:]))
            result = Contraction(red_op, bin_op, unique_vars, lhs, rhs)
            if result is not normalize(Contraction, red_op, bin_op, unique_vars, (lhs, rhs)):  # did we make progress?
                # pick the first evaluable pair
                reduced_vars -= unique_vars
                new_terms = terms[:i] + (result,) + terms[i+1:j] + terms[j+1:]
                return Contraction(red_op, bin_op, reduced_vars, *new_terms)

    return None


@eager.register(Contraction, AssociativeOp, AssociativeOp, frozenset, Funsor)
def eager_contraction_to_reduce(red_op, bin_op, reduced_vars, term):
    args = red_op, term, reduced_vars
    return eager.dispatch(Reduce, *args)(*args)


@eager.register(Contraction, AssociativeOp, AssociativeOp, frozenset, Funsor, Funsor)
def eager_contraction_to_binary(red_op, bin_op, reduced_vars, lhs, rhs):

    if reduced_vars - (reduced_vars.intersection(lhs.inputs, rhs.inputs)):
        args = red_op, bin_op, reduced_vars, (lhs, rhs)
        result = eager.dispatch(Contraction, *args)(*args)
        if result is not None:
            return result

    args = bin_op, lhs, rhs
    result = eager.dispatch(Binary, *args)(*args)
    if result is not None and reduced_vars:
        args = red_op, result, reduced_vars
        result = eager.dispatch(Reduce, *args)(*args)
    return result


@eager.register(Contraction, ops.AddOp, ops.MulOp, frozenset, Tensor, Tensor)
def eager_contraction_tensor(red_op, bin_op, reduced_vars, *terms):
    if not all(term.dtype == "real" for term in terms):
        raise NotImplementedError('TODO')
    backend = BACKEND_TO_EINSUM_BACKEND[get_backend()]
    return _eager_contract_tensors(reduced_vars, terms, backend=backend)


@eager.register(Contraction, ops.LogAddExpOp, ops.AddOp, frozenset, Tensor, Tensor)
def eager_contraction_tensor(red_op, bin_op, reduced_vars, *terms):
    if not all(term.dtype == "real" for term in terms):
        raise NotImplementedError('TODO')
    backend = BACKEND_TO_LOGSUMEXP_BACKEND[get_backend()]
    return _eager_contract_tensors(reduced_vars, terms, backend=backend)


# TODO Consider using this for more than binary contractions.
def _eager_contract_tensors(reduced_vars, terms, backend):
    iter_symbols = map(opt_einsum.get_symbol, itertools.count())
    symbols = defaultdict(functools.partial(next, iter_symbols))

    inputs = OrderedDict()
    einsum_inputs = []
    operands = []
    for term in terms:
        inputs.update(term.inputs)
        einsum_inputs.append("".join(symbols[k] for k in term.inputs) +
                             "".join(symbols[i - len(term.shape)]
                                     for i, size in enumerate(term.shape)
                                     if size != 1))

        # Squeeze absent event dims to be compatible with einsum.
        data = term.data
        batch_shape = data.shape[:len(data.shape) - len(term.shape)]
        event_shape = tuple(size for size in term.shape if size != 1)
        data = data.reshape(batch_shape + event_shape)
        operands.append(data)

    for k in reduced_vars:
        del inputs[k]
    batch_shape = tuple(v.size for v in inputs.values())
    event_shape = broadcast_shape(*(term.shape for term in terms))
    einsum_output = ("".join(symbols[k] for k in inputs) +
                     "".join(symbols[dim]
                             for dim in range(-len(event_shape), 0)
                             if dim in symbols))
    equation = ",".join(einsum_inputs) + "->" + einsum_output
    data = opt_einsum.contract(equation, *operands, backend=backend)
    data = data.reshape(batch_shape + event_shape)
    return Tensor(data, inputs)


# TODO(https://github.com/pyro-ppl/funsor/issues/238) Use a port of
# Pyro's gaussian_tensordot() here. Until then we must eagerly add the
# possibly-rank-deficient terms before reducing to avoid Cholesky errors.
@eager.register(Contraction, ops.LogAddExpOp, ops.AddOp, frozenset,
                GaussianMixture, GaussianMixture)
def eager_contraction_gaussian(red_op, bin_op, reduced_vars, x, y):
    return (x + y).reduce(red_op, reduced_vars)


@affine_inputs.register(Contraction)
def _(fn):
    with interpretation(reflect):
        flat = reduce(fn.bin_op, fn.terms).reduce(fn.red_op, fn.reduced_vars)
    return affine_inputs(flat)


##########################################
# Normalizing Contractions
##########################################

ORDERING = {Delta: 1, Number: 2, Tensor: 3, Gaussian: 4}
GROUND_TERMS = tuple(ORDERING)


@normalize.register(Contraction, AssociativeOp, ops.AddOp, frozenset, GROUND_TERMS, GROUND_TERMS)
def normalize_contraction_commutative_canonical_order(red_op, bin_op, reduced_vars, *terms):
    # when bin_op is commutative, put terms into a canonical order for pattern matching
    new_terms = tuple(
        v for i, v in sorted(enumerate(terms),
                             key=lambda t: (ORDERING.get(type(t[1]).__origin__, -1), t[0]))
    )
    if any(v is not vv for v, vv in zip(terms, new_terms)):
        return Contraction(red_op, bin_op, reduced_vars, *new_terms)
    return normalize(Contraction, red_op, bin_op, reduced_vars, new_terms)


@normalize.register(Contraction, AssociativeOp, ops.AddOp, frozenset, GaussianMixture, GROUND_TERMS)
def normalize_contraction_commute_joint(red_op, bin_op, reduced_vars, mixture, other):
    return Contraction(mixture.red_op if red_op is nullop else red_op, bin_op,
                       reduced_vars | mixture.reduced_vars, *(mixture.terms + (other,)))


@normalize.register(Contraction, AssociativeOp, ops.AddOp, frozenset, GROUND_TERMS, GaussianMixture)
def normalize_contraction_commute_joint(red_op, bin_op, reduced_vars, other, mixture):
    return Contraction(mixture.red_op if red_op is nullop else red_op, bin_op,
                       reduced_vars | mixture.reduced_vars, *(mixture.terms + (other,)))


@normalize.register(Contraction, AssociativeOp, AssociativeOp, frozenset, Variadic[Funsor])
def normalize_contraction_generic_args(red_op, bin_op, reduced_vars, *terms):
    return normalize(Contraction, red_op, bin_op, reduced_vars, tuple(terms))


@normalize.register(Contraction, NullOp, NullOp, frozenset, Funsor)
def normalize_trivial(red_op, bin_op, reduced_vars, term):
    assert not reduced_vars
    return term


@normalize.register(Contraction, AssociativeOp, AssociativeOp, frozenset, tuple)
def normalize_contraction_generic_tuple(red_op, bin_op, reduced_vars, terms):

    if not reduced_vars and red_op is not nullop:
        return Contraction(nullop, bin_op, reduced_vars, *terms)

    if len(terms) == 1 and bin_op is not nullop:
        return Contraction(red_op, nullop, reduced_vars, *terms)

    if red_op is nullop and bin_op is nullop:
        return terms[0]

    if red_op is bin_op:
        new_terms = tuple(v.reduce(red_op, reduced_vars) for v in terms)
        return Contraction(red_op, bin_op, frozenset(), *new_terms)

    if bin_op in ops.UNITS and any(isinstance(t, Number) and t.data == ops.UNITS[bin_op] for t in terms):
        new_terms = tuple(t for t in terms if not (isinstance(t, Number) and t.data == ops.UNITS[bin_op]))
        if not new_terms:  # everything was a unit
            new_terms = (terms[0],)
        return Contraction(red_op, bin_op, reduced_vars, *new_terms)

    if any(isinstance(t, Lebesgue) for t in terms):
        dx_terms = set(t for t in terms if isinstance(t, Lebesgue) and t.name not in reduced_vars)
        dx_terms = tuple(sorted(dx_terms, key=lambda t: t.name))
        new_terms = dx_terms + tuple(t for t in terms if not isinstance(t, Lebesgue))
        if new_terms != terms:
            return Contraction(red_op, bin_op, reduced_vars, *new_terms)

    for i, v in enumerate(terms):

        if not isinstance(v, Contraction):
            continue

        # fuse operations without distributing
        if (v.red_op is nullop and bin_op is v.bin_op) or \
                (bin_op is nullop and v.red_op in (red_op, nullop)):
            red_op = v.red_op if red_op is nullop else red_op
            bin_op = v.bin_op if bin_op is nullop else bin_op
            new_terms = terms[:i] + v.terms + terms[i+1:]
            return Contraction(red_op, bin_op, reduced_vars | v.reduced_vars, *new_terms)

    # nothing more to do, reflect
    return None


#########################################
# Creating Contractions from other terms
#########################################

@normalize.register(Binary, AssociativeOp, Funsor, Funsor)
def binary_to_contract(op, lhs, rhs):
    return Contraction(nullop, op, frozenset(), lhs, rhs)


@normalize.register(Reduce, AssociativeOp, Funsor, frozenset)
def reduce_funsor(op, arg, reduced_vars):
    return Contraction(op, nullop, reduced_vars, arg)


@normalize.register(Unary, ops.NegOp, (Variable, Contraction[ops.AssociativeOp, ops.MulOp, frozenset, tuple]))
def unary_neg_variable(op, arg):
    return arg * -1


#######################################################################
# Distributing Unary transformations (Subs, log, exp, neg, reciprocal)
#######################################################################

@normalize.register(Subs, Funsor, tuple)
def do_fresh_subs(arg, subs):
    if not subs:
        return arg
    if all(name in arg.fresh for name, sub in subs):
        return arg.eager_subs(subs)
    return None


@normalize.register(Subs, Contraction, tuple)
def distribute_subs_contraction(arg, subs):
    new_terms = tuple(Subs(v, tuple((name, sub) for name, sub in subs if name in v.inputs))
                      if any(name in v.inputs for name, sub in subs)
                      else v
                      for v in arg.terms)
    return Contraction(arg.red_op, arg.bin_op, arg.reduced_vars, *new_terms)


@normalize.register(Subs, Subs, tuple)
def normalize_fuse_subs(arg, subs):
    # a(b)(c) -> a(b(c), c)
    arg_subs = tuple(arg.subs.items()) if isinstance(arg.subs, OrderedDict) else arg.subs
    new_subs = subs + tuple((k, Subs(v, subs)) for k, v in arg_subs)
    return Subs(arg.arg, new_subs)


@normalize.register(Binary, ops.SubOp, Funsor, Funsor)
def binary_subtract(op, lhs, rhs):
    return lhs + -rhs


@normalize.register(Binary, ops.DivOp, Funsor, Funsor)
def binary_divide(op, lhs, rhs):
    return lhs * Unary(ops.reciprocal, rhs)


@normalize.register(Unary, ops.ExpOp, Unary[ops.LogOp, Funsor])
@normalize.register(Unary, ops.LogOp, Unary[ops.ExpOp, Funsor])
@normalize.register(Unary, ops.NegOp, Unary[ops.NegOp, Funsor])
@normalize.register(Unary, ops.ReciprocalOp, Unary[ops.ReciprocalOp, Funsor])
def unary_log_exp(op, arg):
    return arg.arg


@normalize.register(Unary, ops.ReciprocalOp, Contraction[NullOp, ops.MulOp, frozenset, tuple])
@normalize.register(Unary, ops.NegOp, Contraction[NullOp, ops.AddOp, frozenset, tuple])
def unary_contract(op, arg):
    return Contraction(arg.red_op, arg.bin_op, arg.reduced_vars, *(op(t) for t in arg.terms))


BACKEND_TO_EINSUM_BACKEND = {
    "numpy": "numpy",
    "torch": "torch",
    "jax": "jax.numpy",
}
# NB: numpy_log, numpy_map is backend-agnostic so they also work for torch backend;
# however, we might need to profile to make a switch
BACKEND_TO_LOGSUMEXP_BACKEND = {
    "numpy": "funsor.einsum.numpy_log",
    "torch": "pyro.ops.einsum.torch_log",
    "jax": "funsor.einsum.numpy_log",
}
BACKEND_TO_MAP_BACKEND = {
    "numpy": "funsor.einsum.numpy_map",
    "torch": "pyro.ops.einsum.torch_map",
    "jax": "funsor.einsum.numpy_map",
}
