"""Optional visualization workflow.

The example returns plot-ready deterministic tables in every environment. If
Matplotlib is installed through `netbone[viz]`, it also creates three figures.
"""

from __future__ import annotations

import networkx as nx

import netbone as nb
from netbone import viz


def _graph() -> nx.Graph:
    graph = nx.Graph()
    graph.add_edge("alice", "bob", weight=4.0)
    graph.add_edge("bob", "carol", weight=2.0)
    graph.add_edge("carol", "dana", weight=1.0)
    graph.add_edge("alice", "carol", weight=3.0)
    return graph


def main() -> dict[str, object]:
    """Run the optional visualization workflow and return deterministic output."""

    graph = _graph()
    strict = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("threshold", value=4.0, operator="greater_equal")
        .run(graph)
    )
    loose = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("threshold", value=2.0, operator="greater_equal")
        .run(graph)
    )
    comparison = nb.compare({"strict": strict, "loose": loose})
    sweep_result = (
        nb.sweep(graph)
        .score("edge_weight", weight="weight")
        .filter("threshold", operator="greater_equal")
        .vary_filter(value=[4.0, 3.0, 2.0])
        .measure(["edge_count"])
        .run()
    )

    figures_created = 0
    try:
        viz.plot_comparison_metric(comparison, "edge_retention")
        viz.plot_pairwise_metric(comparison, "edge_jaccard")
        viz.plot_sweep_metric(sweep_result, "edge_count")
    except nb.ConfigurationError:
        figures_created = 0
    else:
        figures_created = 3

    return {
        "single_metric_rows": len(comparison.metric("edge_retention")),
        "pairwise_metric_rows": len(comparison.pairwise(metrics=["edge_jaccard"])),
        "sweep_metric_rows": len(sweep_result.table()),
        "figures_created": figures_created,
    }


if __name__ == "__main__":
    print(main())
