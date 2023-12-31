import tensorflow as tf

import numpy as np

from collections import namedtuple


BACKEND_NAME = 'tensorflow'

from ...backend.tensorflow_backend import Modulus
from ...backend.base_backend import FFT


def modulus_rotation(x, module):
    """Used for computing rotation invariant scattering transform coefficents.

        Parameters
        ----------
        x : tensor
            Size (batchsize, M, N, O).
        module : tensor
            Tensor that holds the overall sum.

        Returns
        -------
        output : tensor
            Tensor of the same size as input_array. It holds the output of
            the operation::

            $\\sqrt{\\sum_m (\\text{input}_\\text{array} \\star \\psi_{j,l,m})^2)}$

            which is covariant to 3D translations and rotations.

    """
    if module is None:
        module = tf.zeros_like(x, tf.float32)
    else:
        module = module ** 2
    module += tf.abs(x) ** 2
    return tf.sqrt(module)


def compute_integrals(input_array, integral_powers):
    """Computes integrals.

        Computes integrals of the input_array to the given powers.

        Parameters
        ----------
        input_array : tensor
            Size (B, M, N, O), where B is batch_size, and M, N, O are spatial
            dims.
        integral_powers : list
            List of P positive floats containing the p values used to
            compute the integrals of the input_array to the power p (l_p
            norms).

        Returns
        -------
        integrals : tensor
            Tensor of size (B, P) containing the integrals of the input_array
            to the powers p (l_p norms).

    """
    integrals = []
    for i_q, q in enumerate(integral_powers):
        integrals.append(tf.reduce_sum(tf.reshape(tf.pow(input_array, q), shape=(input_array.shape[0], -1)), axis=1))
    return tf.stack(integrals, axis=-1)


def cdgmm3d(A, B, inplace=False):
    """Complex pointwise multiplication.

        Complex pointwise multiplication between (batched) tensor A and tensor B.

        Parameters
        ----------
        A : tensor
            Complex tensor.
        B : tensor
            Complex tensor of the same size as A.
        inplace : boolean, optional
            If set True, all the operations are performed inplace.

        Returns
        -------
        output : tensor
            Tensor of the same size as A containing the result of the elementwise
            complex multiplication of A with B.

    """
    if B.ndim != 3:
        raise RuntimeError('The dimension of the second input must be 3.')

    Cr = tf.cast(tf.math.real(A) * np.real(B) - tf.math.imag(A) * np.imag(B), tf.complex64)
    Ci = tf.cast(tf.math.real(A) * np.imag(B) + tf.math.imag(A) * np.real(B), tf.complex64)

    return Cr + 1.0j * Ci


def concatenate(arrays, L):
    S = tf.stack(arrays, axis=1)
    S = tf.reshape(S, tuple((S.shape[0], S.shape[1] // (L + 1), (L + 1))) + tuple(S.shape[2:]))
    return S


backend = namedtuple('backend', ['name', 'cdgmm3d', 'fft', 'modulus', 'modulus_rotation', 'compute_integrals'])

backend.name = 'tensorflow'
backend.cdgmm3d = cdgmm3d
backend.fft = FFT(lambda x: tf.signal.fft3d(x, name='fft3d'),
                  lambda x: tf.signal.fft3d(tf.cast(x, tf.complex64), name='rfft3d'),
                  lambda x: tf.signal.ifft3d(x, name='ifft3d'),
                  lambda x: tf.math.real(tf.signal.ifft3d(x, name='irfft3d')),
                  lambda x: None)
backend.modulus = Modulus()
backend.modulus_rotation = modulus_rotation
backend.compute_integrals = compute_integrals
backend.concatenate = concatenate
