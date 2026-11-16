"""Baseline edge-weight scoring method."""

from __future__ import annotations

import math
from numbers import Real
from typing import Any

import pandas as pd

from netbone.exceptions import ValidationError
from netbone.network import EDGE_ID_ATTR, Network
from netbone.results import MethodResult

EDGE_WEIGHT_METADATA: dict[str, object] = {
    "name": "edge_weight",
    "display_name": "Edge Weight",
    "target": "edge",
    "output_type": "score",
    "primary_statistic": "score",
    "preferred_direction": "higher",
    "supports_directed": False,
    "supports_weighted": True,
    "requires_weights": False,
    "supports_multigraph": False,
}


def compute_edge_weight(
    network: Network,
    *,
    weight: str | None = None,
) -> MethodResult:
    """Compute one edge score per edge from a numeric weight attribute.

    Args:
        network: Normalized network to score.
        weight: Edge attribute containing numeric weights. When omitted, every
            edge receives score `1.0`.

    Raises:
        ValidationError: If a requested weight attribute is missing or not
            finite numeric.
    """

    rows: list[dict[str, Any]] = []
    for source_id, target_id, attributes in sorted(
        network.graph.edges(data=True),
        key=lambda edge: edge[2][EDGE_ID_ATTR],
    ):
        edge_id = attributes[EDGE_ID_ATTR]
        score = _edge_score(
            attributes=attributes,
            weight=weight,
            source_id=source_id,
            target_id=target_id,
        )
        rows.append(
            {
                "edge_id": edge_id,
                "source_id": source_id,
                "target_id": target_id,
                "source": network.node_id_to_original[source_id],
                "target": network.node_id_to_original[target_id],
                "score": score,
            }
        )

    statistics = pd.DataFrame(
        rows,
        columns=["edge_id", "source_id", "target_id", "source", "target", "score"],
    )
    return MethodResult(
        method_name="edge_weight",
        target="edge",
        statistics=statistics,
        primary_statistic="score",
        output_type="score",
        preferred_direction="higher",
        parameters={"weight": weight},
        metadata=EDGE_WEIGHT_METADATA,
        warnings=(),
    )


def _edge_score(
    *,
    attributes: dict[str, object],
    weight: str | None,
    source_id: int,
    target_id: int,
) -> float:
    if weight is None:
        return 1.0

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
    score = float(value)
    if not math.isfinite(score):
        raise ValidationError(
            f"Weight attribute {weight!r} on edge ({source_id}, {target_id}) "
            "must be finite."
        )
    return score
