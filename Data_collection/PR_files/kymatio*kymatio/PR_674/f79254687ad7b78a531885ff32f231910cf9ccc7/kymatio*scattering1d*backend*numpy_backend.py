from ...backend.numpy_backend import NumpyBackend


class NumpyBackend1D(NumpyBackend):
    @classmethod
    def subsample_fourier(cls, x, k):
        """Subsampling in the Fourier domain
        Subsampling in the temporal domain amounts to periodization in the Fourier
        domain, so the input is periodized according to the subsampling factor.
        Parameters
        ----------
        x : tensor
            Input tensor with at least 3 dimensions, where the next to last
            corresponds to the frequency index in the standard PyTorch FFT
            ordering. The length of this dimension should be a power of 2 to
            avoid errors. The last dimension should represent the real and
            imaginary parts of the Fourier transform.
        k : int
            The subsampling factor.
        Returns
        -------
        res : tensor
            The input tensor periodized along the next to last axis to yield a
            tensor of size x.shape[-2] // k along that dimension.
        """
        cls.complex_check(x)

        y = x.reshape(*x.shape[:-1], k, x.shape[-1] // k)

        res = y.mean(axis=-2)

        return res

    @classmethod
    def pad(cls, x, pad_left, pad_right, pad_mode='reflect'):
        """Pad real 1D tensors
        1D implementation of the padding function for real PyTorch tensors.
        Parameters
        ----------
        x : tensor
            Three-dimensional input tensor with the third axis being the one to
            be padded.
        pad_left : int
            Amount to add on the left of the tensor (at the beginning of the
            temporal axis).
        pad_right : int
            amount to add on the right of the tensor (at the end of the temporal
            axis).
        pad_mode : str
            name of padding to use.
        Returns
        -------
        output : tensor
            The tensor passed along the third dimension.
        """
        if pad_mode == 'zero':
            pad_mode = 'constant'

        paddings = ((0, 0),) * len(x.shape[:-1])
        paddings += (pad_left, pad_right),

        output = cls._np.pad(x, paddings, mode=pad_mode)

        return output

    @staticmethod
    def unpad(x, i0, i1):
        """Unpad real 1D tensor
        Slices the input tensor at indices between i0 and i1 along the last axis.
        Parameters
        ----------
        x : tensor
            Input tensor with least one axis.
        i0 : int
            Start of original signal before padding.
        i1 : int
            End of original signal before padding.
        Returns
        -------
        x_unpadded : tensor
            The tensor x[..., i0:i1].
        """
        return x[..., i0:i1]

    @classmethod
    def zeros_like(cls, ref, shape=None):
        shape = shape if shape is not None else ref.shape
        return cls._np.zeros(shape, dtype=ref.dtype)

    @classmethod
    def fft(cls, x, axis=-1):
        return cls._np.fft.fft(x, axis=axis)

    @classmethod
    def rfft(cls, x):
        cls.real_check(x)

        return cls._np.fft.fft(x)

    @classmethod
    def irfft(cls, x):
        cls.complex_check(x)

        return cls._fft.ifft(x).real

    @classmethod
    def ifft(cls, x):
        cls.complex_check(x)

        return cls._fft.ifft(x)

    @classmethod
    def transpose(cls, x):
        """Permute time and frequency dimension for time-frequency scattering"""
        return x.transpose(*list(range(x.ndim - 2)), -1, -2)

    @classmethod
    def mean(cls, x, axis=-1):
        """Take mean along specified axis, without collapsing the axis."""
        return x.mean(axis, keepdims=True)


backend = NumpyBackend1D
