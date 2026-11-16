"""Run a small Netbone parameter-sweep workflow."""

from __future__ import annotations

import networkx as nx

import netbone as nb


def main() -> dict[str, object]:
    """Sweep threshold values and return inspectable outputs."""

    graph = nx.Graph()
    graph.add_edge("alice", "bob", weight=4.0)
    graph.add_edge("bob", "carol", weight=2.0)
    graph.add_edge("carol", "dana", weight=1.0)

    sweep_result = (
        nb.sweep(graph)
        .score("edge_weight", weight="weight")
        .filter("threshold", operator="greater_equal")
        .vary_filter(value=[4.0, 2.0])
        .measure(["edge_count", "edge_retention"])
        .run()
    )

    output = {
        "score_cache_hits": sweep_result.score_cache_hits,
        "score_cache_misses": sweep_result.score_cache_misses,
        "runs": sweep_result.runs.to_dict(orient="records"),
        "metrics": sweep_result.table().to_dict(orient="records"),
    }
    print(output)
    return output


if __name__ == "__main__":
    main()
