from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb


def test_lans_computes_hand_checkable_empirical_pvalues() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("a", "c", weight=1.0)
    graph.add_edge("b", "c", weight=2.0)

    result = nb.pipeline().score("lans", weight="weight").compute(graph)

    assert list(result.statistics.columns) == [
        "edge_id",
        "source_id",
        "target_id",
        "source",
        "target",
        "lans_weight",
        "lans_source_fraction",
        "lans_target_fraction",
        "lans_source_pvalue",
        "lans_target_pvalue",
        "lans_pvalue",
    ]
    assert result.target == "edge"
    assert result.output_type == "pvalue"
    assert result.primary_statistic == "lans_pvalue"
    assert result.preferred_direction == "lower"
    assert result.metadata["default_filter"] == "significance"
    assert result.statistics["lans_pvalue"].tolist() == pytest.approx([0.0, 0.5, 0.0])


def test_lans_can_choose_endpoint_pvalue_aggregation() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("a", "c", weight=1.0)
    graph.add_edge("b", "c", weight=2.0)

    result = nb.score(
        graph,
        method="lans",
        weight="weight",
        pvalue_aggregation="max",
    )

    assert result.statistics["lans_pvalue"].tolist() == pytest.approx([0.0, 0.5, 0.5])
    assert result.parameters["pvalue_aggregation"] == "max"


def test_lans_directed_checks_source_outgoing_and_target_incoming() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("a", "c", weight=1.0)
    graph.add_edge("b", "c", weight=2.0)
    graph.add_edge("d", "c", weight=5.0)

    result = nb.score(graph, method="lans", pvalue_aggregation="max")
    statistics = result.statistics

    assert statistics["lans_source_fraction"].tolist() == pytest.approx(
        [0.75, 0.25, 1.0, 1.0]
    )
    assert statistics["lans_target_fraction"].tolist() == pytest.approx(
        [1.0, 0.125, 0.25, 0.625]
    )
    assert statistics["lans_source_pvalue"].tolist() == pytest.approx(
        [0.0, 0.5, 0.0, 0.0]
    )
    assert statistics["lans_target_pvalue"].tolist() == pytest.approx(
        [0.0, 2 / 3, 1 / 3, 0.0]
    )
    assert statistics["lans_pvalue"].tolist() == pytest.approx([0.0, 2 / 3, 1 / 3, 0.0])
    assert result.warnings == ()


def test_lans_symmetric_digraph_matches_undirected_scores() -> None:
    graph = nx.karate_club_graph()
    for index, (source, target) in enumerate(graph.edges()):
        graph[source][target]["weight"] = float((index * 7) % 11 + 1)

    undirected = nb.score(graph, method="lans").statistics
    directed = nb.score(graph.to_directed(), method="lans").statistics
    expected = {
        frozenset((source, target)): value
        for source, target, value in zip(
            undirected["source"],
            undirected["target"],
            undirected["lans_pvalue"],
            strict=False,
        )
    }

    for source, target, value in zip(
        directed["source"], directed["target"], directed["lans_pvalue"], strict=False
    ):
        assert value == pytest.approx(expected[frozenset((source, target))])


def test_lans_leaf_policy_zero_is_default() -> None:
    graph = nx.Graph()
    graph.add_edge("center", "leaf_a", weight=3.0)
    graph.add_edge("center", "leaf_b", weight=1.0)

    zero_leaf = nb.score(graph, method="lans", weight="weight")
    ignore_leaf = nb.score(
        graph,
        method="lans",
        weight="weight",
        leaf_policy="ignore",
    )

    assert zero_leaf.parameters["leaf_policy"] == "zero"
    assert zero_leaf.statistics["lans_pvalue"].tolist() == [0.0, 0.0]
    assert ignore_leaf.statistics["lans_pvalue"].tolist() == pytest.approx([0.0, 0.5])


def test_lans_rejects_non_positive_weights() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=0.0)

    with pytest.raises(nb.ValidationError, match="must be positive"):
        nb.score(graph, method="lans", weight="weight")


def test_lans_default_filter_resolves_to_significance() -> None:
    graph = nx.Graph()
    graph.add_edge("center", "leaf_a", weight=3.0)
    graph.add_edge("center", "leaf_b", weight=1.0)

    result = nb.pipeline().score("lans", weight="weight").filter("default").run(graph)

    assert result.selection.parameters["strategy"] == "significance"
    assert result.selection.parameters["alpha"] == 0.05
    assert sorted(result.graph.edges()) == [
        ("center", "leaf_a"),
        ("center", "leaf_b"),
    ]


def test_lans_significance_filter_uses_primary_statistic_by_default() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("b", "c", weight=1.0)
    graph.add_edge("b", "d", weight=2.0)

    result = (
        nb.pipeline()
        .score("lans")
        .filter("significance", alpha=0.3, drop_isolates=False)
        .run(graph)
    )

    assert result.selection.statistic == "lans_pvalue"
    assert result.selection.parameters["statistic"] == "lans_pvalue"
    assert sorted(result.graph.edges()) == [("a", "b"), ("b", "c"), ("b", "d")]
