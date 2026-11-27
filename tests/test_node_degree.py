from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb


def test_node_degree_computes_unweighted_node_scores() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    graph.add_edge("c", "d")

    result = nb.score(graph, method="node_degree")

    assert list(result.statistics.columns) == ["node_id", "node", "node_degree"]
    assert result.target == "node"
    assert result.output_type == "score"
    assert result.primary_statistic == "node_degree"
    assert result.preferred_direction == "higher"
    assert result.parameters == {}
    assert result.statistics[["node", "node_degree"]].to_dict(orient="records") == [
        {"node": "a", "node_degree": 1.0},
        {"node": "b", "node_degree": 2.0},
        {"node": "c", "node_degree": 2.0},
        {"node": "d", "node_degree": 1.0},
    ]


def test_node_degree_filter_extracts_node_induced_subgraph() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    graph.add_edge("c", "d")

    result = (
        nb.pipeline()
        .score("node_degree")
        .filter("threshold", value=2.0, operator="greater_equal")
        .run(graph)
    )

    assert result.selection.target == "node"
    assert result.selection.selected_ids == (1, 2)
    assert sorted(result.graph.nodes()) == ["b", "c"]
    assert sorted(result.graph.edges()) == [("b", "c")]
    assert result.summary()["selected_node_count"] == 2
    assert "selected_edge_count" not in result.summary()


def test_node_degree_default_filter_keeps_top_fraction() -> None:
    graph = nx.Graph()
    graph.add_edge("center", "a")
    graph.add_edge("center", "b")
    graph.add_edge("center", "c")

    result = nb.pipeline().score("node_degree").filter("default").run(graph)

    assert result.selection.parameters["strategy"] == "fraction"
    assert result.selection.parameters["statistic"] == "node_degree"
    assert result.selection.parameters["fraction"] == 0.1
    assert list(result.graph.nodes()) == ["center"]
    assert list(result.graph.edges()) == []


def test_node_degree_rejects_unknown_parameters() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")

    with pytest.raises(nb.ConfigurationError, match="does not accept"):
        nb.score(graph, method="node_degree", unknown=1)


def test_node_degree_accepts_and_ignores_weight_choices() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=2.0)
    graph.add_edge("b", "c", weight=1.0)

    baseline = nb.score(graph, method="node_degree").statistics
    for weight in (None, "auto"):
        result = nb.score(graph, method="node_degree", weight=weight)
        assert result.warnings == ()
        assert result.statistics.equals(baseline)
    named = nb.score(graph, method="node_degree", weight="weight")
    assert named.statistics.equals(baseline)
    assert any("ignores edge weights" in warning for warning in named.warnings)
