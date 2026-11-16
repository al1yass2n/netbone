from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb


def test_doubly_stochastic_scores_sinkhorn_normalized_edges() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("a", "c", weight=1.0)
    graph.add_edge("b", "c", weight=2.0)

    result = nb.score(graph, method="doubly_stochastic", weight="weight")

    assert list(result.statistics.columns) == [
        "edge_id",
        "source_id",
        "target_id",
        "source",
        "target",
        "doubly_stochastic_weight",
        "doubly_stochastic_score",
        "doubly_stochastic_connected_order",
        "doubly_stochastic_connected_selected",
    ]
    assert result.primary_statistic == "doubly_stochastic_score"
    assert result.parameters["iterations"] > 0
    assert result.parameters["epsilon_mode"] == "relative"
    assert result.parameters["effective_epsilon_by_component"] == {0: 0.0002}
    assert result.statistics["doubly_stochastic_score"].tolist() == pytest.approx(
        [0.500033, 0.499900, 0.499950],
        abs=1e-6,
    )
    assert result.statistics["doubly_stochastic_connected_selected"].tolist() == [
        1.0,
        0.0,
        1.0,
    ]


def test_doubly_stochastic_absolute_epsilon_preserves_unscaled_scores() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("a", "c", weight=1.0)
    graph.add_edge("b", "c", weight=2.0)

    result = nb.score(
        graph,
        method="doubly_stochastic",
        weight="weight",
        epsilon_mode="absolute",
    )

    assert result.parameters["epsilon_mode"] == "absolute"
    assert result.parameters["effective_epsilon_by_component"] == {0: 0.0001}
    assert result.statistics["doubly_stochastic_score"].tolist() == pytest.approx(
        [0.500017, 0.499950, 0.499975],
        abs=1e-6,
    )


def test_doubly_stochastic_relative_epsilon_is_scale_invariant() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("a", "c", weight=1.0)
    graph.add_edge("b", "c", weight=2.0)
    scaled_graph = nx.Graph()
    scaled_graph.add_edge("a", "b", weight=3000.0)
    scaled_graph.add_edge("a", "c", weight=1000.0)
    scaled_graph.add_edge("b", "c", weight=2000.0)

    result = nb.score(graph, method="doubly_stochastic", weight="weight")
    scaled = nb.score(scaled_graph, method="doubly_stochastic", weight="weight")

    assert scaled.parameters["effective_epsilon_by_component"] == {0: 0.2}
    assert scaled.statistics["doubly_stochastic_score"].tolist() == pytest.approx(
        result.statistics["doubly_stochastic_score"].tolist(),
        abs=1e-12,
    )


def test_doubly_stochastic_default_filter_extracts_connected_prefix() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("a", "c", weight=1.0)
    graph.add_edge("b", "c", weight=2.0)

    result = (
        nb.pipeline()
        .score("doubly_stochastic", weight="weight")
        .filter("default")
        .run(graph)
    )

    assert result.selection.statistic == "doubly_stochastic_connected_selected"
    assert sorted(result.graph.edges()) == [("a", "b"), ("b", "c")]
    connected_orders = result.statistics.set_index("edge_id")[
        "doubly_stochastic_connected_order"
    ]
    assert connected_orders.dropna().tolist() == [1.0, 2.0]


def test_doubly_stochastic_default_filter_connects_each_component() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("a", "c", weight=1.0)
    graph.add_edge("b", "c", weight=2.0)
    graph.add_edge("d", "e", weight=5.0)
    graph.add_edge("d", "f", weight=1.0)
    graph.add_edge("e", "f", weight=4.0)

    result = (
        nb.pipeline()
        .score("doubly_stochastic", weight="weight")
        .filter("default")
        .run(graph)
    )

    assert result.method_result.parameters["component_count"] == 2
    assert sorted(result.graph.edges()) == [
        ("a", "b"),
        ("b", "c"),
        ("d", "e"),
        ("e", "f"),
    ]
    assert result.summary()["connected_component_count"] == 2
    assert result.statistics["doubly_stochastic_connected_selected"].tolist() == [
        1.0,
        0.0,
        1.0,
        1.0,
        0.0,
        1.0,
    ]


def test_doubly_stochastic_rejects_non_positive_weights() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=0.0)

    with pytest.raises(nb.ValidationError, match="must be positive"):
        nb.score(graph, method="doubly_stochastic", weight="weight")


def test_doubly_stochastic_rejects_invalid_epsilon_mode() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1.0)

    with pytest.raises(nb.ConfigurationError, match="epsilon_mode"):
        nb.score(
            graph,
            method="doubly_stochastic",
            weight="weight",
            epsilon_mode="scaled",
        )
