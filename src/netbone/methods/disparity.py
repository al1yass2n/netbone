"""Disparity backbone scoring method."""

from __future__ import annotations

import math
from numbers import Real
from typing import Any

import pandas as pd

from netbone.exceptions import ConfigurationError, ValidationError
from netbone.network import EDGE_ID_ATTR, Network
from netbone.results import MethodResult

P_VALUE_AGGREGATIONS = frozenset({"average", "in", "max", "min", "out"})
DIRECTED_ONLY_AGGREGATIONS = frozenset({"in", "out"})
LEAF_POLICIES = frozenset({"ignore", "zero"})

DISPARITY_METADATA: dict[str, object] = {
    "name": "disparity",
    "display_name": "Disparity Filter",
    "target": "edge",
    "output_type": "pvalue",
    "primary_statistic": "disparity_pvalue",
    "preferred_direction": "lower",
    "supports_directed": True,
    "directed_semantics": "source_outgoing_and_target_incoming_distributions",
    "supports_weighted": True,
    "requires_weights": True,
    "weight_mode": "required",
    "default_weight": "auto",
    "requires_positive_weights": True,
    "supports_multigraph": False,
    "supports_self_loops": False,
    "default_filter": "significance",
    "default_pvalue_aggregation": "min",
    "pvalue_aggregation_options": tuple(sorted(P_VALUE_AGGREGATIONS)),
    "default_leaf_policy": "zero",
    "leaf_policy_options": tuple(sorted(LEAF_POLICIES)),
    "reference": "Serrano, Boguna, and Vespignani, PNAS 106(16) (2009).",
    "doi": "10.1073/pnas.0808904106",
}


def compute_disparity(
    network: Network,
    *,
    weight: str = "weight",
    pvalue_aggregation: str = "min",
    leaf_policy: str = "zero",
) -> MethodResult:
    """Compute edge p-values from the disparity filter.

    For each endpoint of an edge, the method computes the fraction of that
    endpoint's strength carried by the edge, then evaluates the disparity null
    model p-value `(1 - fraction) ** (degree - 1)`. Endpoint p-values are
    combined into the method-specific primary statistic `disparity_pvalue`.
    For a directed arc, the source value uses its outgoing distribution and the
    target value uses its incoming distribution.

    Args:
        network: Normalized simple directed or undirected network to score.
        weight: Edge attribute containing finite positive weights.
        pvalue_aggregation: How to combine endpoint p-values. `min` keeps an
            edge that is significant for at least one endpoint, `max` requires
            both, and `average` takes their mean. On directed graphs, `out`
            uses only the source's outgoing test (important for the sender) and
            `in` only the target's incoming test (important for the receiver).
        leaf_policy: How degree-one endpoints contribute. `zero` (default)
            gives a leaf endpoint p-value `0.0`, while `ignore` leaves it out
            of the aggregation when the other endpoint is available.

    Raises:
        ConfigurationError: If a method parameter value is invalid.
        ValidationError: If a required weight is missing, non-numeric,
            non-finite, zero, or negative.
    """

    if pvalue_aggregation not in P_VALUE_AGGREGATIONS:
        allowed = ", ".join(sorted(P_VALUE_AGGREGATIONS))
        raise ConfigurationError(
            f"disparity parameter 'pvalue_aggregation' must be one of: {allowed}."
        )
    if pvalue_aggregation in DIRECTED_ONLY_AGGREGATIONS and not network.directed:
        raise ConfigurationError(
            f"disparity pvalue_aggregation={pvalue_aggregation!r} needs a directed "
            "graph; an undirected edge has no source or target end. Use 'min', "
            "'max', or 'average'."
        )
    if leaf_policy not in LEAF_POLICIES:
        allowed = ", ".join(sorted(LEAF_POLICIES))
        raise ConfigurationError(
            f"disparity parameter 'leaf_policy' must be one of: {allowed}."
        )

    weights = _edge_weights(network, weight=weight)
    source_strengths: dict[int, float] = {
        node_id: 0.0 for node_id in network.graph.nodes
    }
    target_strengths = (
        {node_id: 0.0 for node_id in network.graph.nodes}
        if network.directed
        else source_strengths
    )
    source_degrees: dict[int, int] = dict(
        network.graph.out_degree() if network.directed else network.graph.degree()
    )
    target_degrees: dict[int, int] = (
        dict(network.graph.in_degree()) if network.directed else source_degrees
    )

    for edge_id, edge_weight in weights.items():
        source_id, target_id = network.edge_id_to_endpoints[edge_id]
        source_strengths[source_id] += edge_weight
        target_strengths[target_id] += edge_weight

    rows: list[dict[str, Any]] = []
    for source_id, target_id, attributes in sorted(
        network.graph.edges(data=True),
        key=lambda edge: edge[2][EDGE_ID_ATTR],
    ):
        edge_id = int(attributes[EDGE_ID_ATTR])
        edge_weight = weights[edge_id]
        source_fraction = edge_weight / source_strengths[source_id]
        target_fraction = edge_weight / target_strengths[target_id]
        source_pvalue = _endpoint_pvalue(
            source_fraction,
            source_degrees[source_id],
            leaf_policy=leaf_policy,
        )
        target_pvalue = _endpoint_pvalue(
            target_fraction,
            target_degrees[target_id],
            leaf_policy=leaf_policy,
        )
        disparity_pvalue = _aggregate_pvalues(
            (source_pvalue, target_pvalue),
            pvalue_aggregation=pvalue_aggregation,
        )
        rows.append(
            {
                "edge_id": edge_id,
                "source_id": source_id,
                "target_id": target_id,
                "source": network.node_id_to_original[source_id],
                "target": network.node_id_to_original[target_id],
                "disparity_weight": edge_weight,
                "disparity_source_fraction": source_fraction,
                "disparity_target_fraction": target_fraction,
                "disparity_source_pvalue": source_pvalue,
                "disparity_target_pvalue": target_pvalue,
                "disparity_pvalue": disparity_pvalue,
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
            "disparity_weight",
            "disparity_source_fraction",
            "disparity_target_fraction",
            "disparity_source_pvalue",
            "disparity_target_pvalue",
            "disparity_pvalue",
        ],
    )
    return MethodResult(
        method_name="disparity",
        target="edge",
        statistics=statistics,
        primary_statistic="disparity_pvalue",
        output_type="pvalue",
        preferred_direction="lower",
        parameters={
            "weight": weight,
            "pvalue_aggregation": pvalue_aggregation,
            "leaf_policy": leaf_policy,
        },
        metadata=DISPARITY_METADATA,
        warnings=(),
    )


def _edge_weights(network: Network, *, weight: str) -> dict[int, float]:
    weights: dict[int, float] = {}
    for source_id, target_id, attributes in network.graph.edges(data=True):
        edge_id = int(attributes[EDGE_ID_ATTR])
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
        if edge_weight <= 0.0:
            raise ValidationError(
                f"Weight attribute {weight!r} on edge ({source_id}, {target_id}) "
                "must be positive for disparity scoring."
            )
        weights[edge_id] = edge_weight
    return weights


def _endpoint_pvalue(
    fraction: float,
    degree: int,
    *,
    leaf_policy: str,
) -> float | None:
    if degree <= 1:
        return 0.0 if leaf_policy == "zero" else None
    return max(0.0, min(1.0, (1.0 - fraction) ** (degree - 1)))


def _aggregate_pvalues(
    pvalues: tuple[float | None, float | None],
    *,
    pvalue_aggregation: str,
) -> float:
    if pvalue_aggregation == "out":
        pvalues = (pvalues[0], None)
    elif pvalue_aggregation == "in":
        pvalues = (None, pvalues[1])
    available = [pvalue for pvalue in pvalues if pvalue is not None]
    if not available:
        return 1.0
    if pvalue_aggregation == "min":
        return min(available)
    if pvalue_aggregation == "max":
        return max(available)
    return sum(available) / len(available)
