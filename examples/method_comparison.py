"""Run a small Netbone method-comparison workflow."""

from __future__ import annotations

import networkx as nx

import netbone as nb


def main() -> dict[str, object]:
    """Compare two backbone configurations and return inspectable outputs."""

    graph = nx.Graph()
    graph.add_edge("alice", "bob", weight=4.0)
    graph.add_edge("bob", "carol", weight=2.0)
    graph.add_edge("carol", "dana", weight=1.0)

    strict = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("threshold", value=4.0, operator="greater_equal")
        .run(graph)
    )
    relaxed = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("fraction", fraction=2 / 3)
        .run(graph)
    )

    comparison = nb.compare({"strict": strict, "relaxed": relaxed})
    single = comparison.table(metrics=["edge_count", "edge_retention"])
    pairwise = comparison.pairwise(metrics=["edge_jaccard"])
    spearman = comparison.spearman()

    output = {
        "single_metrics": single.to_dict(orient="records"),
        "pairwise_metrics": pairwise.to_dict(orient="records"),
        "spearman": spearman.to_dict(orient="records"),
    }
    print(output)
    return output


if __name__ == "__main__":
    main()
