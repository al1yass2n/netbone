"""Marginal likelihood statistical backbone scoring method."""

from __future__ import annotations

from typing import Any

import pandas as pd

from netbone.exceptions import ValidationError
from netbone.methods._utils import binomial_upper_tail, integer_edge_weights
from netbone.network import EDGE_ID_ATTR, Network
from netbone.results import MethodResult

MARGINAL_LIKELIHOOD_METADATA: dict[str, object] = {
    "name": "marginal_likelihood",
    "display_name": "Marginal Likelihood Filter",
    "target": "edge",
    "output_type": "pvalue",
    "primary_statistic": "marginal_likelihood_pvalue",
    "preferred_direction": "lower",
    "supports_directed": False,
    "supports_weighted": True,
    "requires_weights": True,
    "weight_mode": "required",
    "requires_positive_weights": True,
    "requires_integer_weights": True,
    "supports_multigraph": False,
    "supports_self_loops": False,
    "default_filter": "significance",
    "default_weight": "auto",
    "reference": "Dianati, Physical Review E 93, 012304 (2016).",
    "doi": "10.1103/PhysRevE.93.012304",
}


def compute_marginal_likelihood(
    network: Network,
    *,
    weight: str = "weight",
) -> MethodResult:
    """Compute marginal-likelihood binomial-test p-values for each edge."""

    weights = integer_edge_weights(
        network,
        weight=weight,
        method_name="marginal_likelihood",
    )
    total_weight = sum(weights.values())
    strengths = _node_strengths(network, weights)

    rows: list[dict[str, Any]] = []
    for source_id, target_id, attributes in sorted(
        network.graph.edges(data=True),
        key=lambda edge: edge[2][EDGE_ID_ATTR],
    ):
        edge_id = int(attributes[EDGE_ID_ATTR])
        source_strength = strengths[source_id]
        target_strength = strengths[target_id]
        try:
            probability = (
                (source_strength / total_weight)
                * (target_strength / total_weight)
                / 2.0
            )
            pvalue = binomial_upper_tail(
                observed=weights[edge_id],
                trials=total_weight,
                probability=probability,
                inclusive=True,
            )
        except OverflowError as exc:
            raise ValidationError(
                "Edge weights are too large for marginal_likelihood scoring; the "
                f"total weight {total_weight:.3e} cannot be represented. Rescale "
                "the counts before scoring."
            ) from exc
        rows.append(
            {
                "edge_id": edge_id,
                "source_id": source_id,
                "target_id": target_id,
                "source": network.node_id_to_original[source_id],
                "target": network.node_id_to_original[target_id],
                "marginal_likelihood_weight": weights[edge_id],
                "marginal_likelihood_source_strength": source_strength,
                "marginal_likelihood_target_strength": target_strength,
                "marginal_likelihood_probability": probability,
                "marginal_likelihood_pvalue": pvalue,
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
            "marginal_likelihood_weight",
            "marginal_likelihood_source_strength",
            "marginal_likelihood_target_strength",
            "marginal_likelihood_probability",
            "marginal_likelihood_pvalue",
        ],
    )
    return MethodResult(
        method_name="marginal_likelihood",
        target="edge",
        statistics=statistics,
        primary_statistic="marginal_likelihood_pvalue",
        output_type="pvalue",
        preferred_direction="lower",
        parameters={"weight": weight},
        metadata=MARGINAL_LIKELIHOOD_METADATA,
        warnings=(),
    )


def _node_strengths(network: Network, weights: dict[int, int]) -> dict[int, int]:
    strengths = {node_id: 0 for node_id in network.graph.nodes}
    for edge_id, edge_weight in weights.items():
        source_id, target_id = network.edge_id_to_endpoints[edge_id]
        strengths[source_id] += edge_weight
        strengths[target_id] += edge_weight
    return strengths
