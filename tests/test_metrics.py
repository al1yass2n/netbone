from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb
from netbone.metrics.connectivity import (
    connected_component_count,
    isolated_node_count,
    strongly_connected_component_count,
    weakly_connected_component_count,
)
from netbone.metrics.retention import (
    edge_retention_fraction,
    fraction,
    node_retention_fraction,
)


def test_fraction_returns_zero_for_empty_original_count() -> None:
    assert fraction(0, 0) == 0.0


def test_fraction_rejects_invalid_counts() -> None:
    with pytest.raises(nb.ValidationError, match="non-negative"):
        fraction(-1, 2)

    with pytest.raises(nb.ValidationError, match="greater than original"):
        fraction(3, 2)


def test_node_and_edge_retention_fraction() -> None:
    original = nx.Graph()
    original.add_edge("a", "b")
    original.add_edge("b", "c")

    backbone = nx.Graph()
    backbone.add_edge("a", "b")

    assert node_retention_fraction(original, backbone) == 2 / 3
    assert edge_retention_fraction(original, backbone) == 1 / 2


def test_connectivity_metrics_for_undirected_graph() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")
    graph.add_node("c")

    assert connected_component_count(graph) == 2
    assert isolated_node_count(graph) == 1


def test_connected_component_count_rejects_directed_graph() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b")

    with pytest.raises(nb.CompatibilityError, match="undirected"):
        connected_component_count(graph)


def test_directed_connectivity_metrics_report_weak_and_strong_components() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "a")
    graph.add_edge("b", "c")
    graph.add_node("isolated")

    assert weakly_connected_component_count(graph) == 2
    assert strongly_connected_component_count(graph) == 3
    assert isolated_node_count(graph) == 1
