"""Run a small reproducible experiment-bundle workflow."""

from __future__ import annotations

import json
from tempfile import TemporaryDirectory

import networkx as nx

import netbone as nb


def main() -> dict[str, object]:
    """Save a bundle and return inspectable deterministic outputs."""

    graph = nx.Graph()
    graph.add_edge("alice", "bob", weight=4.0)
    graph.add_edge("bob", "carol", weight=2.0)
    graph.add_edge("carol", "dana", weight=1.0)

    result = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("threshold", value=2.0, operator="greater_equal")
        .run(graph)
    )

    with TemporaryDirectory() as directory:
        bundle_path = nb.save_experiment(result, f"{directory}/bundle")
        manifest = json.loads(
            (bundle_path / "manifest.json").read_text(encoding="utf-8")
        )
        restored = nb.Pipeline.from_json(bundle_path / "pipeline.json")

    output = {
        "subject_type": manifest["subject_type"],
        "file_count": len(manifest["files"]),
        "restored_pipeline": restored.to_dict(),
    }
    print(output)
    return output


if __name__ == "__main__":
    main()
