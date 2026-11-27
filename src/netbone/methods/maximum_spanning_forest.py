"""Deterministic maximum spanning forest scoring method."""

from __future__ import annotations

import math
from collections.abc import Mapping
from numbers import Real
from typing import Any

import pandas as pd

from netbone.exceptions import ValidationError
from netbone.methods._references import reference_metadata
from netbone.network import EDGE_ID_ATTR, Network
from netbone.results import MethodResult

MAXIMUM_SPANNING_FOREST_METADATA: dict[str, object] = {
    "name": "maximum_spanning_forest",
    "display_name": "Maximum Spanning Forest",
    "target": "edge",
    "output_type": "score",
    "primary_statistic": "maximum_spanning_forest_selected",
    "preferred_direction": "higher",
    "supports_directed": False,
    "supports_weighted": True,
    "requires_weights": False,
    "weight_mode": "optional",
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
    **reference_metadata("maximum_spanning_forest"),
}


def compute_maximum_spanning_forest(
    network: Network,
    *,
    weight: str | None = "weight",
) -> MethodResult:
    """Compute deterministic maximum-spanning-forest membership.

    Edges are considered by descending weight and then by stable internal edge
    id. The primary statistic is `1.0` for edges in the forest and `0.0` for
    rejected edges, so the existing threshold filter can extract the forest.

    Args:
        network: Normalized simple undirected network to score.
        weight: Edge attribute containing finite numeric weights. Pass `None`
            to treat every edge as weight `1.0`.

    Raises:
        ValidationError: If a configured weight is missing, non-numeric,
            boolean, NaN, or infinite.
    """

    weights = _edge_weights(network, weight=weight)
    selected_order = _selected_edge_order(network, weights)
    selected_ids = set(selected_order)

    rows: list[dict[str, Any]] = []
    for source_id, target_id, attributes in sorted(
        network.graph.edges(data=True),
        key=lambda edge: edge[2][EDGE_ID_ATTR],
    ):
        edge_id = int(attributes[EDGE_ID_ATTR])
        rows.append(
            {
                "edge_id": edge_id,
                "source_id": source_id,
                "target_id": target_id,
                "source": network.node_id_to_original[source_id],
                "target": network.node_id_to_original[target_id],
                "maximum_spanning_forest_weight": weights[edge_id],
                "maximum_spanning_forest_order": selected_order.get(edge_id),
                "maximum_spanning_forest_selected": (
                    1.0 if edge_id in selected_ids else 0.0
                ),
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
            "maximum_spanning_forest_weight",
            "maximum_spanning_forest_order",
            "maximum_spanning_forest_selected",
        ],
    )
    return MethodResult(
        method_name="maximum_spanning_forest",
        target="edge",
        statistics=statistics,
        primary_statistic="maximum_spanning_forest_selected",
        output_type="score",
        preferred_direction="higher",
        parameters={"weight": weight, "tie_policy": "stable_edge_id"},
        metadata=MAXIMUM_SPANNING_FOREST_METADATA,
        warnings=_warnings(weights, selected_ids),
    )


def _edge_weights(network: Network, *, weight: str | None) -> dict[int, float]:
    weights: dict[int, float] = {}
    for source_id, target_id, attributes in network.graph.edges(data=True):
        edge_id = int(attributes[EDGE_ID_ATTR])
        if weight is None:
            weights[edge_id] = 1.0
            continue
        weights[edge_id] = _numeric_edge_weight(
            attributes,
            weight=weight,
            source_id=source_id,
            target_id=target_id,
        )
    return weights


def _numeric_edge_weight(
    attributes: Mapping[str, object],
    *,
    weight: str,
    source_id: int,
    target_id: int,
) -> float:
    if weight not in attributes:
        raise ValidationError(
            f"Edge ({source_id}, {target_id}) is missing required weight "
            f"attribute {weight!r}."
        )
    value = attributes[weight]
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValidationError(
            f"Weight attribute {weight!r} on edge ({source_id}, {target_id}) "
            "must be numeric."
        )
    edge_weight = float(value)
    if not math.isfinite(edge_weight):
        raise ValidationError(
            f"Weight attribute {weight!r} on edge ({source_id}, {target_id}) "
            "must be finite."
        )
    return edge_weight


def _selected_edge_order(
    network: Network,
    weights: Mapping[int, float],
) -> dict[int, int]:
    parent = {node_id: node_id for node_id in network.graph.nodes}
    selected_order: dict[int, int] = {}
    edge_rows = [
        (edge_id, endpoints[0], endpoints[1], weights[edge_id])
        for edge_id, endpoints in network.edge_id_to_endpoints.items()
    ]

    for edge_id, source_id, target_id, _weight in sorted(
        edge_rows,
        key=lambda row: (-row[3], row[0]),
    ):
        if _union(parent, source_id, target_id):
            selected_order[edge_id] = len(selected_order) + 1
    return selected_order


def _find(parent: dict[int, int], node_id: int) -> int:
    root = node_id
    while parent[root] != root:
        root = parent[root]
    while parent[node_id] != node_id:
        next_node = parent[node_id]
        parent[node_id] = root
        node_id = next_node
    return root


def _union(parent: dict[int, int], source_id: int, target_id: int) -> bool:
    source_root = _find(parent, source_id)
    target_root = _find(parent, target_id)
    if source_root == target_root:
        return False
    if source_root < target_root:
        parent[target_root] = source_root
    else:
        parent[source_root] = target_root
    return True


def _warnings(
    weights: Mapping[int, float],
    selected_ids: set[int],
) -> tuple[str, ...]:
    rejected_ids = set(weights).difference(selected_ids)
    selected_weights = {weights[edge_id] for edge_id in selected_ids}
    rejected_weights = {weights[edge_id] for edge_id in rejected_ids}
    if selected_weights.intersection(rejected_weights):
        return (
            "Maximum spanning forest encountered tied weights across selected "
            "and rejected edges; ties were broken by stable edge_id order.",
        )
    return ()
