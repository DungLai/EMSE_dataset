# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union
import networkx as nx
import numpy as np
import scipy
from .. import utils

import graspologic_native as gn


def _validate_and_build_edge_list(
    graph: Union[List[Tuple[Any, Any, Union[int, float]]], nx.Graph, np.ndarray, scipy.sparse.csr.csr_matrix],
    is_weighted: Optional[bool],
    weight_attribute: str,
    check_directed: bool,
    weight_default: float,
) -> List[Tuple[str, str, float]]:
    if isinstance(graph, (nx.DiGraph, nx.MultiGraph, nx.MultiDiGraph)):
        raise TypeError("directed or multigraphs are not supported in these functions")
    if isinstance(graph, (np.ndarray, scipy.sparse.csr.csr_matrix)) and check_directed is True and not utils.is_almost_symmetric(graph):
        raise ValueError("leiden only supports undirected graphs and the adjacency matrix provided was found "
                         "to be directed")

    return utils.to_weighted_edge_list(
        graph=graph,
        weight_attribute=weight_attribute,
        weight_default=weight_default,
        is_weighted=is_weighted,
        is_directed=False
    )


def leiden(
    graph: Union[List[Tuple[Any, Any, Union[int, float]]], nx.Graph, np.ndarray, scipy.sparse.csr.csr_matrix],
    starting_communities: Optional[Dict[str, int]] = None,
    iterations: int = 1,
    resolution: float = 1.0,
    randomness: float = 0.001,
    use_modularity: bool = True,
    random_seed: Optional[int] = None,
    weight_attribute: str = "weight",
    is_weighted: Optional[bool] = None,
    weight_default: float = 1.0,
    check_directed: bool = True,
) -> Dict[str, int]:
    """
    Leiden is a global network partitioning algorithm. Given a list of edges and a maximization function, it will
    iterate through the network attempting to find an optimal partitioning of the entire network.

    Parameters
    ----------
    graph : Union[List[Tuple[Any, Any, Union[int, float]]], nx.Graph, np.ndarray, scipy.sparse.csr.csr_matrix]
        A graph representation, whether a weighted edge list referencing an undirected graph, an undirected networkx
        graph, or an undirected adjacency matrix in either numpy.ndarray or scipy.sparse.csr.csr_matrix form.
    starting_communities : Optional[Dict[str, int]]
        Default is ``None``. An optional community mapping dictionary that contains the string representation of the
        node and the community it belongs to. Note this map must contain precisely the same nodes as the graph and every
        node must have a positive community id. This mapping forms the starting point of Leiden clustering and can be
        very useful in saving the state of a previous partition schema from a previous graph and then adjusting the
        graph based on new temporal data (additions, removals, weight changes, connectivity changes, etc).
        New nodes should get their own unique community positive integer, but the original partition can be very useful
        to speed up future runs of leiden. If no community map is provided, the default behavior is to create a
        node community identity map, where every node is in their own community.
    iterations : int
        Default is ``1``. Leiden will run until a maximum quality score has been found for the node clustering and no
        nodes are moved to a new cluster in another iteration. As there is an element of randomness to the Leiden
        algorithm, it is sometimes useful to set iterations to a number larger than 1 where the entire process is
        started over, but using the new community partitioning from the last run as a starting point for another
        execution of the entire process.
    resolution : float
        Default is ``1.0``. Higher resolution values lead to more communities and lower resolution values leads to fewer
        communities. Must be greater than 0.
    randomness : float
        Default is ``0.001``. The larger the randomness value, the more exploration of the partition space is possible.
        This is a major difference from the Louvain algorithm, which is purely greedy in the partition exploration.
    use_modularity : bool
        Default is ``True``. If ``False``, will use a Constant Potts Model (CPM).
    random_seed : Optional[int]
        Default is ``None``. Can provide an optional seed to the PRNG used in Leiden for deterministic output.
    weight_attribute : str
        Default is ``weight``. Only used when creating a weighed edge list of tuples when the source graph is a
        networkx graph. This attribute corresponds to the edge data dict key.
    is_weighted : Optional[bool]
        Default is ``None``. Only used when creating a weighted edge list of tuples when the source graph is an
        adjacency matrix. The graspologic.utils.to_weighted_edge_list() function will scan these matrices and attempt
        to determine whether it is weighted or not. This flag can short circuit this test and the values in the
        adjacency matrix will be treated as weights.
    weight_default : float
        Default is ``1.0``. If the graph is a networkx graph and the graph does not have a fully weighted sequence of
        edges, this default will be used. If the adjacency matrix is found or specified to be unweighted, this
        weight_default will be used for every edge.
    check_directed : bool
        Default is ``True``. If the graph is an adjacency matrix, we will attempt to ascertain whether it is directed
        or undirected. As our leiden implementation is only known to work with an undirected graph, this function
        will raise an error if it is found to be a directed graph. If you know it is undirected and wish to avoid this
        scan, you can set this value to ``False`` and only the bottom left of the adjacency matrix will be used to
        generate the weighted edge list.

    Returns
    -------
    Dict[str, int]
        The results of running leiden over the provided graph, a dictionary containing mappings of node -> community id.
        The keys in the dictionary are the string representations of the nodes.

    Raises
    ------
    ValueError
    TypeError

    See Also
    --------
    graspologic.utils.to_weighted_edge_list()
    `graspologic native <https://github.com/microsoft/graspologic-native_>`

    References
    ----------
    .. [1] Traag, V.A.; Waltman, L.; Van, Eck N.J. "From Louvain to Leiden: guaranteeing well-connected communities",
         Scientific Reports, Vol. 9, 2019

    Notes
    -----
    This function is implemented in the `graspologic-native` Python module, a module written in Rust for Python.

    """
    graph = _validate_and_build_edge_list(graph, is_weighted, weight_attribute, check_directed, weight_default)

    _improved, _modularity, partitions = gn.leiden(
        edges=graph,
        starting_communities=starting_communities,
        resolution=resolution,
        randomness=randomness,
        iterations=iterations,
        use_modularity=use_modularity,
        seed=random_seed,
    )

    return partitions


class HierarchicalCluster(NamedTuple):
    node: str
    cluster: int
    parent_cluster: Optional[int]
    level: int
    is_final_cluster: bool

    @classmethod
    def from_native(
        cls, native_cluster: gn.HierarchicalCluster
    ) -> "HierarchicalCluster":
        return cls(
            node=native_cluster.node,
            cluster=native_cluster.cluster,
            parent_cluster=native_cluster.parent_cluster,
            level=native_cluster.level,
            is_final_cluster=native_cluster.is_final_cluster,
        )

    @staticmethod
    def final_hierarchical_clustering(
        hierarchical_clusters: List["HierarchicalCluster"]
    ) -> Dict[str, int]:
        final_clusters = (cluster for cluster in hierarchical_clusters if cluster.is_final_cluster)
        return {cluster.node: cluster.cluster for cluster in final_clusters}


def hierarchical_leiden(
    graph: Union[List[Tuple[str, str, float]], nx.Graph],
    max_cluster_size: int = 1000,
    starting_communities: Optional[Dict[str, int]] = None,
    iterations: int = 1,
    resolution: float = 1.0,
    randomness: float = 0.001,
    use_modularity: bool = True,
    random_seed: Optional[int] = None,
    weight_attribute: str = "weight",
    is_weighted: Optional[bool] = None,
    weight_default: float = 1.0,
    check_directed: bool = True,
) -> List[HierarchicalCluster]:
    """
    Leiden is a global network partitioning algorithm. Given a list of edges and a maximization function, it will
    iterate through the network attempting to find an optimal partitioning of the entire network. Unlike the function
    graspologic.partition.leiden(), this function does not stop after maximization has been achieved. On some large
    graphs, it's useful to identify particularly large communities whose membership counts exceed ``max_cluster_size``
    and induce a subnetwork solely out of that community. This subnetwork is then treated as a wholly separate entity,
    leiden is run over it, and the new, smaller communities are then mapped into the original community map space.

    The results also differ substantially; the returned List[HierarchicalCluster] is more of a log of state at each
    level. All HierarchicalClusters at level 0 should be considered to be the results of running
    `graspologic.partition.leiden()`. Every community whose membership is greater than ``max_cluster_size`` will then
    also have entries where level == 1, and so on until no communities are greater in population than
    ``max_cluster_size`` OR we are unable to break them down any further.

    Once a node's membership registration in a community cannot be changed any further, it is marked with the flag
    `graspologic.partition.HierarchicalCluster.is_final_cluster = 1.

    Parameters
    ----------
    graph : Union[List[Tuple[Any, Any, Union[int, float]]], nx.Graph, np.ndarray, scipy.sparse.csr.csr_matrix]
        A graph representation, whether a weighted edge list referencing an undirected graph, an undirected networkx
        graph, or an undirected adjacency matrix in either numpy.ndarray or scipy.sparse.csr.csr_matrix form.
    max_cluster_size : int
        Default is ``1000``. Any partition or cluster with membership >= ``max_cluster_size`` will be isolated into
        a subnetwork. This subnetwork will be used for a new leiden global partition mapping, which will then be
        remapped back into the global space after completion. Once all clusters >= ``max_cluster_size`` have been
        completed, the level increases and the partition scheme is scanned again for any new clusters >=
        ``max_cluster_size`` and the process continues until every cluster's membership is < ``max_cluster_size`` or
        if they cannot be broken into more than one new community.
    starting_communities : Optional[Dict[str, int]]
        Default is ``None``. An optional community mapping dictionary that contains the string representation of the
        node and the community it belongs to. Note this map must contain precisely the same nodes as the graph and every
        node must have a positive community id. This mapping forms the starting point of Leiden clustering and can be
        very useful in saving the state of a previous partition schema from a previous graph and then adjusting the
        graph based on new temporal data (additions, removals, weight changes, connectivity changes, etc).
        New nodes should get their own unique community positive integer, but the original partition can be very useful
        to speed up future runs of leiden. If no community map is provided, the default behavior is to create a
        node community identity map, where every node is in their own community.
    iterations : int
        Default is ``1``. Leiden will run until a maximum quality score has been found for the node clustering and no
        nodes are moved to a new cluster in another iteration. As there is an element of randomness to the Leiden
        algorithm, it is sometimes useful to set iterations to a number larger than 1 where the entire process is
        started over, but using the new community partitioning from the last run as a starting point for another
        execution of the entire process.
    resolution : float
        Default is ``1.0``. Higher resolution values lead to more communities and lower resolution values leads to fewer
        communities. Must be greater than 0.
    randomness : float
        Default is ``0.001``. The larger the randomness value, the more exploration of the partition space is possible.
        This is a major difference from the Louvain algorithm, which is purely greedy in the partition exploration.
    use_modularity : bool
        Default is ``True``. If ``False``, will use a Constant Potts Model (CPM).
    random_seed : Optional[int]
        Default is ``None``. Can provide an optional seed to the PRNG used in Leiden for deterministic output.
    weight_attribute : str
        Default is ``weight``. Only used when creating a weighed edge list of tuples when the source graph is a
        networkx graph. This attribute corresponds to the edge data dict key.
    is_weighted : Optional[bool]
        Default is ``None``. Only used when creating a weighted edge list of tuples when the source graph is an
        adjacency matrix. The graspologic.utils.to_weighted_edge_list() function will scan these matrices and attempt
        to determine whether it is weighted or not. This flag can short circuit this test and the values in the
        adjacency matrix will be treated as weights.
    weight_default : float
        Default is ``1.0``. If the graph is a networkx graph and the graph does not have a fully weighted sequence of
        edges, this default will be used. If the adjacency matrix is found or specified to be unweighted, this
        weight_default will be used for every edge.
    check_directed : bool
        Default is ``True``. If the graph is an adjacency matrix, we will attempt to ascertain whether it is directed
        or undirected. As our leiden implementation is only known to work with an undirected graph, this function
        will raise an error if it is found to be a directed graph. If you know it is undirected and wish to avoid this
        scan, you can set this value to ``False`` and only the bottom left of the adjacency matrix will be used to
        generate the weighted edge list.

    Returns
    -------
    List[HierarchicalCluster]
        The results of running hierarchical leiden over the provided graph, a list of HierarchicalClusters identifying
        the state of every node and cluster at each level. The function
        graspologic.partition.HierarchicalCluster.final_hierarchical_clustering() can be used to create a
        dictionary mapping of node -> cluster ID that corresponds to the output of `graspologic.partition.leiden()`

    Raises
    ------
    ValueError
    TypeError

    See Also
    --------
    graspologic.utils.to_weighted_edge_list()
    `graspologic native <https://github.com/microsoft/graspologic-native_>`

    References
    ----------
    .. [1] Traag, V.A.; Waltman, L.; Van, Eck N.J. "From Louvain to Leiden: guaranteeing well-connected communities",
         Scientific Reports, Vol. 9, 2019

    Notes
    -----
    This function is implemented in the `graspologic-native` Python module, a module written in Rust for Python.

    """
    graph = _validate_and_build_edge_list(graph, is_weighted, weight_attribute, check_directed, weight_default)
    hierarchical_clusters_native = gn.hierarchical_leiden(
        edges=graph,
        starting_communities=starting_communities,
        resolution=resolution,
        randomness=randomness,
        iterations=iterations,
        use_modularity=use_modularity,
        max_cluster_size=max_cluster_size,
        seed=random_seed,
    )

    return [
        HierarchicalCluster.from_native(entry) for entry in hierarchical_clusters_native
    ]
