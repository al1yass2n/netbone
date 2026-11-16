"""Node degree scoring method."""

from __future__ import annotations

from typing import Any

import pandas as pd

from netbone.network import Network
from netbone.results import MethodResult

NODE_DEGREE_METADATA: dict[str, object] = {
    "name": "node_degree",
    "display_name": "Node Degree",
    "target": "node",
    "output_type": "score",
    "primary_statistic": "node_degree",
    "preferred_direction": "higher",
    "supports_directed": False,
    "supports_weighted": True,
    "requires_weights": False,
    "supports_multigraph": False,
    "supports_self_loops": False,
    "default_filter": "fraction",
    "default_filter_parameters": {
        "fraction": 0.1,
    },
}


def compute_node_degree(network: Network) -> MethodResult:
    """Compute unweighted degree for every node."""

    rows: list[dict[str, Any]] = []
    for node_id in sorted(network.graph.nodes):
        rows.append(
            {
                "node_id": node_id,
                "node": network.node_id_to_original[node_id],
                "node_degree": float(network.graph.degree[node_id]),
            }
        )

    statistics = pd.DataFrame(
        rows,
        columns=["node_id", "node", "node_degree"],
    )
    return MethodResult(
        method_name="node_degree",
        target="node",
        statistics=statistics,
        primary_statistic="node_degree",
        output_type="score",
        preferred_direction="higher",
        parameters={},
        metadata=NODE_DEGREE_METADATA,
        warnings=(),
    )
