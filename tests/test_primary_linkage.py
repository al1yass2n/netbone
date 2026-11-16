from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb


def test_primary_linkage_marks_each_nodes_strongest_edge() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("a", "c", weight=2.0)
    graph.add_edge("b", "c", weight=1.0)
    graph.add_edge("c", "d", weight=4.0)

    result = nb.score(graph, method="primary_linkage", weight="weight")

    assert list(result.statistics.columns) == [
        "edge_id",
        "source_id",
        "target_id",
        "source",
        "target",
        "primary_linkage_weight",
        "primary_linkage_endpoint_count",
        "primary_linkage_selected",
    ]
    assert result.primary_statistic == "primary_linkage_selected"
    assert result.statistics["primary_linkage_selected"].tolist() == [
        1.0,
        0.0,
        0.0,
        1.0,
    ]
    assert result.statistics["primary_linkage_endpoint_count"].tolist() == [2, 0, 0, 2]


def test_primary_linkage_default_filter_extracts_selected_edges() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("a", "c", weight=2.0)
    graph.add_edge("b", "c", weight=1.0)
    graph.add_edge("c", "d", weight=4.0)

    result = (
        nb.pipeline()
        .score("primary_linkage", weight="weight")
        .filter("default")
        .run(graph)
    )

    assert sorted(result.graph.edges()) == [("a", "b"), ("c", "d")]


def test_primary_linkage_breaks_ties_by_stable_edge_id() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1.0)
    graph.add_edge("a", "c", weight=1.0)

    result = nb.score(graph, method="primary_linkage", weight="weight")

    assert result.statistics["primary_linkage_selected"].tolist() == [1.0, 1.0]
    assert result.statistics["primary_linkage_endpoint_count"].tolist() == [2, 1]
    assert result.warnings == (
        "Primary linkage encountered tied maximum weights for one or more "
        "nodes; ties were broken by stable edge_id order.",
    )


def test_primary_linkage_rejects_missing_and_bad_weights() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")

    with pytest.raises(nb.ValidationError, match="missing required weight"):
        nb.score(graph, method="primary_linkage", weight="weight")

    graph["a"]["b"]["weight"] = "heavy"
    with pytest.raises(nb.ValidationError, match="must be numeric"):
        nb.score(graph, method="primary_linkage", weight="weight")
