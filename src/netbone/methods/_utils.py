"""Shared helpers for built-in scoring methods."""

from __future__ import annotations

import math
from collections.abc import Mapping
from numbers import Real

import networkx as nx

from netbone.exceptions import ConfigurationError, ValidationError
from netbone.network import EDGE_ID_ATTR, Network

DISTANCE_TRANSFORMS = frozenset({"identity", "inverse"})


def edge_weights(
    network: Network,
    *,
    weight: str | None,
    method_name: str,
    require_positive: bool = False,
    require_nonnegative: bool = False,
    require_integer: bool = False,
) -> dict[int, float]:
    """Return finite numeric edge weights keyed by stable edge id."""

    weights: dict[int, float] = {}
    for source_id, target_id, attributes in network.graph.edges(data=True):
        edge_id = int(attributes[EDGE_ID_ATTR])
        if weight is None:
            edge_weight = 1.0
        else:
            edge_weight = numeric_edge_weight(
                attributes,
                weight=weight,
                source_id=source_id,
                target_id=target_id,
            )
        validate_weight_constraints(
            edge_weight,
            source_id=source_id,
            target_id=target_id,
            method_name=method_name,
            require_positive=require_positive,
            require_nonnegative=require_nonnegative,
            require_integer=require_integer,
        )
        weights[edge_id] = edge_weight
    return weights


def integer_edge_weights(
    network: Network,
    *,
    weight: str,
    method_name: str,
    require_positive: bool = True,
) -> dict[int, int]:
    """Return finite integral edge weights keyed by stable edge id."""

    values = edge_weights(
        network,
        weight=weight,
        method_name=method_name,
        require_positive=require_positive,
        require_nonnegative=not require_positive,
        require_integer=True,
    )
    return {edge_id: int(value) for edge_id, value in values.items()}


def numeric_edge_weight(
    attributes: Mapping[str, object],
    *,
    weight: str,
    source_id: int,
    target_id: int,
) -> float:
    """Read one finite numeric edge weight."""

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


def validate_weight_constraints(
    edge_weight: float,
    *,
    source_id: int,
    target_id: int,
    method_name: str,
    require_positive: bool = False,
    require_nonnegative: bool = False,
    require_integer: bool = False,
) -> None:
    """Validate common method-specific weight constraints."""

    if require_positive and edge_weight <= 0.0:
        raise ValidationError(
            f"Weight on edge ({source_id}, {target_id}) must be positive for "
            f"{method_name} scoring."
        )
    if require_nonnegative and edge_weight < 0.0:
        raise ValidationError(
            f"Weight on edge ({source_id}, {target_id}) must be non-negative for "
            f"{method_name} scoring."
        )
    if require_integer and not edge_weight.is_integer():
        raise ValidationError(
            f"Weight on edge ({source_id}, {target_id}) must be an integer count "
            f"for {method_name} scoring."
        )


def edge_weights_and_distances(
    network: Network,
    *,
    weight: str | None,
    distance_transform: str,
    method_name: str,
) -> tuple[dict[int, float], dict[int, float]]:
    """Return edge weights and shortest-path distances by edge id."""

    if distance_transform not in DISTANCE_TRANSFORMS:
        allowed = ", ".join(sorted(DISTANCE_TRANSFORMS))
        raise ConfigurationError(
            f"{method_name} parameter 'distance_transform' must be one of: {allowed}."
        )

    weights = edge_weights(
        network,
        weight=weight,
        method_name=method_name,
    )
    distances: dict[int, float] = {}
    for edge_id, edge_weight in weights.items():
        source_id, target_id = network.edge_id_to_endpoints[edge_id]
        distances[edge_id] = edge_distance(
            edge_weight,
            source_id=source_id,
            target_id=target_id,
            distance_transform=distance_transform,
            method_name=method_name,
        )
    return weights, distances


def edge_distance(
    edge_weight: float,
    *,
    source_id: int,
    target_id: int,
    distance_transform: str,
    method_name: str,
) -> float:
    """Convert a method weight into a shortest-path distance."""

    if distance_transform == "inverse":
        if edge_weight <= 0.0:
            raise ValidationError(
                f"Weight on edge ({source_id}, {target_id}) must be positive "
                f"for {method_name} with distance_transform='inverse'."
            )
        return 1.0 / edge_weight
    if edge_weight <= 0.0:
        raise ValidationError(
            f"Weight on edge ({source_id}, {target_id}) must define a positive "
            f"distance for {method_name} with distance_transform='identity'."
        )
    return edge_weight


def edge_betweenness_by_edge_id(
    network: Network,
    *,
    distances: Mapping[int, float],
    weighted: bool,
    normalized: bool,
    distance_attr: str,
) -> dict[int, float]:
    """Compute NetworkX edge betweenness and return values by stable edge id."""

    graph = nx.Graph()
    graph.add_nodes_from(network.graph.nodes)
    for edge_id, (source_id, target_id) in network.edge_id_to_endpoints.items():
        graph.add_edge(source_id, target_id, **{distance_attr: distances[edge_id]})

    centrality = nx.edge_betweenness_centrality(
        graph,
        normalized=normalized,
        weight=distance_attr if weighted else None,
    )
    values: dict[int, float] = {}
    for edge_id, (source_id, target_id) in network.edge_id_to_endpoints.items():
        edge_key = (source_id, target_id)
        reverse_key = (target_id, source_id)
        values[edge_id] = float(
            centrality[edge_key] if edge_key in centrality else centrality[reverse_key]
        )
    return values


def h_index(values: list[float]) -> int:
    """Return the largest h such that at least h values are >= h."""

    threshold = 0
    for rank, value in enumerate(sorted(values, reverse=True), start=1):
        if value >= rank:
            threshold = rank
        else:
            break
    return threshold


def binomial_upper_tail(
    *,
    observed: int,
    trials: int,
    probability: float,
    inclusive: bool,
) -> float:
    """Return P[X >= observed] or P[X > observed] for X ~ Binomial(n, p)."""

    if trials < 0:
        raise ValueError("Binomial trials must be non-negative.")
    if probability < 0.0 or probability > 1.0 or not math.isfinite(probability):
        raise ValueError("Binomial probability must be finite and between 0 and 1.")

    start = observed if inclusive else observed + 1
    if start <= 0:
        return 1.0
    if start > trials:
        return 0.0
    if probability == 0.0:
        return 0.0
    if probability == 1.0:
        return 1.0 if start <= trials else 0.0

    mode = int(math.floor((trials + 1) * probability))
    if start > mode:
        return _binomial_upper_tail_from_start(
            start=start,
            trials=trials,
            probability=probability,
        )

    lower_tail = _binomial_lower_tail_to_end(
        end=start - 1,
        trials=trials,
        probability=probability,
    )
    return max(0.0, min(1.0, 1.0 - lower_tail))


def _binomial_upper_tail_from_start(
    *,
    start: int,
    trials: int,
    probability: float,
) -> float:
    current = _binomial_pmf(start, trials=trials, probability=probability)
    total = current
    odds = probability / (1.0 - probability)
    for value in range(start, trials):
        if current == 0.0:
            break
        current *= (trials - value) / (value + 1) * odds
        total += current
        if total >= 1.0:
            return 1.0
    return max(0.0, min(1.0, total))


def _binomial_lower_tail_to_end(
    *,
    end: int,
    trials: int,
    probability: float,
) -> float:
    if end < 0:
        return 0.0
    current = _binomial_pmf(end, trials=trials, probability=probability)
    total = current
    inverse_odds = (1.0 - probability) / probability
    for value in range(end, 0, -1):
        if current == 0.0:
            break
        current *= value / (trials - value + 1) * inverse_odds
        total += current
        if total >= 1.0:
            return 1.0
    return max(0.0, min(1.0, total))


def _binomial_pmf(
    value: int,
    *,
    trials: int,
    probability: float,
) -> float:
    log_probability = (
        math.lgamma(trials + 1)
        - math.lgamma(value + 1)
        - math.lgamma(trials - value + 1)
        + value * math.log(probability)
        + (trials - value) * math.log1p(-probability)
    )
    return math.exp(log_probability) if log_probability > -745.0 else 0.0
