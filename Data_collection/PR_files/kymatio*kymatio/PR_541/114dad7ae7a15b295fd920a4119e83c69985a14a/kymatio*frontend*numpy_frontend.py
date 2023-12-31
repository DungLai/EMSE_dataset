class ScatteringNumPy:
    def __init__(self):
        self.frontend_name = 'numpy'

    def scattering(self, x):
        """ This function should compute the scattering transform."""
        raise NotImplementedError

    def __call__(self, x):
        """This method is an alias for `scattering`."""
        return self.scattering(x)

    _doc_array = 'np.ndarray'
    _doc_array_n = 'n'

    _doc_alias_name = '__call__'

    _doc_alias_call = ''

    _doc_frontend_paragraph = ''

    _doc_sample = 'np.random.randn({shape})'
