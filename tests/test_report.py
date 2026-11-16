from __future__ import annotations

import builtins
import json

import networkx as nx
import pytest

import netbone as nb


def _graph() -> nx.Graph:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=2.0)
    graph.add_edge("b", "c", weight=1.0)
    return graph


def _threshold_result(value: float) -> nb.BackboneResult:
    return (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("threshold", value=value, operator="greater_equal")
        .run(_graph())
    )


def test_report_backbone_result_to_dict_and_markdown() -> None:
    result = _threshold_result(2.0)

    report = nb.report(result)
    payload = report.to_dict()
    markdown = report.to_markdown()

    assert isinstance(report, nb.Report)
    assert payload["subject_type"] == "backbone_result"
    assert payload["summary"]["method"] == "edge_weight"
    assert payload["sections"]["method"]["name"] == "edge_weight"
    assert payload["sections"]["filter"]["name"] == "threshold"
    assert payload["reproducibility"]["pipeline"] == result.pipeline_config
    assert "# Netbone Backbone Report" in markdown
    assert "## Method" in markdown
    assert "## Reproducibility" in markdown
    json.dumps(payload)


def test_report_write_markdown_saves_file(tmp_path) -> None:
    report = nb.report(_threshold_result(2.0))
    path = tmp_path / "reports" / "backbone.md"

    written_path = report.write_markdown(path)

    assert written_path == path.resolve()
    assert path.read_text(encoding="utf-8") == report.to_markdown()
    assert path.read_bytes().endswith(b"\n")


def test_report_write_markdown_can_refuse_overwrite(tmp_path) -> None:
    report = nb.report(_threshold_result(2.0))
    path = tmp_path / "backbone.md"
    path.write_text("existing\n", encoding="utf-8")

    with pytest.raises(nb.ValidationError, match="already exists"):
        report.write_markdown(path, overwrite=False)

    assert path.read_text(encoding="utf-8") == "existing\n"


def test_report_write_markdown_rejects_directory_path(tmp_path) -> None:
    report = nb.report(_threshold_result(2.0))

    with pytest.raises(nb.ValidationError, match="points to a directory"):
        report.write_markdown(tmp_path)


def test_report_write_markdown_rejects_file_parent_path(tmp_path) -> None:
    report = nb.report(_threshold_result(2.0))
    parent = tmp_path / "not_a_directory"
    parent.write_text("file\n", encoding="utf-8")

    with pytest.raises(nb.ValidationError, match="parent path is not a directory"):
        report.write_markdown(parent / "backbone.md")


def test_report_backbone_result_with_custom_filter_label() -> None:
    graph = _graph()

    def keep_first(
        method_result: nb.MethodResult,
        _original_graph: nx.Graph,
    ) -> nb.Selection:
        mask = method_result.statistics["edge_id"] == 0
        return nb.Selection(
            target="edge",
            selected_ids=(0,),
            rejected_ids=(1,),
            statistic="score",
            parameters={"strategy": "custom_keep_first"},
            mask=mask,
        )

    result = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter(keep_first)
        .run(graph)
    )

    payload = nb.report(result).to_dict()

    assert payload["sections"]["filter"]["name"] == "custom_keep_first"
    assert payload["sections"]["filter"]["display_name"] is None


def test_report_comparison_includes_metric_tables() -> None:
    comparison = nb.compare(
        {
            "strict": _threshold_result(2.0),
            "loose": _threshold_result(1.0),
        }
    )

    report = nb.report(comparison)
    payload = report.to_dict()
    markdown = report.to_markdown()

    assert payload["subject_type"] == "comparison"
    assert payload["summary"]["result_count"] == 2
    assert payload["summary"]["pairwise_metric_rows"] > 0
    assert payload["sections"]["results"][0]["name"] == "strict"
    assert payload["sections"]["single_metrics"]
    assert "## Single Metrics" in markdown
    assert "| Result | Metric | Value | Status | Explanation |" in markdown
    json.dumps(payload)


def test_report_sweep_result_includes_runs_and_cache_summary() -> None:
    sweep_result = (
        nb.sweep(_graph())
        .score("edge_weight", weight="weight")
        .filter("threshold", operator="greater_equal")
        .vary_filter(value=[2.0, 1.0])
        .measure(["edge_retention"])
        .run()
    )

    report = nb.report(sweep_result)
    payload = report.to_dict()
    markdown = report.to_markdown()

    assert payload["subject_type"] == "sweep_result"
    assert payload["summary"]["run_count"] == 2
    assert payload["summary"]["score_cache_hits"] == 1
    assert len(payload["sections"]["runs"]) == 2
    assert len(payload["sections"]["metrics"]) == 2
    assert "## Runs" in markdown
    assert "## Metrics" in markdown
    json.dumps(payload)


def test_report_generation_does_not_import_llm_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _threshold_result(2.0)
    original_import = builtins.__import__

    def guarded_import(name: str, *args: object, **kwargs: object) -> object:
        if name.split(".")[0] in {"anthropic", "openai"}:
            raise AssertionError(f"Unexpected LLM dependency import: {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    report = nb.report(result)

    assert report.to_markdown()
    assert report.to_dict()


def test_report_rejects_unsupported_subjects() -> None:
    with pytest.raises(nb.ConfigurationError, match="BackboneResult"):
        nb.report(object())  # type: ignore[arg-type]
