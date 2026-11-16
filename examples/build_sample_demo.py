"""Generate the data used by the interactive documentation demo."""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

import netbone as nb


def demo_data() -> dict[str, object]:
    """Compute the example's selections and edge Jaccard values using Netbone."""
    graph = nx.Graph()
    # The same weighted collaboration network used in the local app tutorial.
    graph.add_weighted_edges_from(
        [
            ("alice", "bob", 4),
            ("bob", "carol", 1),
            ("carol", "dana", 2),
            ("alice", "carol", 3),
        ]
    )
    scores = nb.score(graph, "edge_weight", weight="weight")
    results = {
        str(percent): nb.filter_scores(
            graph, scores, "fraction", fraction=percent / 100
        )
        for percent in range(0, 101, 25)
    }
    pairwise = nb.compare(results).pairwise(metrics=["edge_jaccard"])
    return {
        "edges": scores.statistics[["edge_id", "source", "target", "score"]].to_dict(
            orient="records"
        ),
        "runs": {
            percent: list(result.selection.selected_ids)
            for percent, result in results.items()
        },
        "jaccard": {
            f"{row.result_a}:{row.result_b}": float(row.value)
            for row in pairwise.itertuples(index=False)
        },
    }


if __name__ == "__main__":
    destination = Path(__file__).resolve().parents[1] / "docs/assets/sample-demo.json"
    destination.write_text(
        json.dumps(demo_data(), indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
