"""Primary Linkage Analysis scoring method."""

from __future__ import annotations

from typing import Any

import pandas as pd

from netbone.methods._utils import edge_weights
from netbone.network import EDGE_ID_ATTR, Network
from netbone.results import MethodResult

PRIMARY_LINKAGE_METADATA: dict[str, object] = {
    "name": "primary_linkage",
    "display_name": "Primary Linkage",
    "target": "edge",
    "output_type": "score",
    "primary_statistic": "primary_linkage_selected",
    "preferred_direction": "higher",
    "supports_directed": False,
    "supports_weighted": True,
    "requires_weights": True,
    "weight_mode": "required",
    "requires_positive_weights": False,
    "supports_multigraph": False,
    "supports_self_loops": False,
    "default_filter": "threshold",
    "default_filter_parameters": {
        "value": 1.0,
        "operator": "equal",
    },
    "default_weight": "auto",
    "tie_policy": "stable_edge_id",
    "reference": "Nocaj, Ortmann, and Brandes, Computer Graphics Forum 28(3), 2009.",
    "doi": "10.1111/j.1467-9663.2009.00547.x",
}


def compute_primary_linkage(
    network: Network,
    *,
    weight: str = "weight",
) -> MethodResult:
    """Mark each node's strongest incident edge, unioned across endpoints."""

    weights = edge_weights(network, weight=weight, method_name="primary_linkage")
    primary_by_node, tied_nodes = _primary_edges_by_node(network, weights)
    endpoint_counts: dict[int, int] = {edge_id: 0 for edge_id in weights}
    for edge_id in primary_by_node.values():
        endpoint_counts[edge_id] += 1

    rows: list[dict[str, Any]] = []
    for source_id, target_id, attributes in sorted(
        network.graph.edges(data=True),
        key=lambda edge: edge[2][EDGE_ID_ATTR],
    ):
        edge_id = int(attributes[EDGE_ID_ATTR])
        selected = endpoint_counts[edge_id] > 0
        rows.append(
            {
                "edge_id": edge_id,
                "source_id": source_id,
                "target_id": target_id,
                "source": network.node_id_to_original[source_id],
                "target": network.node_id_to_original[target_id],
                "primary_linkage_weight": weights[edge_id],
                "primary_linkage_endpoint_count": endpoint_counts[edge_id],
                "primary_linkage_selected": 1.0 if selected else 0.0,
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
            "primary_linkage_weight",
            "primary_linkage_endpoint_count",
            "primary_linkage_selected",
        ],
    )
    return MethodResult(
        method_name="primary_linkage",
        target="edge",
        statistics=statistics,
        primary_statistic="primary_linkage_selected",
        output_type="score",
        preferred_direction="higher",
        parameters={"weight": weight, "tie_policy": "stable_edge_id"},
        metadata=PRIMARY_LINKAGE_METADATA,
        warnings=_warnings(tied_nodes),
    )


def _primary_edges_by_node(
    network: Network,
    weights: dict[int, float],
) -> tuple[dict[int, int], set[int]]:
    primary_by_node: dict[int, int] = {}
    tied_nodes: set[int] = set()
    for node_id in sorted(network.graph.nodes):
        incident_edges = [
            int(attributes[EDGE_ID_ATTR])
            for _, _, attributes in network.graph.edges(node_id, data=True)
        ]
        if not incident_edges:
            continue
        maximum = max(weights[edge_id] for edge_id in incident_edges)
        candidates = [
            edge_id for edge_id in incident_edges if weights[edge_id] == maximum
        ]
        if len(candidates) > 1:
            tied_nodes.add(node_id)
        primary_by_node[node_id] = min(candidates)
    return primary_by_node, tied_nodes


def _warnings(tied_nodes: set[int]) -> tuple[str, ...]:
    if not tied_nodes:
        return ()
    return (
        "Primary linkage encountered tied maximum weights for one or more "
        "nodes; ties were broken by stable edge_id order.",
    )
