from __future__ import annotations

import runpy
from pathlib import Path


def test_basic_extraction_example_runs() -> None:
    example_path = Path("examples/basic_extraction.py")

    namespace = runpy.run_path(str(example_path))
    output = namespace["main"]()

    assert output["edges"] == [("alice", "bob"), ("carol", "dana")]
    assert output["summary"]["edge_fraction"] == 2 / 3


def test_method_comparison_example_runs() -> None:
    example_path = Path("examples/method_comparison.py")

    namespace = runpy.run_path(str(example_path))
    output = namespace["main"]()

    assert output["pairwise_metrics"][0]["metric"] == "edge_jaccard"
    assert output["pairwise_metrics"][0]["value"] == 0.5
    assert output["spearman"][0]["status"] == "ok"


def test_parameter_sweep_example_runs() -> None:
    example_path = Path("examples/parameter_sweep.py")

    namespace = runpy.run_path(str(example_path))
    output = namespace["main"]()

    assert output["score_cache_misses"] == 1
    assert output["score_cache_hits"] == 1
    assert [
        row["value"] for row in output["metrics"] if row["metric"] == "edge_count"
    ] == [
        1,
        2,
    ]


def test_deterministic_reporting_example_runs() -> None:
    example_path = Path("examples/deterministic_reporting.py")

    namespace = runpy.run_path(str(example_path))
    output = namespace["main"]()

    assert output["subject_type"] == "backbone_result"
    assert output["markdown_heading"] == "# Netbone Backbone Report"


def test_optional_visualization_example_runs_without_matplotlib() -> None:
    example_path = Path("examples/optional_visualization.py")

    namespace = runpy.run_path(str(example_path))
    output = namespace["main"]()

    assert output["single_metric_rows"] == 2
    assert output["pairwise_metric_rows"] == 1
    assert output["sweep_metric_rows"] == 3
    assert output["figures_created"] in {0, 3}


def test_experiment_bundle_example_runs() -> None:
    example_path = Path("examples/experiment_bundle.py")

    namespace = runpy.run_path(str(example_path))
    output = namespace["main"]()

    assert output["subject_type"] == "backbone_result"
    assert output["file_count"] >= 8
    assert output["restored_pipeline"]["method"]["name"] == "edge_weight"


def test_temporal_aggregation_example_runs() -> None:
    example_path = Path("examples/temporal_aggregation.py")

    namespace = runpy.run_path(str(example_path))
    output = namespace["main"]()

    assert output == {
        "weighting": "persistent_weibull",
        "edges": [("bob", "carol")],
        "event_count": 3,
    }
