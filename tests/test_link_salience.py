from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb


def _salience_by_edge(result: nb.MethodResult) -> dict[frozenset[object], float]:
    return {
        frozenset((row["source"], row["target"])): row["link_salience"]
        for row in result.statistics.to_dict(orient="records")
    }


def _directed_salience_by_edge(
    result: nb.MethodResult,
) -> dict[tuple[object, object], float]:
    return {
        (row["source"], row["target"]): row["link_salience"]
        for row in result.statistics.to_dict(orient="records")
    }


def test_link_salience_computes_shortest_path_tree_frequency() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=10.0)
    graph.add_edge("b", "c", weight=10.0)
    graph.add_edge("a", "c", weight=1.0)

    result = nb.score(graph, method="link_salience", weight="weight")

    assert list(result.statistics.columns) == [
        "edge_id",
        "source_id",
        "target_id",
        "source",
        "target",
        "link_salience_weight",
        "link_salience_distance",
        "link_salience_count",
        "link_salience",
    ]
    assert result.target == "edge"
    assert result.output_type == "score"
    assert result.primary_statistic == "link_salience"
    assert result.preferred_direction == "higher"
    assert result.parameters["distance_transform"] == "inverse"
    assert _salience_by_edge(result) == {
        frozenset(("a", "b")): 1.0,
        frozenset(("b", "c")): 1.0,
        frozenset(("a", "c")): 0.0,
    }


def test_link_salience_counts_all_shortest_path_ties() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")
    graph.add_edge("a", "c")
    graph.add_edge("b", "c")

    result = nb.score(graph, method="link_salience", weight=None)

    assert list(_salience_by_edge(result).values()) == pytest.approx([2 / 3] * 3)


def test_link_salience_uses_outgoing_shortest_paths_for_directed_graphs() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")

    result = nb.score(graph, method="link_salience", weight=None)

    assert _directed_salience_by_edge(result) == pytest.approx(
        {("a", "b"): 1 / 3, ("b", "c"): 2 / 3}
    )
    assert "not strongly connected" in result.warnings[0]


def test_link_salience_directed_pipeline_preserves_arc_direction() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "a")
    graph.add_edge("b", "c")

    result = (
        nb.pipeline()
        .score("link_salience", weight=None)
        .filter("threshold", value=0.0, operator="greater_equal")
        .run(graph)
    )

    assert isinstance(result.graph, nx.DiGraph)
    assert set(result.graph.edges()) == {("a", "b"), ("b", "a"), ("b", "c")}
    assert result.summary()["weakly_connected_component_count"] == 1
    assert result.summary()["strongly_connected_component_count"] == 2


def test_directed_graph_rejects_method_without_directed_support() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b", weight=1.0)

    with pytest.raises(nb.CompatibilityError, match="does not support directed"):
        nb.score(graph, method="edge_weight")


def test_link_salience_identity_transform_uses_weights_as_distances() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1.0)
    graph.add_edge("b", "c", weight=1.0)
    graph.add_edge("a", "c", weight=3.0)

    result = nb.score(
        graph,
        method="link_salience",
        weight="weight",
        distance_transform="identity",
    )

    assert _salience_by_edge(result) == {
        frozenset(("a", "b")): 1.0,
        frozenset(("b", "c")): 1.0,
        frozenset(("a", "c")): 0.0,
    }


def test_link_salience_default_filter_extracts_high_salience_skeleton() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=10.0)
    graph.add_edge("b", "c", weight=10.0)
    graph.add_edge("a", "c", weight=1.0)

    result = (
        nb.pipeline()
        .score("link_salience", weight="weight")
        .filter("default")
        .run(graph)
    )

    assert result.selection.parameters["strategy"] == "threshold"
    assert result.selection.parameters["statistic"] == "link_salience"
    assert result.selection.parameters["value"] == 0.5
    assert result.selection.parameters["operator"] == "greater_equal"
    assert sorted(result.graph.edges()) == [("a", "b"), ("b", "c")]


def test_link_salience_rejects_missing_weight_attribute() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")

    with pytest.raises(nb.ValidationError, match="missing required weight"):
        nb.score(graph, method="link_salience", weight="weight")


def test_link_salience_inverse_transform_rejects_non_positive_weights() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=0.0)

    with pytest.raises(nb.ValidationError, match="must be positive"):
        nb.score(graph, method="link_salience", weight="weight")
