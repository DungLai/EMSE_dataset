from __future__ import absolute_import, division, print_function

import math
from collections import OrderedDict

import pyro.distributions as dist
import torch
from six import add_metaclass

from pyro.distributions.util import broadcast_shape

import funsor.delta
import funsor.ops as ops
from funsor.affine import Affine
from funsor.domains import bint, reals
from funsor.gaussian import Gaussian
from funsor.interpreter import interpretation
from funsor.terms import Funsor, FunsorMeta, Number, Subs, Variable, eager, lazy, to_funsor
from funsor.torch import Tensor, align_tensors, materialize


def numbers_to_tensors(*args):
    """
    Convert :class:`~funsor.terms.Number`s to :class:`funsor.torch.Tensor`s,
    using any provided tensor as a prototype, if available.
    """
    if any(isinstance(x, Number) for x in args):
        new_tensor = torch.tensor
        for x in args:
            if isinstance(x, Tensor):
                new_tensor = x.data.new_tensor
                break
        args = tuple(Tensor(new_tensor(x.data), dtype=x.dtype) if isinstance(x, Number) else x
                     for x in args)
    return args


class DistributionMeta(FunsorMeta):
    """
    Wrapper to fill in default values and convert Numbers to Tensors.
    """
    def __call__(cls, *args, **kwargs):
        kwargs.update(zip(cls._ast_fields, args))
        args = cls._fill_defaults(**kwargs)
        args = numbers_to_tensors(*args)

        # If value was explicitly specified, evaluate under current interpretation.
        if 'value' in kwargs:
            return super(DistributionMeta, cls).__call__(*args)

        # Otherwise lazily construct a distribution instance.
        # This makes it cheaper to construct observations in minipyro.
        with interpretation(lazy):
            return super(DistributionMeta, cls).__call__(*args)


@add_metaclass(DistributionMeta)
class Distribution(Funsor):
    """
    Funsor backed by a PyTorch distribution object.
    """
    dist_class = "defined by derived classes"

    def __init__(self, *args):
        params = tuple(zip(self._ast_fields, args))
        assert any(k == 'value' for k, v in params)
        inputs = OrderedDict()
        for name, value in params:
            assert isinstance(name, str)
            assert isinstance(value, Funsor)
            inputs.update(value.inputs)
        inputs = OrderedDict(inputs)
        output = reals()
        super(Distribution, self).__init__(inputs, output)
        self.params = params

    def __repr__(self):
        return '{}({})'.format(type(self).__name__,
                               ', '.join('{}={}'.format(*kv) for kv in self.params))

    def eager_subs(self, subs):
        assert isinstance(subs, tuple)
        if not any(k in self.inputs for k, v in subs):
            return self
        params = OrderedDict((k, Subs(v, subs)) for k, v in self.params)
        return type(self)(**params)

    def eager_reduce(self, op, reduced_vars):
        if op is ops.logaddexp and isinstance(self.value, Variable) and self.value.name in reduced_vars:
            return Number(0.)  # distributions are normalized
        return super(Distribution, self).eager_reduce(op, reduced_vars)

    @classmethod
    def eager_log_prob(cls, **params):
        inputs, tensors = align_tensors(*params.values())
        params = dict(zip(params, tensors))
        value = params.pop('value')
        data = cls.dist_class(**params).log_prob(value)
        return Tensor(data, inputs)


################################################################################
# Distribution Wrappers
################################################################################

class Bernoulli(Distribution):
    dist_class = dist.Bernoulli

    @staticmethod
    def _fill_defaults(probs, value='value'):
        probs = to_funsor(probs)
        value = to_funsor(value, reals())
        return probs, value

    def __init__(self, probs, value=None):
        super(Bernoulli, self).__init__(probs, value)


@eager.register(Bernoulli, Tensor, Tensor)
def eager_categorical(probs, value):
    return Bernoulli.eager_log_prob(probs=probs, value=value)


class Categorical(Distribution):
    dist_class = dist.Categorical

    @staticmethod
    def _fill_defaults(probs, value='value'):
        probs = to_funsor(probs)
        value = to_funsor(value, bint(probs.output.shape[0]))
        return probs, value

    def __init__(self, probs, value='value'):
        super(Categorical, self).__init__(probs, value)


@eager.register(Categorical, Funsor, Tensor)
def eager_categorical(probs, value):
    return probs[value].log()


@eager.register(Categorical, Tensor, Tensor)
def eager_categorical(probs, value):
    return Categorical.eager_log_prob(probs=probs, value=value)


@eager.register(Categorical, Tensor, Variable)
def eager_categorical(probs, value):
    value = materialize(value)
    return Categorical.eager_log_prob(probs=probs, value=value)


class Delta(Distribution):
    dist_class = dist.Delta

    @staticmethod
    def _fill_defaults(v, log_density=0, value='value'):
        v = to_funsor(v)
        log_density = to_funsor(log_density)
        value = to_funsor(value, v.output)
        return v, log_density, value

    def __init__(self, v, log_density=0, value='value'):
        return super(Delta, self).__init__(v, log_density, value)


@eager.register(Delta, Tensor, Tensor, Tensor)
def eager_delta(v, log_density, value):
    # This handles event_dim specially, and hence cannot use the
    # generic Delta.eager_log_prob() method.
    assert v.output == value.output
    event_dim = len(v.output.shape)
    inputs, (v, log_density, value) = align_tensors(v, log_density, value)
    data = dist.Delta(v, log_density, event_dim).log_prob(value)
    return Tensor(data, inputs)


@eager.register(Delta, Funsor, Funsor, Variable)
@eager.register(Delta, Variable, Funsor, Variable)
def eager_delta(v, log_density, value):
    assert v.output == value.output
    return funsor.delta.Delta(value.name, v, log_density)


@eager.register(Delta, Variable, Funsor, Funsor)
def eager_delta(v, log_density, value):
    assert v.output == value.output
    return funsor.delta.Delta(v.name, value, log_density)


def LogNormal(loc, scale, value='value'):
    loc, scale, y = Normal._fill_defaults(loc, scale, value)
    t = ops.exp
    x = t.inv(y)
    log_abs_det_jacobian = t.log_abs_det_jacobian(x, y)
    return Normal(loc, scale, x) - log_abs_det_jacobian


class Normal(Distribution):
    dist_class = dist.Normal

    @staticmethod
    def _fill_defaults(loc, scale, value='value'):
        loc = to_funsor(loc)
        scale = to_funsor(scale)
        assert loc.output == reals()
        assert scale.output == reals()
        value = to_funsor(value, loc.output)
        return loc, scale, value

    def __init__(self, loc, scale, value='value'):
        super(Normal, self).__init__(loc, scale, value)


@eager.register(Normal, Tensor, Tensor, Tensor)
def eager_normal(loc, scale, value):
    return Normal.eager_log_prob(loc=loc, scale=scale, value=value)


# Create a Gaussian from a ground prior or ground likelihood.
@eager.register(Normal, Tensor, Tensor, Variable)
@eager.register(Normal, Variable, Tensor, Tensor)
def eager_normal(loc, scale, value):
    if isinstance(loc, Variable):
        loc, value = value, loc

    inputs, (loc, scale) = align_tensors(loc, scale)
    loc, scale = torch.broadcast_tensors(loc, scale)
    inputs.update(value.inputs)
    int_inputs = OrderedDict((k, v) for k, v in inputs.items() if v.dtype != 'real')

    log_prob = -0.5 * math.log(2 * math.pi) - scale.log()
    loc = loc.unsqueeze(-1)
    precision = scale.pow(-2).unsqueeze(-1).unsqueeze(-1)
    return Tensor(log_prob, int_inputs) + Gaussian(loc, precision, inputs)


# Create a transformed Gaussian from a ground prior or ground likelihood.
@eager.register(Normal, Tensor, Tensor, Funsor)
@eager.register(Normal, Funsor, Tensor, Tensor)
def eager_normal(loc, scale, value):
    if not isinstance(loc, Tensor):
        loc, value = value, loc
    return Normal(loc, scale, 'value')(value=value)


@eager.register(Normal, (Variable, Affine), Tensor, (Variable, Affine))
@eager.register(Normal, (Variable, Affine), Tensor, Tensor)
@eager.register(Normal, Tensor, Tensor, (Variable, Affine))
def eager_normal(loc, scale, value):
    affine = (loc - value) / scale
    assert isinstance(affine, Affine)
    real_inputs = OrderedDict((k, v) for k, v in affine.inputs.items() if v.dtype == 'real')
    assert not any(v.shape for v in real_inputs.values())

    tensors = [affine.const] + [c for v, c in affine.coeffs.items()]
    inputs, tensors = align_tensors(*tensors)
    shape = broadcast_shape(*(t.shape for t in tensors))
    const, coeffs = tensors[0], tensors[1:]

    dim = sum(d.num_elements for d in real_inputs.values())
    loc = const.new_zeros(shape + (dim,))
    loc[..., 0] = -const / coeffs[0]
    precision = const.new_empty(shape + (dim, dim))
    for i, (v1, c1) in enumerate(zip(real_inputs, coeffs)):
        for j, (v2, c2) in enumerate(zip(real_inputs, coeffs)):
            precision[..., i, j] = c1 * c2

    log_prob = -0.5 * math.log(2 * math.pi) - scale.log()
    return log_prob + Gaussian(loc, precision, affine.inputs)


class MultivariateNormal(Distribution):
    dist_class = dist.MultivariateNormal

    @staticmethod
    def _fill_defaults(loc, scale_tril, value='value'):
        loc = to_funsor(loc)
        scale_tril = to_funsor(scale_tril)
        assert loc.dtype == 'real'
        assert scale_tril.dtype == 'real'
        assert len(loc.output.shape) == 1
        dim = loc.output.shape[0]
        assert scale_tril.output.shape == (dim, dim)
        value = to_funsor(value, loc.output)
        return loc, scale_tril, value

    def __init__(self, loc, scale_tril, value='value'):
        super(MultivariateNormal, self).__init__(loc, scale_tril, value)


@eager.register(MultivariateNormal, Tensor, Tensor, Tensor)
def eager_mvn(loc, scale_tril, value):
    return MultivariateNormal.eager_log_prob(loc=loc, scale_tril=scale_tril, value=value)


# Create a Gaussian from a ground observation.
@eager.register(MultivariateNormal, Tensor, Tensor, Variable)
@eager.register(MultivariateNormal, Variable, Tensor, Tensor)
def eager_mvn(loc, scale_tril, value):
    if isinstance(loc, Variable):
        loc, value = value, loc

    dim, = loc.output.shape
    inputs, (loc, scale_tril) = align_tensors(loc, scale_tril)
    inputs.update(value.inputs)
    int_inputs = OrderedDict((k, v) for k, v in inputs.items() if v.dtype != 'real')

    log_prob = -0.5 * dim * math.log(2 * math.pi) - scale_tril.diagonal(dim1=-1, dim2=-2).log().sum(-1)
    inv_scale_tril = torch.inverse(scale_tril)
    precision = torch.matmul(inv_scale_tril.transpose(-1, -2), inv_scale_tril)
    return Tensor(log_prob, int_inputs) + Gaussian(loc, precision, inputs)


__all__ = [
    'Categorical',
    'Delta',
    'Distribution',
    'LogNormal',
    'MultivariateNormal',
    'Normal',
]
