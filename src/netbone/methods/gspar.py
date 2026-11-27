"""GSPAR Jaccard-based graph sparsification scoring method."""

from __future__ import annotations

from typing import Any

import pandas as pd

from netbone.methods._references import reference_metadata
from netbone.network import EDGE_ID_ATTR, Network
from netbone.results import MethodResult

GSPAR_METADATA: dict[str, object] = {
    "name": "gspar",
    "display_name": "GSPAR",
    "target": "edge",
    "output_type": "score",
    "primary_statistic": "gspar_jaccard_similarity",
    "preferred_direction": "higher",
    "supports_directed": False,
    "supports_weighted": True,
    "requires_weights": False,
    "weight_mode": "ignored",
    "supports_multigraph": False,
    "supports_self_loops": False,
    "default_filter": "fraction",
    "default_filter_parameters": {
        "fraction": 0.1,
    },
    "neighborhood": "open",
    **reference_metadata("gspar"),
}


def compute_gspar(network: Network) -> MethodResult:
    """Compute open-neighborhood Jaccard similarity for each edge."""

    neighborhoods = {
        node_id: set(network.graph.neighbors(node_id))
        for node_id in network.graph.nodes
    }
    rows: list[dict[str, Any]] = []
    for source_id, target_id, attributes in sorted(
        network.graph.edges(data=True),
        key=lambda edge: edge[2][EDGE_ID_ATTR],
    ):
        edge_id = int(attributes[EDGE_ID_ATTR])
        score = _jaccard(neighborhoods[source_id], neighborhoods[target_id])
        rows.append(
            {
                "edge_id": edge_id,
                "source_id": source_id,
                "target_id": target_id,
                "source": network.node_id_to_original[source_id],
                "target": network.node_id_to_original[target_id],
                "gspar_jaccard_similarity": score,
            }
        )

    statistics = pd.DataFrame(
        rows,
        columns=[
            "edge_id",
            "source_id",
            "target_id",
            "source",
            "target",
            "gspar_jaccard_similarity",
        ],
    )
    return MethodResult(
        method_name="gspar",
        target="edge",
        statistics=statistics,
        primary_statistic="gspar_jaccard_similarity",
        output_type="score",
        preferred_direction="higher",
        parameters={"neighborhood": "open"},
        metadata=GSPAR_METADATA,
        warnings=(),
    )


def _jaccard(left: set[int], right: set[int]) -> float:
    union = left.union(right)
    if not union:
        return 0.0
    return len(left.intersection(right)) / len(union)
