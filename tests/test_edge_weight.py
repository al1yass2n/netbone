from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb


def test_edge_weight_computes_weighted_statistics() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=2.5)
    graph.add_edge("b", "c", weight=1.5)

    result = nb.pipeline().score("edge_weight", weight="weight").compute(graph)

    assert list(result.statistics.columns) == [
        "edge_id",
        "source_id",
        "target_id",
        "source",
        "target",
        "score",
    ]
    assert result.target == "edge"
    assert result.output_type == "score"
    assert result.primary_statistic == "score"
    assert result.preferred_direction == "higher"
    assert result.statistics["score"].tolist() == [2.5, 1.5]


def test_edge_weight_scores_unweighted_edges_as_one() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")

    result = nb.score(graph)

    assert result.parameters["weight"] is None
    assert result.statistics["score"].tolist() == [1.0, 1.0]


def test_edge_weight_rejects_missing_weight_attribute() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")

    with pytest.raises(nb.ValidationError, match="missing required weight"):
        nb.score(graph, weight="weight")


def test_edge_weight_rejects_non_numeric_weight_attribute() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight="heavy")

    with pytest.raises(nb.ValidationError, match="must be numeric"):
        nb.score(graph, weight="weight")
