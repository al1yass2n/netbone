"""Link-prediction similarity scoring for backbone extraction."""

from __future__ import annotations

import math
from numbers import Real
from typing import Any

import networkx as nx
import pandas as pd

from netbone.exceptions import ConfigurationError, ValidationError
from netbone.methods._utils import edge_weights
from netbone.network import EDGE_ID_ATTR, Network
from netbone.results import MethodResult

SIMILARITIES = frozenset({"local_path", "preferential_attachment", "shortest_path"})
DISTANCE_TRANSFORMS = frozenset({"identity", "inverse"})
EDGE_WEIGHT_ATTR = "_netbone_link_prediction_weight"
EDGE_DISTANCE_ATTR = "_netbone_link_prediction_distance"
DIRECTED_SEMANTICS_WARNING = (
    "Directed link_prediction scoring uses Netbone's explicit directed extension "
    "of the published framework: arc u -> v uses forward replacement paths from "
    "u to v, and preferential attachment uses source out-connectivity times target "
    "in-connectivity."
)

LINK_PREDICTION_METADATA: dict[str, object] = {
    "name": "link_prediction",
    "display_name": "Link Prediction Backbone Framework",
    "target": "edge",
    "output_type": "score",
    "primary_statistic": "link_prediction_similarity",
    "preferred_direction": "higher",
    "supports_directed": True,
    "supports_weighted": True,
    "requires_weights": False,
    "weight_mode": "optional",
    "requires_positive_weights": True,
    "uses_weights": True,
    "supports_multigraph": False,
    "supports_self_loops": False,
    "default_filter": "fraction",
    "default_filter_parameters": {
        "fraction": 0.1,
    },
    "requires_fraction_direction": True,
    "similarity_options": tuple(sorted(SIMILARITIES)),
    "default_weight": "auto",
    "default_weight_alpha": 1.0,
    "default_distance_transform": "inverse",
    "distance_transform_options": tuple(sorted(DISTANCE_TRANSFORMS)),
    "default_epsilon": 1.0,
    "directed_semantics": {
        "preferential_attachment": "source out-degree/strength times target "
        "in-degree/strength",
        "shortest_path": "forward shortest path from source to target",
        "local_path": "forward directed paths of length two and three from source "
        "to target",
    },
    "reference": "Link prediction perspective on network backbone extraction, "
    "Applied Network Science (2025).",
    "doi": "10.1007/s41109-025-00705-y",
}


def compute_link_prediction(
    network: Network,
    *,
    similarity: str,
    epsilon: float = 1.0,
    weight: str | None = None,
    weight_alpha: float = 1.0,
    distance_transform: str = "inverse",
) -> MethodResult:
    """Compute edge similarity scores using an edge-removed graph."""

    if similarity not in SIMILARITIES:
        allowed = ", ".join(sorted(SIMILARITIES))
        raise ConfigurationError(
            f"link_prediction parameter 'similarity' must be one of: {allowed}."
        )
    epsilon_value = _validate_epsilon(epsilon)
    weight_alpha_value = _validate_weight_alpha(weight_alpha)
    if distance_transform not in DISTANCE_TRANSFORMS:
        allowed = ", ".join(sorted(DISTANCE_TRANSFORMS))
        raise ConfigurationError(
            f"link_prediction parameter 'distance_transform' must be one of: {allowed}."
        )
    if weight is None and distance_transform != "inverse":
        raise ConfigurationError(
            "link_prediction parameter 'distance_transform' only applies when "
            "parameter 'weight' is provided."
        )
    original_weights = edge_weights(
        network,
        weight=weight,
        method_name="link_prediction",
        require_positive=weight is not None,
    )
    effective_weights = _effective_weights(
        network,
        weights=original_weights,
        weight_alpha=weight_alpha_value,
    )
    connection_strengths, path_distances = _connection_strengths_and_distances(
        network,
        effective_weights=effective_weights,
        distance_transform=distance_transform,
    )
    graph = _working_graph(network, connection_strengths, path_distances)
    weighted = weight is not None

    rows: list[dict[str, Any]] = []
    for source_id, target_id, attributes in sorted(
        network.graph.edges(data=True),
        key=lambda edge: edge[2][EDGE_ID_ATTR],
    ):
        edge_id = int(attributes[EDGE_ID_ATTR])
        graph.remove_edge(source_id, target_id)
        score, support = _score_removed_edge(
            graph,
            source_id,
            target_id,
            similarity=similarity,
            epsilon=epsilon_value,
            weighted=weighted,
        )
        graph.add_edge(
            source_id,
            target_id,
            **_working_edge_attributes(
                connection_strengths[edge_id],
                path_distances[edge_id],
            ),
        )
        rows.append(
            {
                "edge_id": edge_id,
                "source_id": source_id,
                "target_id": target_id,
                "source": network.node_id_to_original[source_id],
                "target": network.node_id_to_original[target_id],
                "link_prediction_similarity_method": similarity,
                "link_prediction_edge_weight": original_weights[edge_id],
                "link_prediction_edge_effective_weight": effective_weights[edge_id],
                "link_prediction_edge_strength": connection_strengths[edge_id],
                "link_prediction_edge_distance": path_distances[edge_id],
                "link_prediction_similarity": score,
                **support,
            }
        )

    statistics = pd.DataFrame(rows, columns=_columns())
    parameters: dict[str, object] = {"similarity": similarity}
    if weight is not None:
        parameters["weight"] = weight
        parameters["weight_alpha"] = weight_alpha_value
        parameters["distance_transform"] = distance_transform
    if similarity == "local_path":
        parameters["epsilon"] = epsilon_value
    return MethodResult(
        method_name="link_prediction",
        target="edge",
        statistics=statistics,
        primary_statistic="link_prediction_similarity",
        output_type="score",
        preferred_direction="higher",
        parameters=parameters,
        metadata=LINK_PREDICTION_METADATA,
        warnings=(DIRECTED_SEMANTICS_WARNING,) if network.directed else (),
    )


def _validate_epsilon(epsilon: float) -> float:
    if isinstance(epsilon, bool) or not isinstance(epsilon, Real):
        raise ConfigurationError("link_prediction parameter 'epsilon' must be numeric.")
    value = float(epsilon)
    if not math.isfinite(value):
        raise ValidationError("link_prediction parameter 'epsilon' must be finite.")
    if value < 0.0:
        raise ValidationError(
            "link_prediction parameter 'epsilon' must be nonnegative."
        )
    return value


def _validate_weight_alpha(weight_alpha: float) -> float:
    if isinstance(weight_alpha, bool) or not isinstance(weight_alpha, Real):
        raise ConfigurationError(
            "link_prediction parameter 'weight_alpha' must be numeric."
        )
    value = float(weight_alpha)
    if not math.isfinite(value):
        raise ValidationError(
            "link_prediction parameter 'weight_alpha' must be finite."
        )
    return value


def _effective_weights(
    network: Network,
    *,
    weights: dict[int, float],
    weight_alpha: float,
) -> dict[int, float]:
    values: dict[int, float] = {}
    for edge_id, edge_weight in weights.items():
        source_id, target_id = network.edge_id_to_endpoints[edge_id]
        try:
            effective_weight = edge_weight**weight_alpha
        except OverflowError as exc:
            raise ValidationError(
                f"Weight on edge ({source_id}, {target_id}) overflows after applying "
                "link_prediction parameter 'weight_alpha'."
            ) from exc
        if not math.isfinite(effective_weight):
            raise ValidationError(
                f"Weight on edge ({source_id}, {target_id}) must remain finite after "
                "applying link_prediction parameter 'weight_alpha'."
            )
        if effective_weight <= 0.0:
            raise ValidationError(
                f"Weight on edge ({source_id}, {target_id}) must produce a positive "
                "effective weight for link_prediction scoring."
            )
        values[edge_id] = effective_weight
    return values


def _working_graph(
    network: Network,
    connection_strengths: dict[int, float],
    path_distances: dict[int, float],
) -> nx.Graph:
    graph = nx.DiGraph() if network.directed else nx.Graph()
    graph.add_nodes_from(network.graph.nodes)
    for edge_id, (source_id, target_id) in network.edge_id_to_endpoints.items():
        graph.add_edge(
            source_id,
            target_id,
            **_working_edge_attributes(
                connection_strengths[edge_id],
                path_distances[edge_id],
            ),
        )
    return graph


def _connection_strengths_and_distances(
    network: Network,
    *,
    effective_weights: dict[int, float],
    distance_transform: str,
) -> tuple[dict[int, float], dict[int, float]]:
    connection_strengths: dict[int, float] = {}
    path_distances: dict[int, float] = {}
    for edge_id, effective_weight in effective_weights.items():
        source_id, target_id = network.edge_id_to_endpoints[edge_id]
        if distance_transform == "inverse":
            connection_strength = effective_weight
            path_distance = 1.0 / effective_weight
        else:
            path_distance = effective_weight
            connection_strength = 1.0 / effective_weight
        if not math.isfinite(connection_strength) or not math.isfinite(path_distance):
            raise ValidationError(
                f"Weight on edge ({source_id}, {target_id}) must produce finite "
                "link_prediction strength and distance values."
            )
        connection_strengths[edge_id] = connection_strength
        path_distances[edge_id] = path_distance
    return connection_strengths, path_distances


def _working_edge_attributes(
    connection_strength: float,
    path_distance: float,
) -> dict[str, float]:
    return {
        EDGE_WEIGHT_ATTR: connection_strength,
        EDGE_DISTANCE_ATTR: path_distance,
    }


def _score_removed_edge(
    graph: nx.Graph,
    source_id: int,
    target_id: int,
    *,
    similarity: str,
    epsilon: float,
    weighted: bool,
) -> tuple[float, dict[str, object]]:
    if similarity == "preferential_attachment":
        return _preferential_attachment(graph, source_id, target_id)
    if similarity == "shortest_path":
        return _shortest_path_similarity(
            graph,
            source_id,
            target_id,
            weighted=weighted,
        )
    return _local_path_similarity(graph, source_id, target_id, epsilon=epsilon)


def _preferential_attachment(
    graph: nx.Graph,
    source_id: int,
    target_id: int,
) -> tuple[float, dict[str, object]]:
    if isinstance(graph, nx.DiGraph):
        source_degree = int(graph.out_degree[source_id])
        target_degree = int(graph.in_degree[target_id])
        source_strength = _node_strength(graph, source_id, direction="out")
        target_strength = _node_strength(graph, target_id, direction="in")
    else:
        source_degree = int(graph.degree[source_id])
        target_degree = int(graph.degree[target_id])
        source_strength = _node_strength(graph, source_id)
        target_strength = _node_strength(graph, target_id)
    return float(source_strength * target_strength), {
        "link_prediction_source_degree": source_degree,
        "link_prediction_target_degree": target_degree,
        "link_prediction_source_strength": source_strength,
        "link_prediction_target_strength": target_strength,
        "link_prediction_shortest_path_length": None,
        "link_prediction_disconnected": False,
        "link_prediction_paths_length_2": None,
        "link_prediction_paths_length_3": None,
        "link_prediction_weighted_paths_length_2": None,
        "link_prediction_weighted_paths_length_3": None,
    }


def _node_strength(
    graph: nx.Graph,
    node_id: int,
    *,
    direction: str | None = None,
) -> float:
    if isinstance(graph, nx.DiGraph):
        edges = (
            graph.in_edges(node_id, data=True)
            if direction == "in"
            else graph.out_edges(node_id, data=True)
        )
    else:
        edges = graph.edges(node_id, data=True)
    return float(
        sum(
            attributes[EDGE_WEIGHT_ATTR] for _source_id, _target_id, attributes in edges
        )
    )


def _shortest_path_similarity(
    graph: nx.Graph,
    source_id: int,
    target_id: int,
    *,
    weighted: bool,
) -> tuple[float, dict[str, object]]:
    try:
        path_length = float(
            nx.shortest_path_length(
                graph,
                source_id,
                target_id,
                weight=EDGE_DISTANCE_ATTR if weighted else None,
            )
        )
    except nx.NetworkXNoPath:
        path_length = 0.0
        disconnected = True
        score = 0.0
    else:
        disconnected = False
        score = 1.0 / path_length
    return score, {
        "link_prediction_source_degree": None,
        "link_prediction_target_degree": None,
        "link_prediction_source_strength": None,
        "link_prediction_target_strength": None,
        "link_prediction_shortest_path_length": path_length or None,
        "link_prediction_disconnected": disconnected,
        "link_prediction_paths_length_2": None,
        "link_prediction_paths_length_3": None,
        "link_prediction_weighted_paths_length_2": None,
        "link_prediction_weighted_paths_length_3": None,
    }


def _local_path_similarity(
    graph: nx.Graph,
    source_id: int,
    target_id: int,
    *,
    epsilon: float,
) -> tuple[float, dict[str, object]]:
    if isinstance(graph, nx.DiGraph):
        source_neighbors = set(graph.successors(source_id))
        target_neighbors = set(graph.predecessors(target_id))
    else:
        source_neighbors = set(graph.neighbors(source_id))
        target_neighbors = set(graph.neighbors(target_id))
    paths_length_2 = len(source_neighbors.intersection(target_neighbors))
    weighted_paths_length_2 = sum(
        graph.edges[source_id, common_neighbor][EDGE_WEIGHT_ATTR]
        * graph.edges[common_neighbor, target_id][EDGE_WEIGHT_ATTR]
        for common_neighbor in source_neighbors.intersection(target_neighbors)
    )
    paths_length_3 = sum(
        1
        for source_neighbor in source_neighbors
        for target_neighbor in target_neighbors
        if graph.has_edge(source_neighbor, target_neighbor)
    )
    weighted_paths_length_3 = sum(
        graph.edges[source_id, source_neighbor][EDGE_WEIGHT_ATTR]
        * graph.edges[source_neighbor, target_neighbor][EDGE_WEIGHT_ATTR]
        * graph.edges[target_neighbor, target_id][EDGE_WEIGHT_ATTR]
        for source_neighbor in source_neighbors
        for target_neighbor in target_neighbors
        if graph.has_edge(source_neighbor, target_neighbor)
    )
    score = weighted_paths_length_2 + epsilon * weighted_paths_length_3
    return float(score), {
        "link_prediction_source_degree": None,
        "link_prediction_target_degree": None,
        "link_prediction_source_strength": None,
        "link_prediction_target_strength": None,
        "link_prediction_shortest_path_length": None,
        "link_prediction_disconnected": False,
        "link_prediction_paths_length_2": paths_length_2,
        "link_prediction_paths_length_3": paths_length_3,
        "link_prediction_weighted_paths_length_2": float(weighted_paths_length_2),
        "link_prediction_weighted_paths_length_3": float(weighted_paths_length_3),
    }


def _columns() -> list[str]:
    return [
        "edge_id",
        "source_id",
        "target_id",
        "source",
        "target",
        "link_prediction_similarity_method",
        "link_prediction_edge_weight",
        "link_prediction_edge_effective_weight",
        "link_prediction_edge_strength",
        "link_prediction_edge_distance",
        "link_prediction_similarity",
        "link_prediction_source_degree",
        "link_prediction_target_degree",
        "link_prediction_source_strength",
        "link_prediction_target_strength",
        "link_prediction_shortest_path_length",
        "link_prediction_disconnected",
        "link_prediction_paths_length_2",
        "link_prediction_paths_length_3",
        "link_prediction_weighted_paths_length_2",
        "link_prediction_weighted_paths_length_3",
    ]
