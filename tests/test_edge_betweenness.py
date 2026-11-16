from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb


def _betweenness_by_edge(result: nb.MethodResult) -> dict[frozenset[object], float]:
    return {
        frozenset((row["source"], row["target"])): row["edge_betweenness"]
        for row in result.statistics.to_dict(orient="records")
    }


def test_edge_betweenness_computes_unweighted_path_scores() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")

    result = nb.score(graph, method="edge_betweenness")

    assert list(result.statistics.columns) == [
        "edge_id",
        "source_id",
        "target_id",
        "source",
        "target",
        "edge_betweenness_weight",
        "edge_betweenness_distance",
        "edge_betweenness",
    ]
    assert result.target == "edge"
    assert result.output_type == "score"
    assert result.primary_statistic == "edge_betweenness"
    assert result.preferred_direction == "higher"
    assert result.parameters == {
        "weight": None,
        "distance_transform": "inverse",
        "normalized": True,
    }
    assert _betweenness_by_edge(result) == pytest.approx(
        {
            frozenset(("a", "b")): 2 / 3,
            frozenset(("b", "c")): 2 / 3,
        }
    )


def test_edge_betweenness_inverse_transform_treats_weights_as_strengths() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=10.0)
    graph.add_edge("b", "c", weight=10.0)
    graph.add_edge("a", "c", weight=1.0)

    result = nb.score(graph, method="edge_betweenness", weight="weight")

    assert _betweenness_by_edge(result) == pytest.approx(
        {
            frozenset(("a", "b")): 2 / 3,
            frozenset(("b", "c")): 2 / 3,
            frozenset(("a", "c")): 0.0,
        }
    )


def test_edge_betweenness_identity_transform_uses_weights_as_distances() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1.0)
    graph.add_edge("b", "c", weight=1.0)
    graph.add_edge("a", "c", weight=3.0)

    result = nb.score(
        graph,
        method="edge_betweenness",
        weight="weight",
        distance_transform="identity",
    )

    assert _betweenness_by_edge(result) == pytest.approx(
        {
            frozenset(("a", "b")): 2 / 3,
            frozenset(("b", "c")): 2 / 3,
            frozenset(("a", "c")): 0.0,
        }
    )


def test_edge_betweenness_default_filter_keeps_top_fraction() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=10.0)
    graph.add_edge("b", "c", weight=10.0)
    graph.add_edge("a", "c", weight=1.0)

    result = (
        nb.pipeline()
        .score("edge_betweenness", weight="weight")
        .filter("default")
        .run(graph)
    )

    assert result.selection.parameters["strategy"] == "fraction"
    assert result.selection.parameters["statistic"] == "edge_betweenness"
    assert result.selection.parameters["fraction"] == 0.1
    assert sorted(result.graph.edges()) == [("a", "b"), ("b", "c")]


def test_edge_betweenness_rejects_missing_weight_attribute() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")

    with pytest.raises(nb.ValidationError, match="missing required weight"):
        nb.score(graph, method="edge_betweenness", weight="weight")


def test_edge_betweenness_rejects_non_positive_weighted_distances() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=0.0)

    with pytest.raises(nb.ValidationError, match="must be positive"):
        nb.score(graph, method="edge_betweenness", weight="weight")

    with pytest.raises(nb.ValidationError, match="positive distance"):
        nb.score(
            graph,
            method="edge_betweenness",
            weight="weight",
            distance_transform="identity",
        )


def test_edge_betweenness_rejects_bad_parameters() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")

    with pytest.raises(nb.ConfigurationError, match="distance_transform"):
        nb.score(graph, method="edge_betweenness", distance_transform="unknown")

    with pytest.raises(nb.ConfigurationError, match="normalized"):
        nb.score(graph, method="edge_betweenness", normalized="yes")
