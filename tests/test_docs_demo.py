from __future__ import annotations

import json
import runpy
from pathlib import Path
from zipfile import ZipFile


def test_demo_snapshot_keeps_the_same_edge_budget_with_different_links(
    tmp_path: Path,
) -> None:
    build_demo = runpy.run_path("examples/build_sample_demo.py")["build_demo"]
    build_demo(tmp_path)
    snapshot = json.loads((tmp_path / "snapshot.json").read_text(encoding="utf-8"))

    assert snapshot["preview"]["node_count"] == 34
    assert snapshot["preview"]["edge_count"] == 78
    assert set(snapshot["runs"]) == {
        "edge_weight:0.25",
        "edge_weight:0.5",
        "edge_betweenness:0.25",
        "edge_betweenness:0.5",
    }
    assert {
        key: run["preview"]["backbone_edge_count"]
        for key, run in snapshot["runs"].items()
    } == {
        "edge_weight:0.25": 20,
        "edge_weight:0.5": 39,
        "edge_betweenness:0.25": 20,
        "edge_betweenness:0.5": 39,
    }

    comparison_key = "_".join(sorted(snapshot["baseline"]))
    comparison = json.loads(
        (tmp_path / "compare" / f"{comparison_key}.json").read_text(encoding="utf-8")
    )
    assert [
        record["value"]
        for record in comparison["pairwise_metrics"]
        if record["metric"] == "edge_overlap"
    ] == [6]
    assert len(snapshot["comparisons"]) == 11
    for key in snapshot["comparisons"]:
        with ZipFile(tmp_path / "compare" / f"{key}.zip") as bundle:
            assert "manifest.json" in bundle.namelist()
    for result_id in snapshot["baseline"]:
        directory = tmp_path / "runs" / result_id
        assert (directory / "backbone.graphml").is_file()
        with ZipFile(directory / "experiment.zip") as bundle:
            assert "graphs/backbone.graphml" in bundle.namelist()
