from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb


def test_multiple_linkage_marks_leading_incident_edges() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("a", "c", weight=1.0)
    graph.add_edge("b", "c", weight=2.0)

    result = nb.score(graph, method="multiple_linkage", weight="weight")

    assert result.primary_statistic == "multiple_linkage_selected"
    assert result.output_type == "score"
    assert result.statistics["multiple_linkage_selected"].tolist() == [1.0, 0.0, 1.0]
    assert result.statistics["multiple_linkage_endpoint_count"].tolist() == [2, 0, 1]


def test_multiple_linkage_default_filter_extracts_selected_edges() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("a", "c", weight=1.0)
    graph.add_edge("b", "c", weight=2.0)

    result = (
        nb.pipeline()
        .score("multiple_linkage", weight="weight")
        .filter("default")
        .run(graph)
    )

    assert sorted(result.graph.edges()) == [("a", "b"), ("b", "c")]


def test_multiple_linkage_excludes_zero_weight_flows() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("a", "c", weight=0.0)
    graph.add_edge("b", "c", weight=2.0)

    result = nb.score(graph, method="multiple_linkage", weight="weight")

    assert result.statistics["multiple_linkage_selected"].tolist() == [1.0, 0.0, 1.0]
    assert result.statistics["multiple_linkage_endpoint_count"].tolist() == [2, 0, 1]


def test_multiple_linkage_rejects_negative_weights() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=-1.0)

    with pytest.raises(nb.ValidationError, match="must be non-negative"):
        nb.score(graph, method="multiple_linkage", weight="weight")
