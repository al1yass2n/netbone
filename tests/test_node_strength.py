from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb


def test_node_strength_computes_weighted_degree() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=2.0)
    graph.add_edge("b", "c", weight=3.0)
    graph.add_edge("c", "d", weight=1.0)

    result = nb.score(graph, method="node_strength", weight="weight")

    assert list(result.statistics.columns) == ["node_id", "node", "node_strength"]
    assert result.target == "node"
    assert result.output_type == "score"
    assert result.primary_statistic == "node_strength"
    assert result.preferred_direction == "higher"
    assert result.parameters == {"weight": "weight", "direction": "total"}
    assert result.statistics[["node", "node_strength"]].to_dict(orient="records") == [
        {"node": "a", "node_strength": 2.0},
        {"node": "b", "node_strength": 5.0},
        {"node": "c", "node_strength": 4.0},
        {"node": "d", "node_strength": 1.0},
    ]


def test_node_strength_filter_extracts_node_induced_subgraph() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=2.0)
    graph.add_edge("b", "c", weight=3.0)
    graph.add_edge("c", "d", weight=1.0)

    result = (
        nb.pipeline()
        .score("node_strength", weight="weight")
        .filter("threshold", value=4.0, operator="greater_equal")
        .run(graph)
    )

    assert sorted(result.graph.nodes()) == ["b", "c"]
    assert sorted(result.graph.edges()) == [("b", "c")]
    assert result.summary()["node_fraction"] == 0.5
    assert result.summary()["edge_fraction"] == 1 / 3


def test_node_strength_default_filter_keeps_top_fraction() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=2.0)
    graph.add_edge("b", "c", weight=3.0)
    graph.add_edge("c", "d", weight=1.0)

    result = (
        nb.pipeline()
        .score("node_strength", weight="weight")
        .filter("default")
        .run(graph)
    )

    assert result.selection.parameters["strategy"] == "fraction"
    assert result.selection.parameters["statistic"] == "node_strength"
    assert list(result.graph.nodes()) == ["b"]


def test_node_strength_rejects_missing_and_bad_weights() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")

    with pytest.raises(nb.ValidationError, match="missing required weight"):
        nb.score(graph, method="node_strength", weight="weight")

    graph["a"]["b"]["weight"] = "heavy"
    with pytest.raises(nb.ValidationError, match="must be numeric"):
        nb.score(graph, method="node_strength", weight="weight")

    graph["a"]["b"]["weight"] = float("nan")
    with pytest.raises(nb.ValidationError, match="must be finite"):
        nb.score(graph, method="node_strength", weight="weight")


def test_node_strength_rejects_bad_parameter_type() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1.0)

    with pytest.raises(nb.ConfigurationError, match="weight"):
        nb.score(graph, method="node_strength", weight=None)


def test_node_strength_directed_supports_total_in_and_out() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("b", "c", weight=1.0)
    graph.add_edge("c", "a", weight=2.0)

    def strengths(**parameters: object) -> dict[str, float]:
        result = nb.score(graph, method="node_strength", **parameters)
        return dict(
            zip(
                result.statistics["node"],
                result.statistics["node_strength"],
                strict=False,
            )
        )

    assert strengths() == {"a": 5.0, "b": 4.0, "c": 3.0}
    assert strengths(direction="in") == {"a": 2.0, "b": 3.0, "c": 1.0}
    assert strengths(direction="out") == {"a": 3.0, "b": 1.0, "c": 2.0}


def test_node_strength_direction_on_undirected_graph_uses_total() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("b", "c", weight=1.0)

    result = nb.score(graph, method="node_strength", direction="in")

    assert result.statistics["node_strength"].tolist() == [3.0, 4.0, 1.0]
    assert any("no effect on an undirected graph" in item for item in result.warnings)


def test_node_strength_rejects_unknown_direction() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b", weight=1.0)

    with pytest.raises(nb.ConfigurationError, match="'direction' must be one of"):
        nb.score(graph, method="node_strength", direction="both")
    with pytest.raises(nb.ConfigurationError, match="must be a string"):
        nb.score(graph, method="node_strength", direction=1)
