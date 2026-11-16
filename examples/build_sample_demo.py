"""Precompute the files used by the Netbone web app demo on GitHub Pages."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from io import BytesIO
from itertools import combinations
from pathlib import Path
from zipfile import ZipFile

import networkx as nx

from netbone.webapp.bridge import (
    comparison_payload,
    experiment_export_payload,
    filter_payload,
    filter_preview_payload,
    preview_payload,
    result_export_payload,
    score_payload,
    ui_schema_payload,
)

METHOD_LABELS = {"edge_weight": "EW", "edge_betweenness": "EB"}
FRACTIONS = (0.25, 0.50)


def build_demo(destination: Path) -> None:
    """Write app response fixtures and exports for the supported demo settings."""
    graphml = "\n".join(nx.generate_graphml(nx.karate_club_graph())) + "\n"
    dataset = {
        "data_mode": "graphml",
        "graphml_text": graphml,
        "weight": "weight",
        "context": "Zachary’s Karate Club. Edge weights count interaction contexts.",
    }

    scores = {}
    runs = {}
    baseline = []
    results = {}
    for method, label in METHOD_LABELS.items():
        scores[method] = score_payload(
            {
                **dataset,
                "guided": {
                    "method": method,
                    "controls": {"distance_transform": "inverse"},
                },
            }
        )
        for fraction in FRACTIONS:
            request = {
                "score_id": scores[method]["score_id"],
                "guided": {
                    "method": method,
                    "filter": "fraction",
                    "controls": {"fraction": fraction, "tie_policy": "exact_stable"},
                },
            }
            result = filter_payload(request)
            result_id = str(result["result_id"])
            runs[f"{method}:{fraction}"] = {
                "preview": filter_preview_payload(request),
                "result": result,
            }
            results[result_id] = {
                "result_id": result_id,
                "label": f"{label} {fraction:.0%}",
            }
            if fraction == FRACTIONS[0]:
                baseline.append(result_id)
            _write_run_downloads(destination / "runs" / result_id, result_id)

    comparisons = []
    for count in range(2, len(results) + 1):
        for selected in combinations(sorted(results), count):
            key = "_".join(selected)
            comparison = comparison_payload(
                {"results": [results[result_id] for result_id in selected]}
            )
            archive = experiment_export_payload(
                {"experiment_id": comparison["experiment_id"]}
            )
            comparison["experiment_id"] = key
            _write_json(destination / "compare" / f"{key}.json", comparison)
            (destination / "compare" / f"{key}.zip").write_bytes(archive.content)
            comparisons.append(key)

    _write_json(
        destination / "snapshot.json",
        {
            "schema": _demo_schema(),
            "graphml": graphml,
            "preview": preview_payload(dataset),
            "scores": scores,
            "runs": runs,
            "baseline": baseline,
            "comparisons": comparisons,
        },
    )


def _demo_schema() -> dict[str, object]:
    schema = ui_schema_payload()
    methods = schema["methods"]
    filters = schema["filters"]
    controls = schema["controls"]
    assert isinstance(methods, list) and isinstance(filters, list)
    assert isinstance(controls, dict)
    return {
        **schema,
        "methods": [
            {
                **method,
                "recommended_filter": "fraction",
                "default_filter_parameters": {"fraction": FRACTIONS[0]},
            }
            for method in methods
            if isinstance(method, dict) and method["name"] in METHOD_LABELS
        ],
        "filters": [
            item
            for item in filters
            if isinstance(item, dict) and item["name"] == "fraction"
        ],
        "controls": {
            **controls,
            "methods": {method: [] for method in METHOD_LABELS},
            "filters": {
                "fraction": [
                    {
                        "name": "fraction",
                        "label": "Retained fraction",
                        "control": "select",
                        "default": FRACTIONS[0],
                        "options": [
                            {"value": str(fraction), "label": f"{fraction:.0%}"}
                            for fraction in FRACTIONS
                        ],
                    }
                ]
            },
        },
    }


def _write_run_downloads(destination: Path, result_id: str) -> None:
    archive = result_export_payload({"result_id": result_id, "format": "zip"})
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "experiment.zip").write_bytes(archive.content)
    with ZipFile(BytesIO(archive.content)) as bundle:
        for scope, stem in (
            ("annotated", "original_annotated"),
            ("backbone", "backbone"),
        ):
            for fmt in ("graphml", "gexf"):
                (destination / f"{scope}.{fmt}").write_bytes(
                    bundle.read(f"graphs/{stem}.{fmt}")
                )


def _write_json(path: Path, content: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(content, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    build_demo(parser.parse_args().destination)
