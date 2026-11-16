"""Multiple Linkage Analysis scoring method."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from netbone.methods._utils import edge_weights
from netbone.network import EDGE_ID_ATTR, Network
from netbone.results import MethodResult

MULTIPLE_LINKAGE_METADATA: dict[str, object] = {
    "name": "multiple_linkage",
    "display_name": "Multiple Linkage Analysis",
    "target": "edge",
    "output_type": "score",
    "primary_statistic": "multiple_linkage_selected",
    "preferred_direction": "higher",
    "supports_directed": False,
    "supports_weighted": True,
    "requires_weights": True,
    "requires_positive_weights": False,
    "requires_nonnegative_weights": True,
    "supports_multigraph": False,
    "supports_self_loops": False,
    "default_filter": "threshold",
    "default_filter_parameters": {
        "value": 1.0,
        "operator": "equal",
    },
    "default_weight": "weight",
    "tie_policy": "stable_edge_id",
    "reference": "Nocaj, Ortmann, and Brandes, Computer Graphics Forum 28(3), 2009.",
    "doi": "10.1111/j.1467-9663.2009.00547.x",
}


def compute_multiple_linkage(
    network: Network,
    *,
    weight: str = "weight",
) -> MethodResult:
    """Mark the leading MLAM incident edges for each node."""

    weights = edge_weights(
        network,
        weight=weight,
        method_name="multiple_linkage",
        require_nonnegative=True,
    )
    selected_by_node = _selected_edges_by_node(network, weights)
    endpoint_counts: dict[int, int] = {edge_id: 0 for edge_id in weights}
    for selected_edge_ids in selected_by_node.values():
        for edge_id in selected_edge_ids:
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
                "multiple_linkage_weight": weights[edge_id],
                "multiple_linkage_endpoint_count": endpoint_counts[edge_id],
                "multiple_linkage_selected": 1.0 if selected else 0.0,
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
            "multiple_linkage_weight",
            "multiple_linkage_endpoint_count",
            "multiple_linkage_selected",
        ],
    )
    return MethodResult(
        method_name="multiple_linkage",
        target="edge",
        statistics=statistics,
        primary_statistic="multiple_linkage_selected",
        output_type="score",
        preferred_direction="higher",
        parameters={"weight": weight, "tie_policy": "stable_edge_id"},
        metadata=MULTIPLE_LINKAGE_METADATA,
        warnings=(),
    )


def _selected_edges_by_node(
    network: Network,
    weights: dict[int, float],
) -> dict[int, tuple[int, ...]]:
    selected_by_node: dict[int, tuple[int, ...]] = {}
    for node_id in sorted(network.graph.nodes):
        incident_edges = [
            int(attributes[EDGE_ID_ATTR])
            for _, _, attributes in network.graph.edges(node_id, data=True)
            if weights[int(attributes[EDGE_ID_ATTR])] > 0.0
        ]
        if not incident_edges:
            selected_by_node[node_id] = ()
            continue
        ordered_edges = sorted(
            incident_edges,
            key=lambda edge_id: (-weights[edge_id], edge_id),
        )
        cutoff_index = _cutoff_index([weights[edge_id] for edge_id in ordered_edges])
        selected_by_node[node_id] = tuple(ordered_edges[: cutoff_index + 1])
    return selected_by_node


def _cutoff_index(sorted_weights: list[float]) -> int:
    if len(sorted_weights) == 1:
        return 0
    total = sum(sorted_weights)
    real_distribution = [weight / total * 100.0 for weight in sorted_weights]
    best_cod = -1.0
    best_index = 0
    for index in range(len(sorted_weights)):
        cod = _coefficient_of_determination(
            real_distribution,
            _ideal_distribution(index, len(sorted_weights)),
        )
        if cod > best_cod:
            best_cod = cod
            best_index = index
    return best_index


def _ideal_distribution(index: int, total: int) -> list[float]:
    percentage = 100.0 / (index + 1)
    return [percentage if position <= index else 0.0 for position in range(total)]


def _coefficient_of_determination(left: list[float], right: list[float]) -> float:
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    left_offsets = [value - left_mean for value in left]
    right_offsets = [value - right_mean for value in right]
    left_variance = sum(value * value for value in left_offsets)
    right_variance = sum(value * value for value in right_offsets)
    if left_variance == 0.0 and right_variance == 0.0:
        return 1.0
    if left_variance == 0.0 or right_variance == 0.0:
        return 0.0
    covariance = sum(
        left_value * right_value
        for left_value, right_value in zip(left_offsets, right_offsets, strict=True)
    )
    correlation = covariance / math.sqrt(left_variance * right_variance)
    return correlation * correlation
