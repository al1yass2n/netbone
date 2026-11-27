"""Globally and Locally Adaptive Network Backbone scoring method."""

from __future__ import annotations

import math
from typing import Any

import networkx as nx
import pandas as pd

from netbone.exceptions import ConfigurationError, ValidationError
from netbone.methods._utils import edge_weights
from netbone.network import EDGE_ID_ATTR, Network
from netbone.results import MethodResult

GLANB_DISTANCE_ATTR = "_netbone_glanb_distance"

GLANB_METADATA: dict[str, object] = {
    "name": "glanb",
    "display_name": "Globally and Locally Adaptive Network Backbone",
    "target": "edge",
    "output_type": "pvalue",
    "primary_statistic": "glanb_significance",
    "preferred_direction": "lower",
    "supports_directed": False,
    "supports_weighted": True,
    "requires_weights": False,
    "weight_mode": "optional",
    "requires_positive_weights": True,
    "supports_multigraph": False,
    "supports_self_loops": False,
    "default_filter": "significance",
    "default_weight": "auto",
    "requires_parameter": ("c",),
    "reference": "Zhang et al., PLoS ONE 9(6): e100428 (2014).",
    "doi": "10.1371/journal.pone.0100428",
}


def compute_glanb(
    network: Network,
    *,
    weight: str | None = None,
    c: float,
) -> MethodResult:
    """Compute GLANB edge significance values."""

    c_value = _validate_c(c)
    weights = edge_weights(
        network,
        weight=weight,
        method_name="glanb",
        require_positive=True,
    )
    distances = {
        edge_id: 1.0 / value if weight is not None else 1.0
        for edge_id, value in weights.items()
    }
    involvement = _endpoint_involvement(network, distances)
    significance = _endpoint_significance(network, involvement, c=c_value)

    rows: list[dict[str, Any]] = []
    for source_id, target_id, attributes in sorted(
        network.graph.edges(data=True),
        key=lambda edge: edge[2][EDGE_ID_ATTR],
    ):
        edge_id = int(attributes[EDGE_ID_ATTR])
        source_significance = significance[edge_id].get(source_id)
        target_significance = significance[edge_id].get(target_id)
        edge_significance = _aggregate_significance(
            source_significance,
            target_significance,
        )
        rows.append(
            {
                "edge_id": edge_id,
                "source_id": source_id,
                "target_id": target_id,
                "source": network.node_id_to_original[source_id],
                "target": network.node_id_to_original[target_id],
                "glanb_weight": weights[edge_id],
                "glanb_distance": distances[edge_id],
                "glanb_source_involvement": involvement[edge_id][source_id],
                "glanb_target_involvement": involvement[edge_id][target_id],
                "glanb_source_significance": source_significance,
                "glanb_target_significance": target_significance,
                "glanb_significance": edge_significance,
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
            "glanb_weight",
            "glanb_distance",
            "glanb_source_involvement",
            "glanb_target_involvement",
            "glanb_source_significance",
            "glanb_target_significance",
            "glanb_significance",
        ],
    )
    return MethodResult(
        method_name="glanb",
        target="edge",
        statistics=statistics,
        primary_statistic="glanb_significance",
        output_type="pvalue",
        preferred_direction="lower",
        parameters={"weight": weight, "c": c_value},
        metadata=GLANB_METADATA,
        warnings=(),
    )


def _validate_c(c: float) -> float:
    if not isinstance(c, float | int) or isinstance(c, bool):
        raise ConfigurationError("glanb parameter 'c' must be numeric.")
    value = float(c)
    if not math.isfinite(value):
        raise ValidationError("glanb parameter 'c' must be finite.")
    if value < 0.0:
        raise ValidationError("glanb parameter 'c' must be nonnegative.")
    return value


def _endpoint_involvement(
    network: Network,
    distances: dict[int, float],
) -> dict[int, dict[int, float]]:
    graph = nx.Graph()
    graph.add_nodes_from(network.graph.nodes)
    for edge_id, (source_id, target_id) in network.edge_id_to_endpoints.items():
        graph.add_edge(
            source_id,
            target_id,
            **{GLANB_DISTANCE_ATTR: distances[edge_id]},
        )

    involvement: dict[int, dict[int, float]] = {
        edge_id: {source_id: 0.0, target_id: 0.0}
        for edge_id, (source_id, target_id) in network.edge_id_to_endpoints.items()
    }
    node_count = graph.number_of_nodes()
    if node_count <= 1:
        return involvement

    for source_id in sorted(graph.nodes):
        first_hop_ratios = _first_hop_shortest_path_ratios(graph, source_id)
        for _, neighbor_id, _attributes in graph.edges(source_id, data=True):
            edge_id = int(network.graph.edges[source_id, neighbor_id][EDGE_ID_ATTR])
            involvement[edge_id][source_id] = first_hop_ratios.get(neighbor_id, 0.0) / (
                node_count - 1
            )
    return involvement


def _first_hop_shortest_path_ratios(
    graph: nx.Graph,
    source_id: int,
) -> dict[int, float]:
    distances = nx.single_source_dijkstra_path_length(
        graph,
        source_id,
        weight=GLANB_DISTANCE_ATTR,
    )
    path_counts: dict[int, float] = {source_id: 1.0}
    first_hop_counts: dict[int, dict[int, float]] = {source_id: {}}

    for node_id in sorted(distances, key=lambda value: (distances[value], value)):
        if node_id == source_id:
            continue
        path_counts[node_id] = 0.0
        first_hop_counts[node_id] = {}
        for predecessor_id in sorted(graph.neighbors(node_id)):
            edge_distance = float(
                graph.edges[node_id, predecessor_id][GLANB_DISTANCE_ATTR]
            )
            predecessor_distance = distances.get(predecessor_id)
            if predecessor_distance is None:
                continue
            if not math.isclose(
                predecessor_distance + edge_distance,
                distances[node_id],
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                continue

            predecessor_paths = path_counts.get(predecessor_id, 0.0)
            path_counts[node_id] += predecessor_paths
            if predecessor_id == source_id:
                first_hop_counts[node_id][node_id] = (
                    first_hop_counts[node_id].get(node_id, 0.0) + predecessor_paths
                )
                continue
            for first_hop, count in first_hop_counts.get(predecessor_id, {}).items():
                first_hop_counts[node_id][first_hop] = (
                    first_hop_counts[node_id].get(first_hop, 0.0) + count
                )

    ratios: dict[int, float] = {}
    for target_id, total_paths in path_counts.items():
        if target_id == source_id or total_paths == 0.0:
            continue
        for first_hop, count in first_hop_counts[target_id].items():
            ratios[first_hop] = ratios.get(first_hop, 0.0) + (count / total_paths)
    return ratios


def _endpoint_significance(
    network: Network,
    involvement: dict[int, dict[int, float]],
    *,
    c: float,
) -> dict[int, dict[int, float | None]]:
    significance: dict[int, dict[int, float | None]] = {}
    for edge_id, endpoint_values in involvement.items():
        significance[edge_id] = {}
        for node_id, value in endpoint_values.items():
            degree = network.graph.degree[node_id]
            if degree <= 1:
                significance[edge_id][node_id] = None
                continue
            significance[edge_id][node_id] = _endpoint_statistic(value, degree, c=c)
    return significance


def _endpoint_statistic(value: float, degree: int, *, c: float) -> float:
    """Return ``(1 - value) ** ((degree - 1) ** c)`` without overflowing.

    A large ``c`` can make the exponent exceed the float range. The limit is
    then exact: 0 when the involvement is positive and 1 when it is zero.
    """

    try:
        exponent = float(degree - 1) ** c
    except OverflowError:
        exponent = math.inf
    return (1.0 - value) ** exponent


def _aggregate_significance(
    source_significance: float | None,
    target_significance: float | None,
) -> float:
    values = [
        value
        for value in (source_significance, target_significance)
        if value is not None
    ]
    if not values:
        return 1.0
    return min(values)
