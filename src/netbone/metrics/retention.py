"""Small retention helpers used by result summaries."""

from __future__ import annotations

import networkx as nx

from netbone.exceptions import ValidationError


def fraction(part: int, whole: int) -> float:
    """Return `part / whole`, or `0.0` when the denominator is zero."""

    if part < 0 or whole < 0:
        raise ValidationError("Retention counts must be non-negative.")
    if part > whole:
        raise ValidationError("Retained count cannot be greater than original count.")
    return part / whole if whole else 0.0


def node_retention_fraction(
    original_graph: nx.Graph, backbone_graph: nx.Graph
) -> float:
    """Return the fraction of original nodes retained in the backbone graph."""

    return fraction(backbone_graph.number_of_nodes(), original_graph.number_of_nodes())


def edge_retention_fraction(
    original_graph: nx.Graph, backbone_graph: nx.Graph
) -> float:
    """Return the fraction of original edges retained in the backbone graph."""

    return fraction(backbone_graph.number_of_edges(), original_graph.number_of_edges())
