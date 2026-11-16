from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb


def _graph() -> nx.Graph:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=4.0)
    graph.add_edge("b", "c", weight=2.0)
    graph.add_edge("c", "d", weight=1.0)
    return graph


def test_filter_sweep_reuses_scores_when_only_filter_changes() -> None:
    result = (
        nb.sweep(_graph())
        .score("edge_weight", weight="weight")
        .filter("threshold", operator="greater_equal")
        .vary_filter(value=[4.0, 2.0])
        .measure(["edge_count"])
        .run()
    )

    table = result.table()

    assert result.score_cache_misses == 1
    assert result.score_cache_hits == 1
    assert table[["pipeline_name", "metric", "value", "status"]].to_dict(
        orient="records"
    ) == [
        {
            "pipeline_name": "edge_weight_threshold_value_4p0",
            "metric": "edge_count",
            "value": 1,
            "status": "ok",
        },
        {
            "pipeline_name": "edge_weight_threshold_value_2p0",
            "metric": "edge_count",
            "value": 2,
            "status": "ok",
        },
    ]
    assert table["varied_parameter"].tolist() == ["value", "value"]
    assert table["parameter_value"].tolist() == [4.0, 2.0]
    assert result.runs["score_cache_hit"].tolist() == [False, True]


def test_fraction_sweep_uses_fraction_filter_tie_policies() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=2.0)
    graph.add_edge("b", "c", weight=2.0)
    graph.add_edge("c", "d", weight=1.0)

    result = (
        nb.sweep(graph)
        .score("edge_weight", weight="weight")
        .filter("fraction", tie_policy="include_all_ties")
        .vary_filter(fraction=[1 / 3, 1.0])
        .measure(["edge_count"])
        .run()
    )

    table = result.table()

    assert result.score_cache_misses == 1
    assert result.score_cache_hits == 1
    assert table["value"].tolist() == [2, 3]
    assert "retained additional tied items" in table.loc[0, "warning"]


def test_method_parameter_sweep_computes_distinct_scores() -> None:
    result = (
        nb.sweep(_graph())
        .score("disparity", weight="weight")
        .filter("significance", alpha=0.6)
        .vary_method(pvalue_aggregation=["min", "max"])
        .measure(["edge_count"])
        .run()
    )

    table = result.table()

    assert result.score_cache_misses == 2
    assert result.score_cache_hits == 0
    assert table["pipeline_name"].tolist() == [
        "disparity_significance_pvalue_aggregation_min",
        "disparity_significance_pvalue_aggregation_max",
    ]
    assert table["varied_parameter"].tolist() == [
        "pvalue_aggregation",
        "pvalue_aggregation",
    ]
    assert table["status"].tolist() == ["ok", "ok"]
    assert set(result.results) == set(table["pipeline_name"])


def test_grid_sweep_supports_multiple_methods_with_one_filter() -> None:
    result = (
        nb.sweep(_graph())
        .grid(
            methods={
                "edge_weight": {"weight": "weight"},
                "link_salience": {"weight": "weight"},
                "disparity": {"weight": "missing"},
            },
            filters={"fraction": {"fraction": 2 / 3}},
        )
        .measure(["edge_count"])
        .run()
    )

    table = result.table()
    runs = result.runs
    failures = result.failures

    assert len(result.results) == 2
    assert runs[["method", "filter", "status"]].to_dict(orient="records") == [
        {"method": "edge_weight", "filter": "fraction", "status": "ok"},
        {"method": "link_salience", "filter": "fraction", "status": "ok"},
        {"method": "disparity", "filter": "fraction", "status": "failed"},
    ]
    assert failures["method"].tolist() == ["disparity"]
    assert "missing required weight attribute" in failures.loc[2, "explanation"]
    assert table.loc[table["method"] == "disparity", "status"].tolist() == ["failed"]


def test_grid_sweep_crosses_methods_and_filters_with_failure_isolation() -> None:
    result = (
        nb.sweep(_graph())
        .grid(
            methods={
                "edge_weight": {"weight": "weight"},
                "disparity": {
                    "weight": "weight",
                    "pvalue_aggregation": ["min", "max"],
                },
            },
            filters={
                "fraction": {"fraction": [0.5, 1.0]},
                "significance": {"alpha": 0.6},
            },
        )
        .measure(["edge_count"])
        .run()
    )

    runs = result.runs
    failures = result.failures

    assert len(runs) == 9
    assert len(result.results) == 8
    assert runs["pipeline_name"].is_unique
    assert result.score_cache_misses == 3
    assert result.score_cache_hits == 6
    assert runs["status"].value_counts().to_dict() == {"ok": 8, "failed": 1}
    assert failures[["method", "filter", "score_cache_hit"]].to_dict(
        orient="records"
    ) == [
        {
            "method": "edge_weight",
            "filter": "significance",
            "score_cache_hit": True,
        }
    ]
    assert "requires method output_type 'pvalue'" in failures.iloc[0]["explanation"]
    assert runs.iloc[0]["varied_parameters"] == {
        "method": "edge_weight",
        "filter": "fraction",
        "method_parameters": {"weight": "weight"},
        "filter_parameters": {"fraction": 0.5},
    }
    table = result.table()
    assert table.loc[table["status"] == "failed", "metric"].isna().tolist() == [True]


def test_sweep_plot_data_returns_copied_dataframes() -> None:
    result = (
        nb.sweep(_graph())
        .score("edge_weight", weight="weight")
        .filter("threshold", value=2.0, operator="greater_equal")
        .measure(["edge_count"])
        .run()
    )

    plot_data = result.plot_data
    plot_data["sweep_metrics"].loc[0, "value"] = 999

    assert set(plot_data) == {"sweep_metrics", "sweep_runs"}
    assert result.table().loc[0, "value"] == 2


def test_sweep_records_invalid_metric_rows_without_aborting() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight="not numeric")

    result = (
        nb.sweep(graph)
        .score("edge_weight", weight=None)
        .filter("threshold", value=0.5, operator="greater_equal")
        .measure(["edge_count", "weight_retention"])
        .run()
    )

    table = result.table()

    assert result.runs.loc[0, "status"] == "ok"
    assert table[["metric", "status"]].to_dict(orient="records") == [
        {"metric": "edge_count", "status": "ok"},
        {"metric": "weight_retention", "status": "invalid"},
    ]
    assert table.loc[0, "value"] == 1
    assert table.loc[1, "value"] != table.loc[1, "value"]
    assert (
        "weight_retention metric requires finite numeric" in table.loc[1, "explanation"]
    )
    assert result.to_dict()["table"][1]["value"] is None
    assert set(result.results) == {"edge_weight_threshold_pipeline"}


def test_sweep_rejects_missing_configuration_and_empty_inputs() -> None:
    graph = _graph()

    with pytest.raises(nb.ConfigurationError, match="requires a scoring method"):
        nb.sweep(graph).vary_filter("threshold", value=[1.0])

    with pytest.raises(nb.ConfigurationError, match="requires a filter"):
        nb.sweep(graph).score("edge_weight").vary_method(weight=["weight"])

    with pytest.raises(nb.ConfigurationError, match="at least one metric"):
        nb.sweep(graph).measure([])

    with pytest.raises(nb.ConfigurationError, match="not a string"):
        nb.sweep(graph).measure("edge_count")

    with pytest.raises(nb.ConfigurationError, match="must contain at least one value"):
        (
            nb.sweep(graph)
            .score("edge_weight", weight="weight")
            .filter("threshold", operator="greater_equal")
            .vary_filter(value=[])
        )

    with pytest.raises(nb.ConfigurationError, match="at least one method"):
        nb.sweep(graph).grid(methods={}, filters={"fraction": {}})

    with pytest.raises(nb.ConfigurationError, match="at least one filter"):
        nb.sweep(graph).grid(methods={"edge_weight": {}}, filters={})

    with pytest.raises(nb.ConfigurationError, match="filters must be a mapping"):
        nb.sweep(graph).grid(methods={"edge_weight": {}}, filters="fraction")

    with pytest.raises(nb.ConfigurationError, match="Filter grid"):
        nb.sweep(graph).grid(
            methods={"edge_weight": {}},
            filters={"fraction": 0.5},
        )
