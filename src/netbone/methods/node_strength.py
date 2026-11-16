"""Node strength scoring method."""

from __future__ import annotations

import math
from collections.abc import Mapping
from numbers import Real
from typing import Any

import pandas as pd

from netbone.exceptions import ValidationError
from netbone.network import Network
from netbone.results import MethodResult

NODE_STRENGTH_METADATA: dict[str, object] = {
    "name": "node_strength",
    "display_name": "Node Strength",
    "target": "node",
    "output_type": "score",
    "primary_statistic": "node_strength",
    "preferred_direction": "higher",
    "supports_directed": False,
    "supports_weighted": True,
    "requires_weights": True,
    "requires_positive_weights": False,
    "supports_multigraph": False,
    "supports_self_loops": False,
    "default_filter": "fraction",
    "default_filter_parameters": {
        "fraction": 0.1,
    },
    "default_weight": "weight",
}


def compute_node_strength(
    network: Network,
    *,
    weight: str = "weight",
) -> MethodResult:
    """Compute weighted degree, or strength, for every node.

    Args:
        network: Normalized simple undirected network to score.
        weight: Edge attribute containing finite numeric weights.

    Raises:
        ValidationError: If a configured weight is missing, non-numeric,
            boolean, NaN, or infinite.
    """

    strengths = {node_id: 0.0 for node_id in network.graph.nodes}
    for source_id, target_id, attributes in network.graph.edges(data=True):
        edge_weight = _numeric_edge_weight(
            attributes,
            weight=weight,
            source_id=source_id,
            target_id=target_id,
        )
        strengths[source_id] += edge_weight
        strengths[target_id] += edge_weight

    rows: list[dict[str, Any]] = []
    for node_id in sorted(network.graph.nodes):
        rows.append(
            {
                "node_id": node_id,
                "node": network.node_id_to_original[node_id],
                "node_strength": strengths[node_id],
            }
        )

    statistics = pd.DataFrame(
        rows,
        columns=["node_id", "node", "node_strength"],
    )
    return MethodResult(
        method_name="node_strength",
        target="node",
        statistics=statistics,
        primary_statistic="node_strength",
        output_type="score",
        preferred_direction="higher",
        parameters={"weight": weight},
        metadata=NODE_STRENGTH_METADATA,
        warnings=(),
    )


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
