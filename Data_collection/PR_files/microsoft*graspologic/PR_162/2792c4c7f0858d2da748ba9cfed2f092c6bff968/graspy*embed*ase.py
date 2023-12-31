# ase.py
# Created by Ben Pedigo on 2018-09-15.
# Email: bpedigo@jhu.edu
import warnings

from .base import BaseEmbed
from .svd import selectSVD
from ..utils import import_graph, get_lcc, is_fully_connected

import numpy as np
from sklearn.utils.validation import check_is_fitted


class AdjacencySpectralEmbed(BaseEmbed):
    r"""
    Class for computing the adjacency spectral embedding of a graph 
    
    The adjacency spectral embedding (ASE) is a k-dimensional Euclidean representation of 
    the graph based on its adjacency matrix [1]_. It relies on an SVD to reduce the dimensionality
    to the specified k, or if k is unspecified, can find a number of dimensions automatically
    (see graspy.embed.selectSVD).

    Parameters
    ----------
    n_components : int or None, default = None
        Desired dimensionality of output data. If "full", 
        n_components must be <= min(X.shape). Otherwise, n_components must be
        < min(X.shape). If None, then optimal dimensions will be chosen by
        ``select_dimension`` using ``n_elbows`` argument.
    n_elbows : int, optional, default: 2
        If `n_components=None`, then compute the optimal embedding dimension using
        `select_dimension`. Otherwise, ignored.
    algorithm : {'randomized' (default), 'full', 'truncated'}, optional
        SVD solver to use:

        - 'randomized'
            Computes randomized svd using 
            ``sklearn.utils.extmath.randomized_svd``
        - 'full'
            Computes full svd using ``scipy.linalg.svd``
        - 'truncated'
            Computes truncated svd using ``scipy.sparse.linalg.svd``
    n_iter : int, optional (default = 5)
        Number of iterations for randomized SVD solver. Not used by 'full' or 
        'truncated'. The default is larger than the default in randomized_svd 
        to handle sparse matrices that may have large slowly decaying spectrum.
    check_lcc : bool , optional (defult = True)
        Whether to check if input graph is connected. May result in non-optimal 
        results if the graph is unconnected. If True and input is unconnected,
        a UserWarning is thrown. Not checking for connectedness may result in 
        faster computation.

    Attributes
    ----------
    latent_left_ : array, shape (n_samples, n_components)
        Estimated left latent positions of the graph. 
    latent_right_ : array, shape (n_samples, n_components), or None
        Only computed when the graph is directed, or adjacency matrix is assymetric.
        Estimated right latent positions of the graph. Otherwise, None.
    singular_values_ : array, shape (n_components)
        Singular values associated with the latent position matrices. 

    See Also
    --------
    graspy.embed.selectSVD
    graspy.embed.select_dimension

    Notes
    -----
    The singular value decomposition: 

    .. math:: A = U \Sigma V^T

    is used to find an orthonormal basis for a matrix, which in our case is the adjacency
    matrix of the graph. These basis vectors (in the matrices U or V) are ordered according 
    to the amount of variance they explain in the original matrix. By selecting a subset of these
    basis vectors (through our choice of dimensionality reduction) we can find a lower dimensional 
    space in which to represent the graph.

    References
    ----------
    .. [1] Sussman, D.L., Tang, M., Fishkind, D.E., Priebe, C.E.  "A
       Consistent Adjacency Spectral Embedding for Stochastic Blockmodel Graphs,"
       Journal of the American Statistical Association, Vol. 107(499), 2012
    .. [2] Levin, K., Roosta-Khorasani, F., Mahoney, M. W., & Priebe, C. E. (2018). Out-of-sample 
        extension of graph adjacency spectral embedding. PMLR: Proceedings of Machine Learning 
        Research, 80, 2975-2984.
    """

    def __init__(
        self,
        n_components=None,
        n_elbows=2,
        algorithm="randomized",
        n_iter=5,
        check_lcc=True,
    ):
        super().__init__(
            n_components=n_components,
            n_elbows=n_elbows,
            algorithm=algorithm,
            n_iter=n_iter,
            check_lcc=check_lcc,
        )

    def fit(self, graph, y=None):
        """
        Fit ASE model to input graph

        Parameters
        ----------
        graph : array_like or networkx.Graph
            Input graph to embed.

        Returns
        -------
        self : returns an instance of self.
        """
        A = import_graph(graph)

        if self.check_lcc:
            if not is_fully_connected(A):
                msg = (
                    "Input graph is not fully connected. Results may not"
                    + "be optimal. You can compute the largest connected component by"
                    + "using ``graspy.utils.get_lcc``."
                )
                warnings.warn(msg, UserWarning)

        self._reduce_dim(A)
        return self

    def predict(self, X):
        """
        Embed out of sample vertices.

        Parameters
        ----------
        X : array_like
            m stacked similarity lists, where the jth entry of the ith row corresponds to
            the similarity of the ith out of sample observation to the jth in sample
            observation.

        Returns
        -------
        oos_embedding : array, shape (m, d)
            The embedding of the out of sample vertices.
        """    

        # Check if fit is already called
        check_is_fitted(self, ["latent_left_"], all_or_any=all)

        is_embedding = self.latent_left_
        n = is_embedding.shape[0]

        # Type checking
        if isinstance(X, np.ndarray):
            if X.ndim is 1:
                X = X.reshape((1, -1))
                X = X.T
            elif X.ndim is 2:
                if X.shape[1] == n:
                    X = X.T
                elif X.shape[0] != n:
                    msg = (
                        "Simlarity vectors must be of shape (m, n) or (n, m)."
                    )
                    raise ValueError(msg)
            else:
                msg = ( 
                    "The dimension of array must be 1 or 2."
                )
        else:
            msg = (
                "Similarity vector must by an array."
            )
            raise TypeError(msg)

        oos_embedding = X.T @ np.linalg.pinv(is_embedding).T

        return oos_embedding
















