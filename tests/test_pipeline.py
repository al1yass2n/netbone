from __future__ import annotations

import json

import networkx as nx
import pytest

import netbone as nb


def test_pipeline_is_immutable() -> None:
    base = nb.pipeline()
    scored = base.score("edge_weight", weight="weight")
    filtered = scored.filter(
        "threshold",
        value=2.0,
        operator="greater_equal",
    )

    assert base.method_name is None
    assert scored.filter_name is None
    assert filtered.method_name == "edge_weight"
    assert filtered.filter_name == "threshold"


def test_pipeline_run_returns_result_with_summary_and_to_dict() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=2)
    graph.add_edge("b", "c", weight=1)

    result = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("threshold", value=2, operator="greater_equal")
        .run(graph)
    )

    assert sorted(result.graph.edges()) == [("a", "b")]
    assert result.summary() == {
        "method": "edge_weight",
        "filter": "threshold",
        "original_node_count": 3,
        "original_edge_count": 2,
        "backbone_node_count": 3,
        "backbone_edge_count": 1,
        "node_fraction": 1.0,
        "edge_fraction": 0.5,
        "selected_edge_count": 1,
        "drop_isolates": False,
        "isolated_node_count": 1,
        "connected_component_count": 2,
    }
    assert result.to_dict()["summary"]["edge_fraction"] == 0.5


def test_pipeline_from_dict_round_trips_registered_configuration() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=2)
    graph.add_edge("b", "c", weight=1)

    original = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("threshold", value=2.0, operator="greater_equal")
    )
    saved_config = json.loads(json.dumps(original.to_dict()))
    restored = nb.Pipeline.from_dict(saved_config)
    result = restored.run(graph)

    assert saved_config["schema_version"] == "1.0"
    assert saved_config["package"]["name"] == "netbone"
    assert restored == original
    assert restored.to_dict() == original.to_dict()
    assert sorted(result.graph.edges()) == [("a", "b")]
    assert result.pipeline_config == original.to_dict()


def test_pipeline_from_dict_accepts_legacy_configuration_without_metadata() -> None:
    restored = nb.Pipeline.from_dict(
        {
            "method": {"name": "edge_weight", "parameters": {"weight": "weight"}},
            "filter": {
                "name": "threshold",
                "parameters": {"value": 2.0, "operator": "greater_equal"},
            },
        }
    )

    assert restored.method_name == "edge_weight"
    assert restored.filter_name == "threshold"
    assert restored.to_dict()["schema_version"] == "1.0"


def test_pipeline_json_file_round_trips_registered_configuration(tmp_path) -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=2)
    graph.add_edge("b", "c", weight=1)
    path = tmp_path / "pipeline.json"

    original = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("threshold", value=2.0, operator="greater_equal")
    )

    original.to_json(path)
    restored = nb.Pipeline.from_json(path)
    result = restored.run(graph)

    assert json.loads(path.read_text(encoding="utf-8")) == original.to_dict()
    assert restored == original
    assert sorted(result.graph.edges()) == [("a", "b")]


def test_pipeline_from_dict_rejects_custom_filter_callable() -> None:
    def keep_everything(*_args: object, **_parameters: object) -> nb.Selection:
        raise AssertionError("custom filter should not be called")

    config = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter(keep_everything)
        .to_dict()
    )

    with pytest.raises(nb.ConfigurationError, match="custom filter callables"):
        nb.Pipeline.from_dict(config)


def test_pipeline_to_json_rejects_custom_filter_callable(tmp_path) -> None:
    def keep_everything(*_args: object, **_parameters: object) -> nb.Selection:
        raise AssertionError("custom filter should not be called")

    pipeline = (
        nb.pipeline().score("edge_weight", weight="weight").filter(keep_everything)
    )

    with pytest.raises(nb.ConfigurationError, match="custom filter callables"):
        pipeline.to_json(tmp_path / "pipeline.json")


def test_pipeline_from_dict_validates_config_shape() -> None:
    with pytest.raises(nb.ConfigurationError, match="method config must be a mapping"):
        nb.Pipeline.from_dict({"method": "edge_weight", "filter": None})

    with pytest.raises(nb.ConfigurationError, match="parameter names must be strings"):
        nb.Pipeline.from_dict(
            {
                "method": {"name": "edge_weight", "parameters": {1: "weight"}},
                "filter": None,
            }
        )


def test_pipeline_from_json_reports_missing_and_invalid_files(tmp_path) -> None:
    missing = tmp_path / "missing.json"
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{", encoding="utf-8")

    with pytest.raises(nb.ValidationError, match="does not exist"):
        nb.Pipeline.from_json(missing)

    with pytest.raises(nb.ValidationError, match="not valid JSON"):
        nb.Pipeline.from_json(invalid)


def test_pipeline_rejects_unknown_method_and_filter() -> None:
    with pytest.raises(nb.ConfigurationError, match="Unknown scoring method"):
        nb.pipeline().score("unknown_method")

    with pytest.raises(nb.ConfigurationError, match="Unknown filter strategy"):
        nb.pipeline().filter("unknown_filter")


def test_pipeline_reports_missing_configuration() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")

    with pytest.raises(nb.ConfigurationError, match="no scoring method"):
        nb.pipeline().compute(graph)

    with pytest.raises(nb.ConfigurationError, match="no filter strategy"):
        nb.pipeline().score("edge_weight").run(graph)


def test_threshold_filter_reports_missing_required_parameters() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1)

    with pytest.raises(nb.ConfigurationError, match="missing required parameter"):
        nb.pipeline().score("edge_weight", weight="weight").filter(
            "threshold",
            value=1,
        ).run(graph)


def test_filter_scores_rejects_method_result_from_different_graph() -> None:
    scored_graph = nx.Graph()
    scored_graph.add_edge("a", "b", weight=2)

    target_graph = nx.Graph()
    target_graph.add_edge("x", "y", weight=2)

    method_result = nb.score(scored_graph, weight="weight")

    with pytest.raises(nb.CompatibilityError, match="do not match"):
        nb.filter_scores(
            target_graph,
            method_result,
            value=1,
            operator="greater_equal",
        )


def test_filter_scores_rejects_different_graph_when_selection_is_empty() -> None:
    scored_graph = nx.Graph()
    scored_graph.add_edge("a", "b", weight=2)

    target_graph = nx.Graph()
    target_graph.add_edge("x", "y", weight=2)

    method_result = nb.score(scored_graph, weight="weight")

    with pytest.raises(nb.CompatibilityError, match="do not match"):
        nb.filter_scores(
            target_graph,
            method_result,
            value=3,
            operator="greater_equal",
        )


def test_filter_scores_rejects_node_method_result_from_different_graph() -> None:
    scored_graph = nx.Graph()
    scored_graph.add_edge("a", "b")

    target_graph = nx.Graph()
    target_graph.add_edge("x", "y")

    method_result = nb.score(scored_graph, method="node_degree")

    with pytest.raises(nb.CompatibilityError, match="do not match"):
        nb.filter_scores(
            target_graph,
            method_result,
            value=1,
            operator="greater_equal",
        )


def test_filter_scores_rejects_incomplete_method_statistics() -> None:
    scored_graph = nx.Graph()
    scored_graph.add_edge("a", "b", weight=2)

    target_graph = nx.Graph()
    target_graph.add_edge("a", "b", weight=2)
    target_graph.add_edge("b", "c", weight=1)

    method_result = nb.score(scored_graph, weight="weight")

    with pytest.raises(nb.CompatibilityError, match="do not cover"):
        nb.filter_scores(
            target_graph,
            method_result,
            value=3,
            operator="greater_equal",
        )


def test_pipeline_defaults_threshold_statistic_to_method_primary_statistic() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=2)
    graph.add_edge("b", "c", weight=1)

    result = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("threshold", value=2, operator="greater_equal")
        .run(graph)
    )

    assert result.selection.statistic == "score"
    assert result.selection.parameters["statistic"] == "score"
    assert sorted(result.graph.edges()) == [("a", "b")]


def test_pipeline_to_json_rejects_non_json_parameters(tmp_path) -> None:
    pipeline = (
        nb.pipeline()
        .score("edge_weight", weight=object())
        .filter("threshold", value=1, operator="greater_equal")
    )

    with pytest.raises(nb.ConfigurationError, match="cannot be serialized"):
        pipeline.to_json(tmp_path / "pipeline.json")
