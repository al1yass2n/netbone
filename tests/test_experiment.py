from __future__ import annotations

import json
import re
from pathlib import Path

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


def test_save_experiment_backbone_result_bundle(tmp_path: Path) -> None:
    result = _result(2.0)
    destination = tmp_path / "bundle"

    bundle_path = nb.save_experiment(result, destination)

    manifest = _json(bundle_path / "manifest.json")
    pipeline = _json(bundle_path / "pipeline.json")
    summary = _json(bundle_path / "result.json")["summary"]
    statistics = pd.read_csv(bundle_path / "tables" / "method_statistics.csv")
    original_edges = pd.read_csv(bundle_path / "graphs" / "original_edges.csv")
    backbone_edges = pd.read_csv(bundle_path / "graphs" / "backbone_edges.csv")
    annotated_graph = nx.read_graphml(
        bundle_path / "graphs" / "original_annotated.graphml"
    )
    backbone_graph = nx.read_graphml(bundle_path / "graphs" / "backbone.graphml")
    annotated_gexf = nx.read_gexf(bundle_path / "graphs" / "original_annotated.gexf")
    backbone_gexf = nx.read_gexf(bundle_path / "graphs" / "backbone.gexf")
    gexf_text = (bundle_path / "graphs" / "original_annotated.gexf").read_text(
        encoding="utf-8"
    )

    assert bundle_path == destination.resolve()
    assert manifest["bundle_schema_version"] == "1.0"
    assert manifest["subject_type"] == "backbone_result"
    assert manifest["files"]["pipeline_json"] == "pipeline.json"
    assert manifest["files"]["original_annotated_graphml"] == (
        "graphs/original_annotated.graphml"
    )
    assert manifest["files"]["backbone_gexf"] == "graphs/backbone.gexf"
    assert pipeline == result.pipeline_config
    assert nb.Pipeline.from_json(bundle_path / "pipeline.json").to_dict() == pipeline
    assert summary["backbone_edge_count"] == 2
    assert statistics["score"].tolist() == [4.0, 2.0, 1.0]
    assert len(original_edges) == 3
    assert len(backbone_edges) == 2
    assert (
        (bundle_path / "report.md")
        .read_text(encoding="utf-8")
        .startswith("# Netbone Backbone Report")
    )
    edge_prefix = _annotation_prefix(annotated_graph["a"]["b"], "edge_weight")
    assert _annotation_prefix(backbone_graph["a"]["b"], "edge_weight") == edge_prefix
    assert annotated_graph["a"]["b"][f"{edge_prefix}_selected"] == 1
    assert annotated_graph["a"]["b"][f"{edge_prefix}_color"] == "#0072B2"
    assert annotated_graph["a"]["b"][f"{edge_prefix}_score"] == 4.0
    assert annotated_graph["c"]["d"][f"{edge_prefix}_selected"] == 0
    assert annotated_graph["c"]["d"][f"{edge_prefix}_score"] == 1.0
    assert backbone_graph["a"]["b"][f"{edge_prefix}_score"] == 4.0
    assert annotated_gexf["a"]["b"][f"{edge_prefix}_score"] == 4.0
    assert backbone_gexf["a"]["b"][f"{edge_prefix}_score"] == 4.0
    assert "netbone_edge_weight_selected" not in annotated_graph["a"]["b"]
    assert f"{edge_prefix}_role" not in annotated_graph.nodes["a"]
    assert f"{edge_prefix}_color" not in annotated_graph.nodes["a"]
    assert f"{edge_prefix}_target" not in annotated_graph.nodes["a"]
    assert backbone_graph.number_of_edges() == 2
    assert "<viz:color" in gexf_text
    assert f"{edge_prefix}_selected" not in result.original_graph["a"]["b"]


def test_save_experiment_node_target_graph_exports_are_annotated(
    tmp_path: Path,
) -> None:
    result = (
        nb.pipeline()
        .score("node_degree")
        .filter("threshold", value=2.0, operator="greater_equal")
        .run(_graph())
    )

    bundle_path = nb.save_experiment(result, tmp_path / "node_bundle")
    annotated_graph = nx.read_graphml(
        bundle_path / "graphs" / "original_annotated.graphml"
    )
    backbone_graph = nx.read_graphml(bundle_path / "graphs" / "backbone.graphml")
    annotated_gexf = nx.read_gexf(bundle_path / "graphs" / "original_annotated.gexf")
    backbone_gexf = nx.read_gexf(bundle_path / "graphs" / "backbone.gexf")

    node_prefix = _annotation_prefix(annotated_graph.nodes["b"], "node_degree")
    assert annotated_graph.nodes["b"][f"{node_prefix}_selected"] == 1
    assert annotated_graph.nodes["b"][f"{node_prefix}_color"] == "#0072B2"
    assert annotated_graph.nodes["b"][f"{node_prefix}_node_degree"] == 2.0
    assert annotated_graph.nodes["a"][f"{node_prefix}_selected"] == 0
    assert annotated_graph.nodes["a"][f"{node_prefix}_color"] == "#D9D9D9"
    assert annotated_graph.nodes["a"][f"{node_prefix}_node_degree"] == 1.0
    assert backbone_graph.nodes["b"][f"{node_prefix}_node_degree"] == 2.0
    assert annotated_gexf.nodes["b"][f"{node_prefix}_node_degree"] == 2.0
    assert backbone_gexf.nodes["b"][f"{node_prefix}_node_degree"] == 2.0
    assert "netbone_node_degree_selected" not in annotated_graph.nodes["b"]
    assert f"{node_prefix}_role" not in annotated_graph["b"]["c"]
    assert f"{node_prefix}_color" not in annotated_graph["b"]["c"]
    assert f"{node_prefix}_target" not in annotated_graph["b"]["c"]


def test_graph_exports_include_all_non_identity_method_statistics(
    tmp_path: Path,
) -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=4.0)
    graph.add_edge("b", "c", weight=2.0)
    graph.add_edge("a", "c", weight=1.0)
    result = (
        nb.pipeline()
        .score("disparity", weight="weight")
        .filter("significance", alpha=1.0)
        .run(graph)
    )

    bundle_path = nb.save_experiment(result, tmp_path / "disparity_bundle")
    exported = nx.read_graphml(bundle_path / "graphs" / "original_annotated.graphml")
    prefix = _annotation_prefix(exported["a"]["b"], "disparity")
    identity_columns = {
        "edge_id",
        "source_id",
        "target_id",
        "source",
        "target",
    }

    exported_attributes = exported["a"]["b"]
    for statistic in set(result.statistics.columns) - identity_columns:
        assert f"{prefix}_{statistic}" in exported_attributes
    for identity in {"edge_id", "source_id", "target_id", "source"}:
        assert f"{prefix}_{identity}" not in exported_attributes
    assert exported_attributes[f"{prefix}_target"] == "edge"


def test_graph_export_annotation_prefix_changes_with_pipeline_config(
    tmp_path: Path,
) -> None:
    strict_path = nb.save_experiment(_result(4.0), tmp_path / "strict")
    loose_path = nb.save_experiment(_result(2.0), tmp_path / "loose")

    strict_graph = nx.read_graphml(
        strict_path / "graphs" / "original_annotated.graphml"
    )
    loose_graph = nx.read_graphml(loose_path / "graphs" / "original_annotated.graphml")

    assert _annotation_prefix(strict_graph["a"]["b"], "edge_weight") != (
        _annotation_prefix(loose_graph["a"]["b"], "edge_weight")
    )


def test_save_experiment_comparison_bundle(tmp_path: Path) -> None:
    comparison = nb.compare({"strict": _result(4.0), "loose": _result(2.0)})

    bundle_path = nb.save_experiment(comparison, tmp_path / "comparison")

    manifest = _json(bundle_path / "manifest.json")
    payload = _json(bundle_path / "comparison.json")
    single_metrics = pd.read_csv(bundle_path / "tables" / "single_metrics.csv")
    pairwise_metrics = pd.read_csv(bundle_path / "tables" / "pairwise_metrics.csv")

    assert manifest["subject_type"] == "comparison"
    assert payload["result_names"] == ["strict", "loose"]
    assert "pipeline_strict_json" in manifest["files"]
    assert "result_loose_json" in manifest["files"]
    assert "edge_retention" in single_metrics["metric"].tolist()
    assert "edge_jaccard" in pairwise_metrics["metric"].tolist()
    assert (bundle_path / "pipelines" / "strict.json").exists()
    assert (bundle_path / "results" / "loose.json").exists()


def test_save_experiment_sweep_bundle(tmp_path: Path) -> None:
    sweep_result = (
        nb.sweep(_graph())
        .score("edge_weight", weight="weight")
        .filter("threshold", operator="greater_equal")
        .vary_filter(value=[4.0, 2.0])
        .measure(["edge_count"])
        .run()
    )

    bundle_path = nb.save_experiment(sweep_result, tmp_path / "sweep")

    manifest = _json(bundle_path / "manifest.json")
    runs = pd.read_csv(bundle_path / "tables" / "runs.csv")
    metrics = pd.read_csv(bundle_path / "tables" / "metrics.csv")
    index = _json(bundle_path / "pipelines" / "index.json")

    assert manifest["subject_type"] == "sweep_result"
    assert manifest["files"]["pipeline_index_json"] == "pipelines/index.json"
    assert runs["status"].tolist() == ["ok", "ok"]
    assert metrics["metric"].tolist() == ["edge_count", "edge_count"]
    assert [entry["status"] for entry in index] == ["ok", "ok"]
    assert len(list((bundle_path / "pipelines").glob("*.json"))) == 3
    assert len(list((bundle_path / "results").glob("*.json"))) == 2


def test_save_experiment_rejects_existing_directory_without_overwrite(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "bundle"
    destination.mkdir()
    (destination / "keep.txt").write_text("keep\n", encoding="utf-8")

    with pytest.raises(nb.ValidationError, match="already exists"):
        nb.save_experiment(_result(2.0), destination)

    assert (destination / "keep.txt").exists()


def test_save_experiment_overwrites_previous_bundle_when_requested(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "bundle"
    nb.save_experiment(_result(2.0), destination)
    (destination / "remove.txt").write_text("remove\n", encoding="utf-8")

    nb.save_experiment(_result(2.0), destination, overwrite=True)

    assert not (destination / "remove.txt").exists()
    assert (destination / "manifest.json").exists()


def test_save_experiment_overwrite_refuses_unrelated_directory(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "project"
    destination.mkdir()
    keep = destination / "keep.txt"
    keep.write_text("keep\n", encoding="utf-8")

    with pytest.raises(nb.ValidationError, match="not a Netbone experiment bundle"):
        nb.save_experiment(_result(2.0), destination, overwrite=True)

    assert keep.read_text(encoding="utf-8") == "keep\n"

    empty = tmp_path / "empty"
    empty.mkdir()
    nb.save_experiment(_result(2.0), empty, overwrite=True)
    assert (empty / "manifest.json").exists()


def test_save_experiment_rejects_file_path_and_unsupported_subject(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "bundle"
    file_path.write_text("file\n", encoding="utf-8")

    with pytest.raises(nb.ValidationError, match="points to a file"):
        nb.save_experiment(_result(2.0), file_path)

    with pytest.raises(nb.ConfigurationError, match="BackboneResult"):
        nb.save_experiment(object(), tmp_path / "bad")  # type: ignore[arg-type]


def _json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _annotation_prefix(attributes: dict[str, object], method_name: str) -> str:
    pattern = re.compile(
        rf"^(netbone_{re.escape(method_name)}_[0-9a-f]{{8}})_selected$"
    )
    matches = [
        match.group(1)
        for key in attributes
        if (match := pattern.match(str(key))) is not None
    ]
    assert len(matches) == 1
    return matches[0]
