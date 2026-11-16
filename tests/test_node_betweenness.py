from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb


def _betweenness_by_node(result: nb.MethodResult) -> dict[object, float]:
    return {
        row["node"]: row["node_betweenness"]
        for row in result.statistics.to_dict(orient="records")
    }


def test_node_betweenness_computes_unweighted_scores() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    graph.add_edge("c", "d")

    result = nb.score(graph, method="node_betweenness")

    assert list(result.statistics.columns) == [
        "node_id",
        "node",
        "node_betweenness",
    ]
    assert result.target == "node"
    assert result.output_type == "score"
    assert result.primary_statistic == "node_betweenness"
    assert result.preferred_direction == "higher"
    assert result.parameters == {
        "weight": None,
        "distance_transform": "inverse",
        "normalized": True,
        "endpoints": False,
    }
    assert _betweenness_by_node(result) == pytest.approx(
        {
            "a": 0.0,
            "b": 2 / 3,
            "c": 2 / 3,
            "d": 0.0,
        }
    )


def test_node_betweenness_filter_extracts_node_induced_subgraph() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    graph.add_edge("c", "d")

    result = (
        nb.pipeline()
        .score("node_betweenness")
        .filter("threshold", value=0.0, operator="greater")
        .run(graph)
    )

    assert result.selection.target == "node"
    assert sorted(result.graph.nodes()) == ["b", "c"]
    assert sorted(result.graph.edges()) == [("b", "c")]


def test_node_betweenness_inverse_transform_treats_weights_as_strengths() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=10.0)
    graph.add_edge("b", "c", weight=10.0)
    graph.add_edge("a", "c", weight=1.0)

    result = nb.score(graph, method="node_betweenness", weight="weight")

    assert _betweenness_by_node(result) == pytest.approx(
        {
            "a": 0.0,
            "b": 1.0,
            "c": 0.0,
        }
    )


def test_node_betweenness_identity_transform_uses_weights_as_distances() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1.0)
    graph.add_edge("b", "c", weight=1.0)
    graph.add_edge("a", "c", weight=3.0)

    result = nb.score(
        graph,
        method="node_betweenness",
        weight="weight",
        distance_transform="identity",
    )

    assert _betweenness_by_node(result) == pytest.approx(
        {
            "a": 0.0,
            "b": 1.0,
            "c": 0.0,
        }
    )


def test_node_betweenness_default_filter_keeps_top_fraction() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    graph.add_edge("c", "d")

    result = nb.pipeline().score("node_betweenness").filter("default").run(graph)

    assert result.selection.parameters["strategy"] == "fraction"
    assert result.selection.parameters["statistic"] == "node_betweenness"
    assert result.selection.parameters["fraction"] == 0.1
    assert sorted(result.graph.nodes()) == ["b", "c"]


def test_node_betweenness_rejects_missing_and_non_positive_weights() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")

    with pytest.raises(nb.ValidationError, match="missing required weight"):
        nb.score(graph, method="node_betweenness", weight="weight")

    graph["a"]["b"]["weight"] = 0.0
    with pytest.raises(nb.ValidationError, match="must be positive"):
        nb.score(graph, method="node_betweenness", weight="weight")

    with pytest.raises(nb.ValidationError, match="positive distance"):
        nb.score(
            graph,
            method="node_betweenness",
            weight="weight",
            distance_transform="identity",
        )


def test_node_betweenness_rejects_bad_parameters() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")

    with pytest.raises(nb.ConfigurationError, match="distance_transform"):
        nb.score(graph, method="node_betweenness", distance_transform="unknown")

    with pytest.raises(nb.ConfigurationError, match="normalized"):
        nb.score(graph, method="node_betweenness", normalized="yes")

    with pytest.raises(nb.ConfigurationError, match="endpoints"):
        nb.score(graph, method="node_betweenness", endpoints="yes")
