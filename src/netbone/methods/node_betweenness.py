"""Node betweenness centrality scoring method."""

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
DISTANCE_ATTR = "_netbone_node_betweenness_distance"

NODE_BETWEENNESS_METADATA: dict[str, object] = {
    "name": "node_betweenness",
    "display_name": "Node Betweenness Centrality",
    "target": "node",
    "output_type": "score",
    "primary_statistic": "node_betweenness",
    "preferred_direction": "higher",
    "supports_directed": False,
    "supports_weighted": True,
    "requires_weights": False,
    "requires_positive_weights": False,
    "supports_multigraph": False,
    "supports_self_loops": False,
    "default_filter": "fraction",
    "default_filter_parameters": {
        "fraction": 0.1,
    },
    "default_weight": None,
    "default_distance_transform": "inverse",
    "distance_transform_options": tuple(sorted(DISTANCE_TRANSFORMS)),
    "default_normalized": True,
    "default_endpoints": False,
    "reference": "Brandes, Journal of Mathematical Sociology 25(2): 163-177 (2001).",
    "doi": "10.1080/0022250X.2001.9990249",
}


def compute_node_betweenness(
    network: Network,
    *,
    weight: str | None = None,
    distance_transform: str = "inverse",
    normalized: bool = True,
    endpoints: bool = False,
) -> MethodResult:
    """Compute node betweenness centrality scores.

    Args:
        network: Normalized simple undirected network to score.
        weight: Optional edge attribute. Pass `None` for unweighted shortest
            paths.
        distance_transform: `inverse` for strength weights or `identity` when
            weights already represent shortest-path distances.
        normalized: Whether NetworkX should normalize centrality scores.
        endpoints: Whether endpoints are included in path counts.

    Raises:
        ConfigurationError: If `distance_transform` is unknown.
        ValidationError: If a configured weight is missing, non-numeric,
            boolean, non-finite, or does not define a positive distance.
    """

    if distance_transform not in DISTANCE_TRANSFORMS:
        allowed = ", ".join(sorted(DISTANCE_TRANSFORMS))
        raise ConfigurationError(
            "node_betweenness parameter 'distance_transform' must be one of: "
            f"{allowed}."
        )

    _, distances = _edge_weights_and_distances(
        network,
        weight=weight,
        distance_transform=distance_transform,
    )
    centrality = _centrality_by_node_id(
        network,
        distances=distances,
        weighted=weight is not None,
        normalized=normalized,
        endpoints=endpoints,
    )

    rows: list[dict[str, Any]] = []
    for node_id in sorted(network.graph.nodes):
        rows.append(
            {
                "node_id": node_id,
                "node": network.node_id_to_original[node_id],
                "node_betweenness": centrality[node_id],
            }
        )

    statistics = pd.DataFrame(
        rows,
        columns=["node_id", "node", "node_betweenness"],
    )
    return MethodResult(
        method_name="node_betweenness",
        target="node",
        statistics=statistics,
        primary_statistic="node_betweenness",
        output_type="score",
        preferred_direction="higher",
        parameters={
            "weight": weight,
            "distance_transform": distance_transform,
            "normalized": normalized,
            "endpoints": endpoints,
        },
        metadata=NODE_BETWEENNESS_METADATA,
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
                "for node_betweenness with distance_transform='inverse'."
            )
        return 1.0 / edge_weight
    if edge_weight <= 0.0:
        raise ValidationError(
            f"Weight on edge ({source_id}, {target_id}) must define a positive "
            "distance for node_betweenness with distance_transform='identity'."
        )
    return edge_weight


def _centrality_by_node_id(
    network: Network,
    *,
    distances: Mapping[int, float],
    weighted: bool,
    normalized: bool,
    endpoints: bool,
) -> dict[int, float]:
    graph = nx.Graph()
    graph.add_nodes_from(network.graph.nodes)
    for edge_id, (source_id, target_id) in network.edge_id_to_endpoints.items():
        graph.add_edge(source_id, target_id, **{DISTANCE_ATTR: distances[edge_id]})

    centrality = nx.betweenness_centrality(
        graph,
        normalized=normalized,
        weight=DISTANCE_ATTR if weighted else None,
        endpoints=endpoints,
    )
    return {node_id: float(value) for node_id, value in centrality.items()}
