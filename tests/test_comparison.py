from __future__ import annotations

import networkx as nx
import pandas as pd
import pytest

import netbone as nb


def _graph() -> nx.Graph:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=4.0)
    graph.add_edge("b", "c", weight=2.0)
    graph.add_edge("c", "d", weight=1.0)
    return graph


def _result(value: float) -> nb.BackboneResult:
    return (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("threshold", value=value, operator="greater_equal")
        .run(_graph())
    )


def _edge_result_like(
    result: nb.BackboneResult,
    *,
    values: list[object],
    method_name: str,
    primary_statistic: str,
    output_type: str,
    preferred_direction: str,
) -> nb.BackboneResult:
    statistics = result.method_result.statistics[
        ["edge_id", "source_id", "target_id", "source", "target"]
    ].copy()
    statistics[primary_statistic] = values
    method_result = nb.MethodResult(
        method_name=method_name,
        target="edge",
        statistics=statistics,
        primary_statistic=primary_statistic,
        output_type=output_type,
        preferred_direction=preferred_direction,
        parameters={},
        metadata={"name": method_name},
    )
    selected_ids = tuple(int(edge_id) for edge_id in statistics["edge_id"].tolist())
    selection = nb.Selection(
        target="edge",
        selected_ids=selected_ids,
        rejected_ids=(),
        statistic=primary_statistic,
        parameters={"strategy": "test_filter"},
        mask=pd.Series([True] * len(statistics)),
    )
    return nb.BackboneResult(
        graph=result.graph.copy(),
        original_graph=result.original_graph.copy(),
        method_result=method_result,
        selection=selection,
        pipeline_config={},
        context=None,
    )


def _node_target_result_like(result: nb.BackboneResult) -> nb.BackboneResult:
    statistics = pd.DataFrame(
        {
            "node_id": [0, 1, 2, 3],
            "node": ["a", "b", "c", "d"],
            "node_score": [4.0, 3.0, 2.0, 1.0],
        }
    )
    method_result = nb.MethodResult(
        method_name="node_score",
        target="node",
        statistics=statistics,
        primary_statistic="node_score",
        output_type="score",
        preferred_direction="higher",
        parameters={},
        metadata={"name": "node_score"},
    )
    selection = nb.Selection(
        target="node",
        selected_ids=(0, 1, 2, 3),
        rejected_ids=(),
        statistic="node_score",
        parameters={"strategy": "test_node_filter"},
        mask=pd.Series([True, True, True, True]),
    )
    return nb.BackboneResult(
        graph=result.graph.copy(),
        original_graph=result.original_graph.copy(),
        method_result=method_result,
        selection=selection,
        pipeline_config={},
        context=None,
    )


def test_compare_returns_tidy_single_metric_table() -> None:
    comparison = nb.compare({"strict": _result(4.0), "loose": _result(2.0)})

    table = comparison.table(metrics=["edge_count", "edge_retention"])
    weight_retention = comparison.metric("weight_retention")

    assert table.to_dict(orient="records") == [
        {
            "result": "strict",
            "metric": "edge_count",
            "value": 1,
            "status": "ok",
            "explanation": "",
        },
        {
            "result": "strict",
            "metric": "edge_retention",
            "value": 1 / 3,
            "status": "ok",
            "explanation": "",
        },
        {
            "result": "loose",
            "metric": "edge_count",
            "value": 2,
            "status": "ok",
            "explanation": "",
        },
        {
            "result": "loose",
            "metric": "edge_retention",
            "value": 2 / 3,
            "status": "ok",
            "explanation": "",
        },
    ]
    assert weight_retention["value"].tolist() == pytest.approx([4 / 7, 6 / 7])


def test_single_metric_errors_return_invalid_rows() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight="not numeric")

    result = (
        nb.pipeline()
        .score("edge_weight", weight=None)
        .filter("threshold", value=0.5, operator="greater_equal")
        .run(graph)
    )

    table = nb.compare({"invalid_weight": result}).metric("weight_retention")

    assert table.loc[0, "status"] == "invalid"
    assert table.loc[0, "value"] is None
    assert (
        "weight_retention metric requires finite numeric" in table.loc[0, "explanation"]
    )


def test_weight_retention_uses_method_weight_parameter() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", strength=4.0)
    graph.add_edge("b", "c", strength=2.0)
    graph.add_edge("c", "d", strength=1.0)

    result = (
        nb.pipeline()
        .score("edge_weight", weight="strength")
        .filter("threshold", value=2.0, operator="greater_equal")
        .run(graph)
    )

    table = nb.compare({"strength": result}).metric("weight_retention")

    assert table.loc[0, "status"] == "ok"
    assert table.loc[0, "value"] == pytest.approx(6 / 7)


def test_weight_retention_rejects_negative_weights() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=-1.0)

    result = (
        nb.pipeline()
        .score("edge_weight", weight=None)
        .filter("threshold", value=0.5, operator="greater_equal")
        .run(graph)
    )

    table = nb.compare({"negative_weight": result}).metric("weight_retention")

    assert table.loc[0, "status"] == "invalid"
    assert "non-negative" in table.loc[0, "explanation"]


def test_compare_returns_pairwise_overlap_metrics() -> None:
    comparison = nb.compare({"strict": _result(4.0), "loose": _result(2.0)})

    table = comparison.pairwise(
        metrics=[
            "edge_overlap",
            "edge_jaccard",
            "edge_overlap_coefficient",
        ]
    )

    assert table[["metric", "value", "status"]].to_dict(orient="records") == [
        {"metric": "edge_overlap", "value": 1, "status": "ok"},
        {"metric": "edge_jaccard", "value": 0.5, "status": "ok"},
        {"metric": "edge_overlap_coefficient", "value": 1.0, "status": "ok"},
    ]
    assert table["same_original_graph"].tolist() == [True, True, True]
    assert table["same_original_topology"].tolist() == [True, True, True]
    assert table["same_target"].tolist() == [True, True, True]


def test_pairwise_comparison_reports_different_original_graphs_as_invalid() -> None:
    other = nx.Graph()
    other.add_edge("x", "y", weight=1.0)
    left = _result(4.0)
    right = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("threshold", value=1.0, operator="greater_equal")
        .run(other)
    )

    table = nb.compare({"left": left, "right": right}).pairwise(
        metrics=["edge_jaccard"]
    )

    assert table.loc[0, "status"] == "invalid"
    assert not table.loc[0, "same_original_graph"]
    assert not table.loc[0, "same_original_topology"]
    assert "same original graph" in table.loc[0, "explanation"]


def test_pairwise_overlap_allows_same_topology_with_different_weights() -> None:
    left_graph = _graph()
    right_graph = _graph()
    right_graph["a"]["b"]["weight"] = 40.0

    pipeline = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("fraction", fraction=1.0)
    )

    table = nb.compare(
        {
            "left": pipeline.run(left_graph),
            "right": pipeline.run(right_graph),
        }
    ).pairwise(metrics=["edge_jaccard"])

    assert table.loc[0, "status"] == "ok"
    assert table.loc[0, "same_original_topology"]
    assert not table.loc[0, "same_original_graph"]
    assert table.loc[0, "value"] == pytest.approx(1.0)


def test_spearman_rejects_same_topology_with_different_attributes() -> None:
    left_graph = _graph()
    right_graph = _graph()
    right_graph["a"]["b"]["weight"] = 40.0

    pipeline = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("fraction", fraction=1.0)
    )

    table = nb.compare(
        {
            "left": pipeline.run(left_graph),
            "right": pipeline.run(right_graph),
        }
    ).spearman()

    assert table.loc[0, "status"] == "invalid"
    assert table.loc[0, "same_original_topology"]
    assert not table.loc[0, "same_original_graph"]
    assert "same attributed original graph" in table.loc[0, "explanation"]


def test_pairwise_overlap_allows_different_method_targets() -> None:
    edge_target = _result(4.0)
    node_target = _node_target_result_like(edge_target)

    table = nb.compare(
        {"edge_target": edge_target, "node_target": node_target}
    ).pairwise(metrics=["edge_jaccard"])

    assert table.loc[0, "status"] == "ok"
    assert not table.loc[0, "same_target"]
    assert table.loc[0, "value"] == pytest.approx(1.0)


def test_score_alignment_and_spearman_for_compatible_results() -> None:
    graph = _graph()
    left = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("threshold", value=4.0, operator="greater_equal")
        .run(graph)
    )
    right = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("fraction", fraction=2 / 3)
        .run(graph)
    )

    comparison = nb.compare({"threshold": left, "fraction": right})
    alignment = comparison.score_alignment("threshold", "fraction")
    spearman = comparison.spearman()

    assert alignment[["edge_id_a", "edge_id_b", "value_a", "value_b"]].to_dict(
        orient="records"
    ) == [
        {"edge_id_a": 0, "edge_id_b": 0, "value_a": 4.0, "value_b": 4.0},
        {"edge_id_a": 1, "edge_id_b": 1, "value_a": 2.0, "value_b": 2.0},
        {"edge_id_a": 2, "edge_id_b": 2, "value_a": 1.0, "value_b": 1.0},
    ]
    assert alignment[
        [
            "output_type_a",
            "output_type_b",
            "preferred_direction_a",
            "preferred_direction_b",
            "importance_rank_a",
            "importance_rank_b",
        ]
    ].to_dict(orient="records") == [
        {
            "output_type_a": "score",
            "output_type_b": "score",
            "preferred_direction_a": "higher",
            "preferred_direction_b": "higher",
            "importance_rank_a": 3.0,
            "importance_rank_b": 3.0,
        },
        {
            "output_type_a": "score",
            "output_type_b": "score",
            "preferred_direction_a": "higher",
            "preferred_direction_b": "higher",
            "importance_rank_a": 2.0,
            "importance_rank_b": 2.0,
        },
        {
            "output_type_a": "score",
            "output_type_b": "score",
            "preferred_direction_a": "higher",
            "preferred_direction_b": "higher",
            "importance_rank_a": 1.0,
            "importance_rank_b": 1.0,
        },
    ]
    assert spearman.loc[0, "metric"] == "score_spearman"
    assert spearman.loc[0, "value"] == pytest.approx(1.0)
    assert spearman.loc[0, "status"] == "ok"


def test_score_alignment_uses_original_edge_identity_not_internal_edge_ids() -> None:
    first = nx.Graph()
    first.add_edge("a", "b", weight=10.0)
    first.add_edge("b", "c", weight=1.0)
    first.add_edge("a", "c", weight=2.0)

    second = nx.Graph()
    second.add_edge("b", "c", weight=1.0)
    second.add_edge("a", "c", weight=2.0)
    second.add_edge("a", "b", weight=10.0)

    pipeline = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("fraction", fraction=1.0)
    )
    comparison = nb.compare(
        {"first": pipeline.run(first), "second": pipeline.run(second)}
    )
    alignment = comparison.score_alignment("first", "second")
    spearman = comparison.spearman()

    assert alignment[
        [
            "source_a",
            "target_a",
            "edge_id_a",
            "source_b",
            "target_b",
            "edge_id_b",
            "value_a",
            "value_b",
        ]
    ].to_dict(orient="records") == [
        {
            "source_a": "a",
            "target_a": "b",
            "edge_id_a": 0,
            "source_b": "b",
            "target_b": "a",
            "edge_id_b": 1,
            "value_a": 10.0,
            "value_b": 10.0,
        },
        {
            "source_a": "a",
            "target_a": "c",
            "edge_id_a": 1,
            "source_b": "c",
            "target_b": "a",
            "edge_id_b": 2,
            "value_a": 2.0,
            "value_b": 2.0,
        },
        {
            "source_a": "b",
            "target_a": "c",
            "edge_id_a": 2,
            "source_b": "b",
            "target_b": "c",
            "edge_id_b": 0,
            "value_a": 1.0,
            "value_b": 1.0,
        },
    ]
    assert spearman.loc[0, "status"] == "ok"
    assert spearman.loc[0, "value"] == pytest.approx(1.0)


def test_directed_comparison_keeps_reciprocal_arcs_distinct() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("b", "a", weight=1.0)
    graph.add_edge("a", "c", weight=1.0)
    significance = (
        nb.pipeline()
        .score("lans", leaf_policy="ignore")
        .filter("significance", alpha=0.6)
        .run(graph)
    )
    fraction = (
        nb.pipeline()
        .score("lans", leaf_policy="ignore")
        .filter(
            "fraction",
            fraction=1 / 3,
            direction="lower",
            tie_policy="exact_stable",
        )
        .run(graph)
    )

    comparison = nb.compare({"significance": significance, "fraction": fraction})
    pairwise = comparison.pairwise(metrics=["edge_jaccard"])
    alignment = comparison.score_alignment("significance", "fraction")

    assert pairwise.iloc[0]["value"] == pytest.approx(0.5)
    assert len(alignment) == 3
    assert set(alignment["edge_key"]) == {
        ("a", "b"),
        ("b", "a"),
        ("a", "c"),
    }


def test_spearman_compares_score_to_pvalue_by_importance_order() -> None:
    score_result = _result(0.0)
    pvalue_result = _edge_result_like(
        score_result,
        values=[0.01, 0.10, 0.30],
        method_name="pvalue_method",
        primary_statistic="pvalue",
        output_type="pvalue",
        preferred_direction="lower",
    )

    comparison = nb.compare({"score": score_result, "pvalue": pvalue_result})
    alignment = comparison.score_alignment("score", "pvalue")
    table = comparison.spearman()

    assert alignment[
        [
            "edge_id_a",
            "edge_id_b",
            "value_a",
            "value_b",
            "output_type_a",
            "output_type_b",
            "importance_rank_a",
            "importance_rank_b",
        ]
    ].to_dict(orient="records") == [
        {
            "edge_id_a": 0,
            "edge_id_b": 0,
            "value_a": 4.0,
            "value_b": 0.01,
            "output_type_a": "score",
            "output_type_b": "pvalue",
            "importance_rank_a": 3.0,
            "importance_rank_b": 3.0,
        },
        {
            "edge_id_a": 1,
            "edge_id_b": 1,
            "value_a": 2.0,
            "value_b": 0.10,
            "output_type_a": "score",
            "output_type_b": "pvalue",
            "importance_rank_a": 2.0,
            "importance_rank_b": 2.0,
        },
        {
            "edge_id_a": 2,
            "edge_id_b": 2,
            "value_a": 1.0,
            "value_b": 0.30,
            "output_type_a": "score",
            "output_type_b": "pvalue",
            "importance_rank_a": 1.0,
            "importance_rank_b": 1.0,
        },
    ]
    assert table.loc[0, "status"] == "ok"
    assert table.loc[0, "value"] == pytest.approx(1.0)


def test_spearman_compares_pvalue_to_pvalue_by_importance_order() -> None:
    base = _result(0.0)
    left = _edge_result_like(
        base,
        values=[0.01, 0.10, 0.30],
        method_name="left_pvalue",
        primary_statistic="pvalue",
        output_type="pvalue",
        preferred_direction="lower",
    )
    right = _edge_result_like(
        base,
        values=[0.02, 0.20, 0.40],
        method_name="right_pvalue",
        primary_statistic="pvalue",
        output_type="pvalue",
        preferred_direction="lower",
    )

    table = nb.compare({"left": left, "right": right}).spearman()

    assert table.loc[0, "status"] == "ok"
    assert table.loc[0, "value"] == pytest.approx(1.0)


def test_spearman_reports_non_numeric_primary_statistics_as_invalid() -> None:
    score_result = _result(0.0)
    non_numeric = _edge_result_like(
        score_result,
        values=[4.0, "bad", 1.0],
        method_name="bad_score",
        primary_statistic="score",
        output_type="score",
        preferred_direction="higher",
    )

    table = nb.compare({"score": score_result, "bad": non_numeric}).spearman()

    assert table.loc[0, "status"] == "invalid"
    assert "finite numeric primary statistics" in table.loc[0, "explanation"]


def test_spearman_reports_constant_importance_ranks_as_undefined() -> None:
    score_result = _result(0.0)
    constant = _edge_result_like(
        score_result,
        values=[1.0, 1.0, 1.0],
        method_name="constant_score",
        primary_statistic="score",
        output_type="score",
        preferred_direction="higher",
    )

    table = nb.compare({"score": score_result, "constant": constant}).spearman()

    assert table.loc[0, "status"] == "undefined"
    assert "constant ranks" in table.loc[0, "explanation"]


def test_spearman_reports_different_targets_as_invalid() -> None:
    edge_target = _result(4.0)
    node_target = _node_target_result_like(edge_target)

    table = nb.compare(
        {"edge_target": edge_target, "node_target": node_target}
    ).spearman()

    assert table.loc[0, "status"] == "invalid"
    assert not table.loc[0, "same_target"]
    assert "same result target" in table.loc[0, "explanation"]


def test_metric_discovery_lists_registered_metrics() -> None:
    assert "edge_jaccard" in nb.list_metrics(scope="pairwise")
    assert "score_spearman" in nb.list_metrics(scope="pairwise")
    assert nb.describe_metric("edge_retention")["scope"] == "single"
