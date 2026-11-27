"""Doubly stochastic edge scoring method."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import networkx as nx
import pandas as pd

from netbone.exceptions import ConfigurationError, ValidationError
from netbone.methods._references import reference_metadata
from netbone.methods._utils import edge_weights
from netbone.network import EDGE_ID_ATTR, Network
from netbone.results import MethodResult

EPSILON_MODES = frozenset({"absolute", "relative"})

DOUBLY_STOCHASTIC_METADATA: dict[str, object] = {
    "name": "doubly_stochastic",
    "display_name": "Doubly Stochastic",
    "target": "edge",
    "output_type": "score",
    "primary_statistic": "doubly_stochastic_score",
    "preferred_direction": "higher",
    "supports_directed": False,
    "supports_weighted": True,
    "requires_weights": True,
    "weight_mode": "required",
    "requires_positive_weights": True,
    "supports_multigraph": False,
    "supports_self_loops": False,
    "default_filter": "threshold",
    "default_filter_parameters": {
        "statistic": "doubly_stochastic_connected_selected",
        "value": 1.0,
        "operator": "equal",
    },
    "default_weight": "auto",
    "default_epsilon": 1e-4,
    "default_epsilon_mode": "relative",
    "epsilon_mode_options": tuple(sorted(EPSILON_MODES)),
    "component_policy": "connected_components",
    "connected_tie_policy": "stable_edge_id",
    **reference_metadata("doubly_stochastic"),
}


def compute_doubly_stochastic(
    network: Network,
    *,
    weight: str = "weight",
    epsilon: float = 1e-4,
    epsilon_mode: str = "relative",
    tolerance: float = 1e-12,
    max_iterations: int = 1000,
) -> MethodResult:
    """Compute Sinkhorn-normalized edge scores."""

    _validate_parameters(epsilon, epsilon_mode, tolerance, max_iterations)
    weights = edge_weights(
        network,
        weight=weight,
        method_name="doubly_stochastic",
        require_positive=True,
    )
    component_result = _sinkhorn_scores(
        network,
        weights,
        epsilon=epsilon,
        epsilon_mode=epsilon_mode,
        tolerance=tolerance,
        max_iterations=max_iterations,
    )
    selected_order = _connected_prefix_order(network, component_result.scores)
    selected_ids = set(selected_order)

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
                "doubly_stochastic_weight": weights[edge_id],
                "doubly_stochastic_score": component_result.scores[edge_id],
                "doubly_stochastic_connected_order": selected_order.get(edge_id),
                "doubly_stochastic_connected_selected": (
                    1.0 if edge_id in selected_ids else 0.0
                ),
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
            "doubly_stochastic_weight",
            "doubly_stochastic_score",
            "doubly_stochastic_connected_order",
            "doubly_stochastic_connected_selected",
        ],
    )
    warnings = (
        ()
        if component_result.converged
        else (
            "Doubly stochastic normalization reached max_iterations before "
            "row and column sums met the requested tolerance.",
        )
    )
    return MethodResult(
        method_name="doubly_stochastic",
        target="edge",
        statistics=statistics,
        primary_statistic="doubly_stochastic_score",
        output_type="score",
        preferred_direction="higher",
        parameters={
            "weight": weight,
            "epsilon": epsilon,
            "epsilon_mode": epsilon_mode,
            "effective_epsilon_by_component": (
                component_result.effective_epsilon_by_component
            ),
            "tolerance": tolerance,
            "max_iterations": max_iterations,
            "iterations": max(component_result.iterations_by_component.values())
            if component_result.iterations_by_component
            else 0,
            "iterations_by_component": component_result.iterations_by_component,
            "component_count": component_result.component_count,
        },
        metadata=DOUBLY_STOCHASTIC_METADATA,
        warnings=warnings,
    )


@dataclass(frozen=True)
class _SinkhornResult:
    scores: dict[int, float]
    iterations_by_component: dict[int, int]
    effective_epsilon_by_component: dict[int, float]
    component_count: int
    converged: bool


def _validate_parameters(
    epsilon: float,
    epsilon_mode: str,
    tolerance: float,
    max_iterations: int,
) -> None:
    if epsilon_mode not in EPSILON_MODES:
        allowed = ", ".join(sorted(EPSILON_MODES))
        raise ConfigurationError(
            f"doubly_stochastic parameter 'epsilon_mode' must be one of: {allowed}."
        )
    if not isinstance(max_iterations, int) or isinstance(max_iterations, bool):
        raise ConfigurationError(
            "doubly_stochastic parameter 'max_iterations' must be an integer."
        )
    if max_iterations <= 0:
        raise ValidationError("max_iterations must be positive.")
    for name, value in {"epsilon": epsilon, "tolerance": tolerance}.items():
        if not isinstance(value, float | int) or isinstance(value, bool):
            raise ConfigurationError(
                f"doubly_stochastic parameter {name!r} must be numeric."
            )
        if not math.isfinite(float(value)) or float(value) <= 0.0:
            raise ValidationError(f"{name} must be finite and positive.")


def _sinkhorn_scores(
    network: Network,
    weights: dict[int, float],
    *,
    epsilon: float,
    epsilon_mode: str,
    tolerance: float,
    max_iterations: int,
) -> _SinkhornResult:
    scores: dict[int, float] = {}
    iterations_by_component: dict[int, int] = {}
    effective_epsilon_by_component: dict[int, float] = {}
    all_converged = True

    components = _connected_components(network)
    for component_id, component_nodes in enumerate(components):
        component_edge_ids = _component_edge_ids(network, component_nodes)
        if not component_edge_ids:
            continue

        effective_epsilon = _effective_epsilon(
            epsilon,
            epsilon_mode=epsilon_mode,
            component_weights=[weights[edge_id] for edge_id in component_edge_ids],
        )
        matrix, node_index = _component_matrix(
            network,
            weights,
            component_nodes=component_nodes,
            component_edge_ids=component_edge_ids,
            effective_epsilon=effective_epsilon,
        )
        iterations, converged = _normalize_matrix(
            matrix,
            tolerance=tolerance,
            max_iterations=max_iterations,
        )
        all_converged = all_converged and converged
        iterations_by_component[component_id] = iterations
        effective_epsilon_by_component[component_id] = effective_epsilon
        scores.update(
            _edge_scores(
                network,
                matrix,
                node_index=node_index,
                edge_ids=component_edge_ids,
            )
        )
    return _SinkhornResult(
        scores=scores,
        iterations_by_component=iterations_by_component,
        effective_epsilon_by_component=effective_epsilon_by_component,
        component_count=len(components),
        converged=all_converged,
    )


def _connected_components(network: Network) -> list[tuple[int, ...]]:
    components = [
        tuple(sorted(component)) for component in nx.connected_components(network.graph)
    ]
    return sorted(components, key=lambda component: component[0] if component else -1)


def _component_edge_ids(
    network: Network,
    component_nodes: tuple[int, ...],
) -> list[int]:
    node_set = set(component_nodes)
    return [
        edge_id
        for edge_id, (source_id, target_id) in network.edge_id_to_endpoints.items()
        if source_id in node_set and target_id in node_set
    ]


def _effective_epsilon(
    epsilon: float,
    *,
    epsilon_mode: str,
    component_weights: list[float],
) -> float:
    if epsilon_mode == "absolute":
        return epsilon
    mean_weight = sum(component_weights) / len(component_weights)
    return epsilon * mean_weight


def _component_matrix(
    network: Network,
    weights: dict[int, float],
    *,
    component_nodes: tuple[int, ...],
    component_edge_ids: list[int],
    effective_epsilon: float,
) -> tuple[list[list[float]], dict[int, int]]:
    node_index = {node_id: index for index, node_id in enumerate(component_nodes)}
    node_count = len(component_nodes)
    matrix = [[effective_epsilon for _ in range(node_count)] for _ in range(node_count)]
    for edge_id in component_edge_ids:
        source_id, target_id = network.edge_id_to_endpoints[edge_id]
        source_index = node_index[source_id]
        target_index = node_index[target_id]
        matrix[source_index][target_index] = weights[edge_id] + effective_epsilon
        matrix[target_index][source_index] = weights[edge_id] + effective_epsilon
    return matrix, node_index


def _normalize_matrix(
    matrix: list[list[float]],
    *,
    tolerance: float,
    max_iterations: int,
) -> tuple[int, bool]:
    converged = False
    iterations = 0
    for iteration in range(1, max_iterations + 1):
        _normalize_rows(matrix)
        _normalize_columns(matrix)
        iterations = iteration
        if _max_sum_error(matrix) <= tolerance:
            converged = True
            break
    return iterations, converged


def _normalize_rows(matrix: list[list[float]]) -> None:
    for row in matrix:
        row_sum = sum(row)
        if row_sum == 0.0:
            continue
        for index, value in enumerate(row):
            row[index] = value / row_sum


def _normalize_columns(matrix: list[list[float]]) -> None:
    for column_index in range(len(matrix)):
        column_sum = sum(row[column_index] for row in matrix)
        if column_sum == 0.0:
            continue
        for row in matrix:
            row[column_index] = row[column_index] / column_sum


def _max_sum_error(matrix: list[list[float]]) -> float:
    row_error = max(abs(sum(row) - 1.0) for row in matrix) if matrix else 0.0
    column_error = 0.0
    if matrix:
        column_error = max(
            abs(sum(row[index] for row in matrix) - 1.0) for index in range(len(matrix))
        )
    return max(row_error, column_error)


def _edge_scores(
    network: Network,
    matrix: list[list[float]],
    *,
    node_index: dict[int, int],
    edge_ids: list[int],
) -> dict[int, float]:
    scores: dict[int, float] = {}
    for edge_id in edge_ids:
        source_id, target_id = network.edge_id_to_endpoints[edge_id]
        source_index = node_index[source_id]
        target_index = node_index[target_id]
        scores[edge_id] = (
            matrix[source_index][target_index] + matrix[target_index][source_index]
        ) / 2.0
    return scores


def _connected_prefix_order(
    network: Network,
    scores: dict[int, float],
) -> dict[int, int]:
    selected_order: dict[int, int] = {}
    next_order = 1
    for component_nodes in _connected_components(network):
        component_edge_ids = _component_edge_ids(network, component_nodes)
        if not component_edge_ids:
            continue

        candidate = nx.Graph()
        candidate.add_nodes_from(component_nodes)
        edge_rows = [
            (
                edge_id,
                network.edge_id_to_endpoints[edge_id][0],
                network.edge_id_to_endpoints[edge_id][1],
                scores[edge_id],
            )
            for edge_id in component_edge_ids
        ]
        for edge_id, source_id, target_id, _score in sorted(
            edge_rows,
            key=lambda row: (-row[3], row[0]),
        ):
            candidate.add_edge(source_id, target_id)
            selected_order[edge_id] = next_order
            next_order += 1
            if nx.is_connected(candidate):
                break
    return selected_order
