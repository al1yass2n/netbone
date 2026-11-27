"""Coscia and Neffke's Noise Corrected backbone scoring."""

from __future__ import annotations

import math
import sys
from collections import defaultdict
from typing import Any

import pandas as pd

from netbone.methods._references import reference_metadata
from netbone.methods._utils import integer_edge_weights
from netbone.network import Network
from netbone.results import MethodResult

NOISE_CORRECTED_METADATA: dict[str, object] = {
    "name": "noise_corrected",
    "display_name": "Noise Corrected",
    "target": "edge",
    "output_type": "score",
    "primary_statistic": "noise_corrected_z",
    "preferred_direction": "higher",
    "supports_directed": True,
    "directed_semantics": "source_outgoing_and_target_incoming_margins",
    "supports_weighted": True,
    "requires_weights": True,
    "weight_mode": "required",
    "requires_positive_weights": True,
    "requires_integer_weights": True,
    "supports_multigraph": False,
    "supports_self_loops": False,
    "default_filter": "threshold",
    "default_filter_parameters": {"value": 1.64, "operator": "greater"},
    "default_weight": "auto",
    **reference_metadata("noise_corrected"),
}


def compute_noise_corrected(
    network: Network,
    *,
    weight: str = "weight",
) -> MethodResult:
    """Score count-weighted edges using the authors' Bayesian reference code."""
    counts = integer_edge_weights(network, weight=weight, method_name="noise_corrected")
    outgoing: dict[int, int] = defaultdict(int)
    incoming: dict[int, int] = defaultdict(int)
    for edge_id, count in counts.items():
        source, target = network.edge_id_to_endpoints[edge_id]
        outgoing[source] += count
        incoming[target] += count
        if not network.directed:
            outgoing[target] += count
            incoming[source] += count
    total = sum(outgoing.values())

    rows: list[dict[str, Any]] = []
    undefined = 0
    for edge_id, count in sorted(counts.items()):
        source, target = network.edge_id_to_endpoints[edge_id]
        lift, deviation = _edge_statistics(
            count, outgoing[source], incoming[target], total
        )
        if deviation is None:
            # For degenerate margins the lift is zero and the reference excludes it.
            z = 0.0
            undefined += 1
        elif deviation == 0.0:
            z = math.copysign(sys.float_info.max, lift) if lift else 0.0
        else:
            z = lift / deviation
        rows.append(
            {
                "edge_id": edge_id,
                "source_id": source,
                "target_id": target,
                "source": network.node_id_to_original[source],
                "target": network.node_id_to_original[target],
                "noise_corrected_score": lift,
                "noise_corrected_stddev": deviation,
                "noise_corrected_z": z,
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
            "noise_corrected_score",
            "noise_corrected_stddev",
            "noise_corrected_z",
        ],
    )
    warning = (
        f"Noise Corrected could not estimate uncertainty for {undefined} edge(s) "
        "because a source or target accounts for all interactions. "
        "These edges have zero standardized score and the default cutoff excludes them."
    )
    return MethodResult(
        method_name="noise_corrected",
        target="edge",
        statistics=statistics,
        primary_statistic="noise_corrected_z",
        output_type="score",
        preferred_direction="higher",
        parameters={"weight": weight},
        metadata=NOISE_CORRECTED_METADATA,
        warnings=(warning,) if undefined else (),
    )


def _edge_statistics(
    count: int, outgoing: int, incoming: int, total: int
) -> tuple[float, float | None]:
    if outgoing == total or incoming == total:
        return 0.0, None
    product = outgoing * incoming
    kappa = total / product
    lift = kappa * count
    source_share = outgoing / total
    target_share = incoming / total
    prior_mean = source_share * target_share
    prior_variance = prior_mean * (1 - source_share) * (1 - target_share) / (total - 1)

    # Match the authors' Python beta prior, which differs from printed Eq. (8).
    # Scale both beta shape parameters by the prior variance before forming
    # the posterior mean to avoid dividing by a small prior variance.
    alpha = prior_mean**2 * (1 - prior_mean) - prior_mean * prior_variance
    beta = prior_mean * (1 - prior_mean**2) - (1 - prior_mean) * prior_variance
    posterior = (alpha + count * prior_variance) / (
        alpha + beta + total * prior_variance
    )
    # Differentiating the global total in kappa gives the reference's total
    # numerator, where the expression printed in the preprint uses the edge count.
    derivative_numerator = product - total * (outgoing + incoming)
    lift_slope = (total * product + count * derivative_numerator) / product**2
    slope = 2 * lift_slope / (lift + 1) ** 2
    deviation = abs(slope) * math.sqrt(total * posterior * (1 - posterior))
    return (lift - 1) / (lift + 1), deviation
