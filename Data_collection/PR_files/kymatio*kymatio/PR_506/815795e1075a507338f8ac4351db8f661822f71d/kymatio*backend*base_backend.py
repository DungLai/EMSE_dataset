

class FFT:
    def __init__(self, fft, ifft, irfft, sanity_checks):
        self.fft = fft
        self.ifft = ifft
        self.irfft = irfft
        self.sanity_checks = sanity_checks

    def fft_forward(self, x, direction='C2C', inverse=False):
        """Interface with torch FFT routines for 2D signals.

            Example
            -------
            x = torch.randn(128, 32, 32, 2)
            x_fft = fft(x)
            x_ifft = fft(x, inverse=True)

            Parameters
            ----------
            x : tensor
                Complex input for the FFT.
            direction : string
                'C2R' for complex to real, 'C2C' for complex to complex.
            inverse : bool
                True for computing the inverse FFT.
                NB : If direction is equal to 'C2R', then an error is raised.

            Raises
            ------
            RuntimeError
                In the event that we are going from complex to real and not doing
                the inverse FFT or in the event x is not contiguous.
            TypeError
                In the event that x does not have a final dimension 2 i.e. not
                complex.

            Returns
            -------
            output : tensor
                Result of FFT or IFFT.

        """
        if direction == 'C2R':
            if not inverse:
                raise RuntimeError('C2R mode can only be done with an inverse FFT.')

        self.sanity_checks(x)

        if direction == 'C2R':
            output = self.irfft(x)
        elif direction == 'C2C':
            if inverse:
                output = self.ifft(x)
            else:
                output = self.fft(x)

        return output

    def __call__(self, x, direction='C2C', inverse=False):
        return self.fft_forward(x, direction=direction, inverse=inverse)
    
