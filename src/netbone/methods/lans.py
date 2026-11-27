"""Locally adaptive network sparsification scoring method."""

from __future__ import annotations

import math
from numbers import Real
from typing import Any

import pandas as pd

from netbone.exceptions import ConfigurationError, ValidationError
from netbone.methods._references import reference_metadata
from netbone.network import EDGE_ID_ATTR, Network
from netbone.results import MethodResult

P_VALUE_AGGREGATIONS = frozenset({"average", "in", "max", "min", "out"})
DIRECTED_ONLY_AGGREGATIONS = frozenset({"in", "out"})
LEAF_POLICIES = frozenset({"ignore", "zero"})

LANS_METADATA: dict[str, object] = {
    "name": "lans",
    "display_name": "Locally Adaptive Network Sparsification",
    "target": "edge",
    "output_type": "pvalue",
    "primary_statistic": "lans_pvalue",
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
    **reference_metadata("lans"),
}


def compute_lans(
    network: Network,
    *,
    weight: str = "weight",
    pvalue_aggregation: str = "min",
    leaf_policy: str = "zero",
) -> MethodResult:
    """Compute LANS empirical upper-tail p-values for each edge.

    LANS compares an edge's fractional weight with the empirical distribution
    of fractional weights at both endpoints and combines the two endpoint
    p-values. For directed graphs, an arc is compared with its source node's
    outgoing distribution and its target node's incoming distribution.

    Args:
        network: Normalized simple graph to score.
        weight: Edge attribute containing finite positive weights.
        pvalue_aggregation: How to combine endpoint p-values. `min` keeps an
            edge that is significant for at least one endpoint, `max` requires
            both, and `average` takes their mean. On directed graphs, `out`
            uses only the source's outgoing test (important for the sender) and
            `in` only the target's incoming test (important for the receiver).
        leaf_policy: How degree-one endpoints contribute: `zero` treats the
            leaf endpoint as locally significant, while `ignore` ignores them
            during aggregation when another endpoint is available.

    Raises:
        ConfigurationError: If a method parameter value is invalid.
        ValidationError: If a required weight is missing, non-numeric,
            non-finite, zero, or negative.
    """

    if pvalue_aggregation not in P_VALUE_AGGREGATIONS:
        allowed = ", ".join(sorted(P_VALUE_AGGREGATIONS))
        raise ConfigurationError(
            f"lans parameter 'pvalue_aggregation' must be one of: {allowed}."
        )
    if pvalue_aggregation in DIRECTED_ONLY_AGGREGATIONS and not network.directed:
        raise ConfigurationError(
            f"lans pvalue_aggregation={pvalue_aggregation!r} needs a directed "
            "graph; an undirected edge has no source or target end. Use 'min', "
            "'max', or 'average'."
        )
    if leaf_policy not in LEAF_POLICIES:
        allowed = ", ".join(sorted(LEAF_POLICIES))
        raise ConfigurationError(
            f"lans parameter 'leaf_policy' must be one of: {allowed}."
        )

    weights = _edge_weights(network, weight=weight)
    source_fractions, target_fractions = _endpoint_fractions(network, weights)
    source_pvalues = _endpoint_pvalues(source_fractions, leaf_policy=leaf_policy)
    target_pvalues = _endpoint_pvalues(target_fractions, leaf_policy=leaf_policy)

    rows: list[dict[str, Any]] = []
    for source_id, target_id, attributes in sorted(
        network.graph.edges(data=True),
        key=lambda edge: edge[2][EDGE_ID_ATTR],
    ):
        edge_id = int(attributes[EDGE_ID_ATTR])
        source_fraction = source_fractions[source_id][edge_id]
        source_pvalue = source_pvalues[source_id][edge_id]
        target_fraction = target_fractions[target_id][edge_id]
        target_pvalue = target_pvalues[target_id][edge_id]
        lans_pvalue = _aggregate_pvalues(
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
                "lans_weight": weights[edge_id],
                "lans_source_fraction": source_fraction,
                "lans_target_fraction": target_fraction,
                "lans_source_pvalue": source_pvalue,
                "lans_target_pvalue": target_pvalue,
                "lans_pvalue": lans_pvalue,
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
            "lans_weight",
            "lans_source_fraction",
            "lans_target_fraction",
            "lans_source_pvalue",
            "lans_target_pvalue",
            "lans_pvalue",
        ],
    )
    return MethodResult(
        method_name="lans",
        target="edge",
        statistics=statistics,
        primary_statistic="lans_pvalue",
        output_type="pvalue",
        preferred_direction="lower",
        parameters={
            "weight": weight,
            "pvalue_aggregation": pvalue_aggregation,
            "leaf_policy": leaf_policy,
        },
        metadata=LANS_METADATA,
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
                "must be positive for LANS scoring."
            )
        weights[edge_id] = edge_weight
    return weights


def _endpoint_fractions(
    network: Network,
    weights: dict[int, float],
) -> tuple[dict[int, dict[int, float]], dict[int, dict[int, float]]]:
    """Return each edge's weight share at its source and at its target.

    Undirected graphs use one incident distribution per node, so both maps
    share it. Directed graphs use outgoing shares at the source and incoming
    shares at the target.
    """

    outgoing: dict[int, float] = {node_id: 0.0 for node_id in network.graph.nodes}
    incoming: dict[int, float] = {node_id: 0.0 for node_id in network.graph.nodes}
    for edge_id, edge_weight in weights.items():
        source_id, target_id = network.edge_id_to_endpoints[edge_id]
        outgoing[source_id] += edge_weight
        incoming[target_id] += edge_weight
    if not network.directed:
        strengths = {
            node_id: outgoing[node_id] + incoming[node_id] for node_id in outgoing
        }
        outgoing = incoming = strengths

    source_fractions: dict[int, dict[int, float]] = {
        node_id: {} for node_id in network.graph.nodes
    }
    target_fractions: dict[int, dict[int, float]] = {
        node_id: {} for node_id in network.graph.nodes
    }
    for edge_id, edge_weight in weights.items():
        source_id, target_id = network.edge_id_to_endpoints[edge_id]
        source_fractions[source_id][edge_id] = edge_weight / outgoing[source_id]
        target_fractions[target_id][edge_id] = edge_weight / incoming[target_id]
    if not network.directed:
        for node_id in network.graph.nodes:
            merged = {**source_fractions[node_id], **target_fractions[node_id]}
            source_fractions[node_id] = merged
            target_fractions[node_id] = merged
    return source_fractions, target_fractions


def _endpoint_pvalues(
    fractions: dict[int, dict[int, float]],
    *,
    leaf_policy: str,
) -> dict[int, dict[int, float | None]]:
    pvalues: dict[int, dict[int, float | None]] = {}
    for node_id, edge_fractions in fractions.items():
        degree = len(edge_fractions)
        if degree <= 1 and leaf_policy == "ignore":
            pvalues[node_id] = {edge_id: None for edge_id in sorted(edge_fractions)}
            continue
        if degree <= 1:
            pvalues[node_id] = {edge_id: 0.0 for edge_id in sorted(edge_fractions)}
            continue

        values = list(edge_fractions.values())
        pvalues[node_id] = {
            edge_id: _upper_tail_pvalue(fraction, values)
            for edge_id, fraction in edge_fractions.items()
        }
    return pvalues


def _upper_tail_pvalue(fraction: float, values: list[float]) -> float:
    empirical_cdf = sum(value <= fraction for value in values) / len(values)
    return max(0.0, min(1.0, 1.0 - empirical_cdf))


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
