"""Edge betweenness centrality scoring method."""

from __future__ import annotations

import math
from collections.abc import Mapping
from numbers import Real
from typing import Any

import networkx as nx
import pandas as pd

from netbone.exceptions import ConfigurationError, ValidationError
from netbone.network import EDGE_ID_ATTR, Network
from netbone.results import MethodResult

DISTANCE_TRANSFORMS = frozenset({"identity", "inverse"})
DISTANCE_ATTR = "_netbone_edge_betweenness_distance"

EDGE_BETWEENNESS_METADATA: dict[str, object] = {
    "name": "edge_betweenness",
    "display_name": "Edge Betweenness Centrality",
    "target": "edge",
    "output_type": "score",
    "primary_statistic": "edge_betweenness",
    "preferred_direction": "higher",
    "supports_directed": False,
    "supports_weighted": True,
    "requires_weights": False,
    "weight_mode": "optional",
    "requires_positive_weights": True,
    "supports_multigraph": False,
    "supports_self_loops": False,
    "default_filter": "fraction",
    "default_filter_parameters": {
        "fraction": 0.1,
    },
    "default_weight": "auto",
    "default_distance_transform": "inverse",
    "distance_transform_options": tuple(sorted(DISTANCE_TRANSFORMS)),
    "default_normalized": True,
    "reference": "Girvan and Newman, PNAS 99(12): 7821-7826 (2002).",
    "doi": "10.1073/pnas.122653799",
}


def compute_edge_betweenness(
    network: Network,
    *,
    weight: str | None = None,
    distance_transform: str = "inverse",
    normalized: bool = True,
) -> MethodResult:
    """Compute edge betweenness centrality scores.

    Edge betweenness is the fraction of shortest paths between node pairs that
    pass through an edge. When `weight` is provided, Netbone converts edge
    weights into shortest-path distances before calling NetworkX's
    implementation.

    Args:
        network: Normalized simple undirected network to score.
        weight: Optional edge attribute. Pass `None` for unweighted shortest
            paths.
        distance_transform: `inverse` for strength weights or `identity` when
            weights already represent shortest-path distances.
        normalized: Whether NetworkX should normalize centrality scores.

    Raises:
        ConfigurationError: If `distance_transform` is unknown.
        ValidationError: If a configured weight is missing, non-numeric,
            non-finite, non-positive for transformed shortest-path distances,
            or boolean.
    """

    if distance_transform not in DISTANCE_TRANSFORMS:
        allowed = ", ".join(sorted(DISTANCE_TRANSFORMS))
        raise ConfigurationError(
            "edge_betweenness parameter 'distance_transform' must be one of: "
            f"{allowed}."
        )

    weights, distances = _edge_weights_and_distances(
        network,
        weight=weight,
        distance_transform=distance_transform,
    )
    centrality = _centrality_by_edge_id(
        network,
        distances=distances,
        weighted=weight is not None,
        normalized=normalized,
    )

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
                "edge_betweenness_weight": weights[edge_id],
                "edge_betweenness_distance": distances[edge_id],
                "edge_betweenness": centrality[edge_id],
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
            "edge_betweenness_weight",
            "edge_betweenness_distance",
            "edge_betweenness",
        ],
    )
    return MethodResult(
        method_name="edge_betweenness",
        target="edge",
        statistics=statistics,
        primary_statistic="edge_betweenness",
        output_type="score",
        preferred_direction="higher",
        parameters={
            "weight": weight,
            "distance_transform": distance_transform,
            "normalized": normalized,
        },
        metadata=EDGE_BETWEENNESS_METADATA,
        warnings=(),
    )


def _edge_weights_and_distances(
    network: Network,
    *,
    weight: str | None,
    distance_transform: str,
) -> tuple[dict[int, float], dict[int, float]]:
    weights: dict[int, float] = {}
    distances: dict[int, float] = {}
    for source_id, target_id, attributes in network.graph.edges(data=True):
        edge_id = int(attributes[EDGE_ID_ATTR])
        edge_weight = (
            1.0
            if weight is None
            else _numeric_edge_weight(
                attributes,
                weight=weight,
                source_id=source_id,
                target_id=target_id,
            )
        )
        edge_distance = _distance(
            edge_weight,
            distance_transform=distance_transform,
            source_id=source_id,
            target_id=target_id,
        )
        weights[edge_id] = edge_weight
        distances[edge_id] = edge_distance
    return weights, distances


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


def _distance(
    edge_weight: float,
    *,
    distance_transform: str,
    source_id: int,
    target_id: int,
) -> float:
    if distance_transform == "inverse":
        if edge_weight <= 0.0:
            raise ValidationError(
                f"Weight on edge ({source_id}, {target_id}) must be positive "
                "for edge_betweenness with distance_transform='inverse'."
            )
        return 1.0 / edge_weight
    if edge_weight <= 0.0:
        raise ValidationError(
            f"Weight on edge ({source_id}, {target_id}) must define a positive "
            "distance for edge_betweenness with distance_transform='identity'."
        )
    return edge_weight


def _centrality_by_edge_id(
    network: Network,
    *,
    distances: Mapping[int, float],
    weighted: bool,
    normalized: bool,
) -> dict[int, float]:
    graph = nx.Graph()
    graph.add_nodes_from(network.graph.nodes)
    for edge_id, (source_id, target_id) in network.edge_id_to_endpoints.items():
        graph.add_edge(source_id, target_id, **{DISTANCE_ATTR: distances[edge_id]})

    centrality = nx.edge_betweenness_centrality(
        graph,
        normalized=normalized,
        weight=DISTANCE_ATTR if weighted else None,
    )
    by_edge_id: dict[int, float] = {}
    for edge_id, endpoints in network.edge_id_to_endpoints.items():
        source_id, target_id = endpoints
        edge_key = (source_id, target_id)
        reverse_key = (target_id, source_id)
        by_edge_id[edge_id] = float(
            centrality[edge_key] if edge_key in centrality else centrality[reverse_key]
        )
    return by_edge_id
