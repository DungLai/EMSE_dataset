# Authors: Edouard Oyallon, Sergey Zagoruyko, Muawiz Chaudhary

import numpy as np
from collections import namedtuple
from scipy.fftpack import fft2, ifft2

BACKEND_NAME = 'numpy'


from ...backend.numpy_backend import modulus, _iscomplex, _isreal


class Pad(object):
    def __init__(self, pad_size, input_size, pre_pad=False):
        """
            Padding which allows to simultaneously pad in a reflection fashion
            and map to complex.

            Parameters
            ----------
            pad_size : list of 4 integers
                size of padding to apply.
            input_size : list of 2 integers
                size of the original signal
            pre_pad : boolean
                if set to true, then there is no padding, one simply converts
                from real to complex.

        """
        self.pre_pad = pre_pad
        self.pad_size = pad_size

    def __call__(self, x):
        if self.pre_pad:
            return x
        else:
            np_pad = ((self.pad_size[0], self.pad_size[1]), (self.pad_size[2], self.pad_size[3]))
            output = np.pad(x, ((0,0), np_pad[0], np_pad[1]), mode='reflect')
            return output


def unpad(in_):
    """
        Slices the input tensor at indices between 1::-1

        Parameters
        ----------
        in_ : tensor_like
            input tensor

        Returns
        -------
        in_[..., 1:-1, 1:-1]

    """
    return in_[..., 1:-1, 1:-1]


class SubsampleFourier(object):
    """ Subsampling of a 2D image performed in the Fourier domain.

        Subsampling in the spatial domain amounts to periodization
        in the Fourier domain, hence the formula.

        Parameters
        ----------
        x : tensor_like
            input tensor with at least three dimensions.
        k : int
            integer such that x is subsampled by k along the spatial variables.

        Returns
        -------
        out : tensor_like
            Tensor such that its Fourier transform is the Fourier
            transform of a subsampled version of x, i.e. in
            F^{-1}(out)[u1, u2] = F^{-1}(x)[u1 * k, u2 * k]

    """
    def __call__(self, x, k):
        y = x.reshape(-1, k, x.shape[1] // k, k, x.shape[2] // k)

        out = y.mean(axis=(1, 3))

        return out


def cdgmm(A, B, inplace=False):
    """
        Complex pointwise multiplication between (batched) tensor A and tensor B.

        Parameters
        ----------
        A : tensor
            A is a complex tensor of size (B, C, M, N, 2)
        B : tensor
            B is a complex tensor of size (M, N) or real tensor of (M, N)
        inplace : boolean, optional
            if set to True, all the operations are performed inplace

        Returns
        -------
        C : tensor
            output tensor of size (B, C, M, N, 2) such that:
            C[b, c, m, n, :] = A[b, c, m, n, :] * B[m, n, :]

    """
    if not _iscomplex(A):
        raise TypeError('The first input must be complex.')

    if B.ndim != 2:
        raise RuntimeError('The dimension of the second input must be 2.')

    if not _iscomplex(B) and not _isreal(B):
        raise TypeError('The second input must be complex or real.')

    if A.shape[-2:] != B.shape[-2:]:
        raise RuntimeError('The inputs are not compatible for '
                           'multiplication.')

    if inplace:
        return np.multiply(A, B, out=A)
    else:
        return A * B


def concatenate(arrays):
    return np.stack(arrays, axis=-3)


backend = namedtuple('backend', ['name', 'cdgmm', 'modulus', 'subsample_fourier', 'fft', 'Pad', 'unpad', 'concatenate'])
backend.name = 'numpy'
backend.cdgmm = cdgmm
backend.modulus = modulus
backend.subsample_fourier = SubsampleFourier()
backend.fft = FFT(lambda x:np.fft.fft2(x),
                  lambda x:np.fft.ifft2(x),
                  lambda x:np.real(np.fft.ifft2(x)),
                  lambda x:None)
backend.Pad = Pad
backend.unpad = unpad
backend.concatenate = concatenate
