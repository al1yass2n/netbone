"""Small connectivity helpers used by result summaries."""

from __future__ import annotations

import networkx as nx

from netbone.exceptions import CompatibilityError


def connected_component_count(graph: nx.Graph) -> int:
    """Return the number of connected components in an undirected graph."""

    if graph.is_directed():
        raise CompatibilityError(
            "Connected component count is defined for undirected graphs in this "
            "vertical slice."
        )
    return nx.number_connected_components(graph) if graph.number_of_nodes() else 0


def isolated_node_count(graph: nx.Graph) -> int:
    """Return the number of isolated nodes in a graph."""

    return nx.number_of_isolates(graph)


def weakly_connected_component_count(graph: nx.Graph) -> int:
    """Return the weakly connected component count for a directed graph."""

    if not graph.is_directed():
        raise CompatibilityError(
            "Weakly connected component count is defined for directed graphs."
        )
    return (
        nx.number_weakly_connected_components(graph) if graph.number_of_nodes() else 0
    )


def strongly_connected_component_count(graph: nx.Graph) -> int:
    """Return the strongly connected component count for a directed graph."""

    if not graph.is_directed():
        raise CompatibilityError(
            "Strongly connected component count is defined for directed graphs."
        )
    return (
        nx.number_strongly_connected_components(graph) if graph.number_of_nodes() else 0
    )
