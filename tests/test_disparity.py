from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb


def test_disparity_computes_hand_checkable_edge_pvalues() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("a", "c", weight=1.0)
    graph.add_edge("b", "c", weight=2.0)

    result = nb.pipeline().score("disparity", weight="weight").compute(graph)

    assert list(result.statistics.columns) == [
        "edge_id",
        "source_id",
        "target_id",
        "source",
        "target",
        "disparity_weight",
        "disparity_source_fraction",
        "disparity_target_fraction",
        "disparity_source_pvalue",
        "disparity_target_pvalue",
        "disparity_pvalue",
    ]
    assert result.target == "edge"
    assert result.output_type == "pvalue"
    assert result.primary_statistic == "disparity_pvalue"
    assert result.preferred_direction == "lower"
    assert result.metadata["default_filter"] == "significance"
    assert result.statistics["disparity_pvalue"].tolist() == pytest.approx(
        [0.25, 2 / 3, 1 / 3]
    )


def test_disparity_can_choose_endpoint_pvalue_aggregation() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("a", "c", weight=1.0)
    graph.add_edge("b", "c", weight=2.0)

    result = nb.score(
        graph,
        method="disparity",
        weight="weight",
        pvalue_aggregation="max",
    )

    assert result.statistics["disparity_pvalue"].tolist() == pytest.approx(
        [0.4, 0.75, 0.6]
    )
    assert result.parameters["pvalue_aggregation"] == "max"


def test_directed_disparity_uses_outgoing_and_incoming_distributions() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "x", weight=4.0)
    graph.add_edge("a", "y", weight=1.0)
    graph.add_edge("b", "x", weight=1.0)
    graph.add_edge("c", "x", weight=3.0)

    result = nb.score(graph, method="disparity", weight="weight", leaf_policy="ignore")
    rows = result.statistics.set_index(["source", "target"])

    assert result.metadata["supports_directed"] is True
    assert result.metadata["directed_semantics"] == (
        "source_outgoing_and_target_incoming_distributions"
    )
    assert rows.loc[("a", "x"), "disparity_source_fraction"] == pytest.approx(0.8)
    assert rows.loc[("a", "x"), "disparity_target_fraction"] == pytest.approx(0.5)
    assert rows.loc[("a", "x"), "disparity_source_pvalue"] == pytest.approx(0.2)
    assert rows.loc[("a", "x"), "disparity_target_pvalue"] == pytest.approx(0.25)
    assert rows.loc[("a", "x"), "disparity_pvalue"] == pytest.approx(0.2)
    assert rows.loc[("a", "y"), "disparity_pvalue"] == pytest.approx(0.8)
    assert rows.loc[("b", "x"), "disparity_pvalue"] == pytest.approx(0.765625)
    assert rows.loc[("c", "x"), "disparity_pvalue"] == pytest.approx(0.390625)


def test_directed_disparity_combines_arc_endpoint_pvalues() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "x", weight=4.0)
    graph.add_edge("a", "y", weight=1.0)
    graph.add_edge("b", "x", weight=1.0)
    graph.add_edge("c", "x", weight=3.0)

    maximum = nb.score(
        graph,
        method="disparity",
        pvalue_aggregation="max",
    ).statistics.set_index(["source", "target"])
    average = nb.score(
        graph,
        method="disparity",
        pvalue_aggregation="average",
    ).statistics.set_index(["source", "target"])

    assert maximum.loc[("a", "x"), "disparity_pvalue"] == pytest.approx(0.25)
    assert average.loc[("a", "x"), "disparity_pvalue"] == pytest.approx(0.225)


def test_directed_disparity_scores_reciprocal_arcs_independently() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b", weight=4.0)
    graph.add_edge("b", "a", weight=2.0)
    graph.add_edge("a", "c", weight=1.0)
    graph.add_edge("c", "a", weight=1.0)

    rows = nb.score(
        graph, method="disparity", leaf_policy="ignore"
    ).statistics.set_index(["source", "target"])

    assert len(rows) == 4
    assert rows.loc[("a", "b"), "disparity_pvalue"] == pytest.approx(0.2)
    assert rows.loc[("b", "a"), "disparity_pvalue"] == pytest.approx(1 / 3)


def test_directed_disparity_significance_filter_keeps_significant_arcs() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "x", weight=4.0)
    graph.add_edge("a", "y", weight=1.0)
    graph.add_edge("b", "x", weight=1.0)
    graph.add_edge("c", "x", weight=3.0)

    result = (
        nb.pipeline()
        .score("disparity", leaf_policy="ignore")
        .filter("significance", alpha=0.21, drop_isolates=True)
        .run(graph)
    )

    assert result.graph.is_directed()
    assert set(result.graph.edges) == {("a", "x")}


def test_directed_disparity_leaf_policy_uses_non_leaf_arc_endpoint() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "x", weight=4.0)
    graph.add_edge("a", "y", weight=1.0)

    ignored = nb.score(
        graph, method="disparity", leaf_policy="ignore"
    ).statistics.set_index(["source", "target"])
    zeroed = nb.score(
        graph,
        method="disparity",
        leaf_policy="zero",
    ).statistics.set_index(["source", "target"])

    assert ignored.loc[("a", "x"), "disparity_pvalue"] == pytest.approx(0.2)
    assert ignored.loc[("a", "y"), "disparity_pvalue"] == pytest.approx(0.8)
    assert zeroed["disparity_pvalue"].tolist() == [0.0, 0.0]


def test_disparity_leaf_policy_ignore_uses_non_leaf_endpoint() -> None:
    graph = nx.Graph()
    graph.add_edge("center", "leaf_a", weight=3.0)
    graph.add_edge("center", "leaf_b", weight=1.0)

    ignore_leaf = nb.score(
        graph, method="disparity", weight="weight", leaf_policy="ignore"
    )
    zero_leaf = nb.score(
        graph,
        method="disparity",
        weight="weight",
        leaf_policy="zero",
    )

    assert zero_leaf.parameters["leaf_policy"] == "zero"
    assert ignore_leaf.statistics["disparity_pvalue"].tolist() == pytest.approx(
        [0.25, 0.75]
    )
    assert zero_leaf.statistics["disparity_pvalue"].tolist() == [0.0, 0.0]


def test_disparity_rejects_non_positive_weights() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=0.0)

    with pytest.raises(nb.ValidationError, match="must be positive"):
        nb.score(graph, method="disparity", weight="weight")


def test_disparity_default_filter_resolves_to_significance() -> None:
    graph = nx.Graph()
    graph.add_edge("center", "leaf_a", weight=3.0)
    graph.add_edge("center", "leaf_b", weight=1.0)

    result = (
        nb.pipeline()
        .score("disparity", weight="weight", leaf_policy="ignore")
        .filter("default")
        .run(graph)
    )

    assert result.selection.parameters["strategy"] == "significance"
    assert result.selection.parameters["alpha"] == 0.05
    assert sorted(result.graph.edges()) == []


def test_disparity_significance_filter_uses_primary_statistic_by_default() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("b", "c", weight=1.0)
    graph.add_edge("b", "d", weight=2.0)

    result = (
        nb.pipeline()
        .score("disparity", leaf_policy="ignore")
        .filter("significance", alpha=0.3, drop_isolates=False)
        .run(graph)
    )

    assert result.selection.statistic == "disparity_pvalue"
    assert result.selection.parameters["statistic"] == "disparity_pvalue"
    assert sorted(result.graph.edges()) == [("a", "b")]


@pytest.mark.parametrize("method", ["disparity", "lans"])
def test_directed_out_and_in_aggregation_use_one_arc_end(method: str) -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("a", "c", weight=1.0)
    graph.add_edge("b", "c", weight=2.0)
    graph.add_edge("d", "c", weight=5.0)
    graph.add_edge("d", "b", weight=1.0)

    def table(aggregation: str) -> object:
        return nb.score(
            graph, method=method, pvalue_aggregation=aggregation
        ).statistics.set_index(["source", "target"])

    column = f"{method}_pvalue"
    outgoing = table("out")
    incoming = table("in")
    both_or = table("min")
    both_and = table("max")
    assert outgoing[column].tolist() == pytest.approx(
        outgoing[f"{method}_source_pvalue"].tolist()
    )
    assert incoming[column].tolist() == pytest.approx(
        incoming[f"{method}_target_pvalue"].tolist()
    )
    for key in outgoing.index:
        pair = (outgoing.loc[key, column], incoming.loc[key, column])
        assert both_or.loc[key, column] == pytest.approx(min(pair))
        assert both_and.loc[key, column] == pytest.approx(max(pair))


@pytest.mark.parametrize("method", ["disparity", "lans"])
@pytest.mark.parametrize("aggregation", ["out", "in"])
def test_out_and_in_aggregation_reject_undirected_graphs(
    method: str, aggregation: str
) -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("b", "c", weight=1.0)

    with pytest.raises(nb.ConfigurationError, match="needs a directed graph"):
        nb.score(graph, method=method, pvalue_aggregation=aggregation)


@pytest.mark.parametrize("aggregation", ["out", "in"])
def test_out_and_in_aggregation_ignore_leaf_gives_one(aggregation: str) -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b", weight=1.0)

    result = nb.score(
        graph,
        method="disparity",
        pvalue_aggregation=aggregation,
        leaf_policy="ignore",
    )

    assert result.statistics["disparity_pvalue"].tolist() == [1.0]
