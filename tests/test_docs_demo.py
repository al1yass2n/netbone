from __future__ import annotations

import json
import runpy
from pathlib import Path


def test_demo_data_matches_netbone_and_the_sample_network() -> None:
    generate = runpy.run_path("examples/build_sample_demo.py")["demo_data"]
    fixture = json.loads(
        Path("docs/assets/sample-demo.json").read_text(encoding="utf-8")
    )

    assert fixture == generate()
    weights_by_id = {edge["edge_id"]: edge["score"] for edge in fixture["edges"]}
    assert fixture["runs"]["0"] == []
    assert [weights_by_id[edge_id] for edge_id in fixture["runs"]["25"]] == [4]
    assert sorted(weights_by_id[edge_id] for edge_id in fixture["runs"]["75"]) == [
        2,
        3,
        4,
    ]
    assert len(fixture["runs"]["100"]) == 4
    assert fixture["jaccard"]["25:75"] == 1 / 3
