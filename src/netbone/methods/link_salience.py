"""Link salience scoring method."""

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

LINK_SALIENCE_METADATA: dict[str, object] = {
    "name": "link_salience",
    "display_name": "Link Salience",
    "target": "edge",
    "output_type": "score",
    "primary_statistic": "link_salience",
    "preferred_direction": "higher",
    "supports_directed": True,
    "directed_semantics": "outgoing_shortest_paths",
    "supports_weighted": True,
    "requires_weights": False,
    "weight_mode": "optional",
    "requires_positive_weights": True,
    "supports_multigraph": False,
    "supports_self_loops": False,
    "default_filter": "threshold",
    "default_filter_parameters": {
        "value": 0.5,
        "operator": "greater_equal",
    },
    "default_weight": "auto",
    "default_distance_transform": "inverse",
    "distance_transform_options": tuple(sorted(DISTANCE_TRANSFORMS)),
    "reference": "Grady, Thiemann, and Brockmann, Nature Communications 3, 864 (2012).",
    "doi": "10.1038/ncomms1847",
}


def compute_link_salience(
    network: Network,
    *,
    weight: str | None = "weight",
    distance_transform: str = "inverse",
) -> MethodResult:
    """Compute edge link salience from shortest-path trees rooted at each node.

    Link salience is the fraction of root nodes whose shortest-path tree or
    shortest-path directed acyclic graph contains an edge. The default
    `distance_transform="inverse"` treats input weights as coupling strengths
    and uses `1 / weight` as the shortest-path distance.

    Args:
        network: Normalized simple graph to score. Directed graphs use
            outgoing shortest paths from each root and preserve arc direction.
        weight: Edge attribute containing numeric weights. Pass `None` for
            unweighted unit-distance salience.
        distance_transform: `inverse` for strength weights or `identity` when
            weights are already shortest-path distances.

    Raises:
        ConfigurationError: If `distance_transform` is unknown.
        ValidationError: If a configured weight is missing, non-numeric,
            non-finite, non-positive for `inverse`, or negative for `identity`.
    """

    if distance_transform not in DISTANCE_TRANSFORMS:
        allowed = ", ".join(sorted(DISTANCE_TRANSFORMS))
        raise ConfigurationError(
            f"link_salience parameter 'distance_transform' must be one of: {allowed}."
        )

    weights, distances = _edge_weights_and_distances(
        network,
        weight=weight,
        distance_transform=distance_transform,
    )
    salience_counts = _salience_counts(network, distances)
    node_count = network.graph.number_of_nodes()

    rows: list[dict[str, Any]] = []
    for source_id, target_id, attributes in sorted(
        network.graph.edges(data=True),
        key=lambda edge: edge[2][EDGE_ID_ATTR],
    ):
        edge_id = int(attributes[EDGE_ID_ATTR])
        count = salience_counts[edge_id]
        rows.append(
            {
                "edge_id": edge_id,
                "source_id": source_id,
                "target_id": target_id,
                "source": network.node_id_to_original[source_id],
                "target": network.node_id_to_original[target_id],
                "link_salience_weight": weights[edge_id],
                "link_salience_distance": distances[edge_id],
                "link_salience_count": count,
                "link_salience": count / node_count if node_count else 0.0,
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
            "link_salience_weight",
            "link_salience_distance",
            "link_salience_count",
            "link_salience",
        ],
    )
    return MethodResult(
        method_name="link_salience",
        target="edge",
        statistics=statistics,
        primary_statistic="link_salience",
        output_type="score",
        preferred_direction="higher",
        parameters={
            "weight": weight,
            "distance_transform": distance_transform,
        },
        metadata=LINK_SALIENCE_METADATA,
        warnings=_warnings(network),
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
        weights[edge_id] = edge_weight
        distances[edge_id] = _distance(
            edge_weight,
            distance_transform=distance_transform,
            source_id=source_id,
            target_id=target_id,
        )
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
                "for link_salience with distance_transform='inverse'."
            )
        return 1.0 / edge_weight
    if edge_weight < 0.0:
        raise ValidationError(
            f"Weight on edge ({source_id}, {target_id}) must be non-negative "
            "for link_salience with distance_transform='identity'."
        )
    return edge_weight


def _salience_counts(
    network: Network,
    distances: Mapping[int, float],
) -> dict[int, int]:
    counts = {edge_id: 0 for edge_id in network.edge_id_to_endpoints}

    for root in sorted(network.graph.nodes):
        root_distances = nx.single_source_dijkstra_path_length(
            network.graph,
            root,
            weight=lambda _source, _target, data: distances[int(data[EDGE_ID_ATTR])],
        )
        for source_id, target_id, attributes in network.graph.edges(data=True):
            edge_id = int(attributes[EDGE_ID_ATTR])
            if _is_shortest_path_edge(
                root_distances,
                source_id,
                target_id,
                distance=distances[edge_id],
                directed=network.directed,
            ):
                counts[edge_id] += 1

    return counts


def _is_shortest_path_edge(
    root_distances: Mapping[int, float],
    source_id: int,
    target_id: int,
    *,
    distance: float,
    directed: bool,
) -> bool:
    source_distance = root_distances.get(source_id)
    target_distance = root_distances.get(target_id)
    if source_distance is None or target_distance is None:
        return False
    forward = math.isclose(
        source_distance + distance,
        target_distance,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )
    if directed:
        return forward
    return forward or math.isclose(
        target_distance + distance,
        source_distance,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )


def _warnings(network: Network) -> tuple[str, ...]:
    if network.graph.number_of_nodes() == 0:
        return ()
    if network.directed:
        if nx.number_strongly_connected_components(network.graph) > 1:
            return (
                "Directed link salience used outgoing shortest paths and all-node "
                "normalization on a graph that is not strongly connected; "
                "unreachable roots contribute zero to an arc's salience.",
            )
        return ()
    if nx.number_connected_components(network.graph) > 1:
        return (
            "Link salience was computed on a disconnected graph; salience is "
            "normalized by all roots, so edges in smaller components cannot "
            "reach salience 1.0.",
        )
    return ()
