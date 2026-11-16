"""Metric registry for comparison tables."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from numbers import Real
from types import MappingProxyType

import networkx as nx

from netbone.compare.alignment import (
    aligned_score_table,
    score_incompatibility,
    spearman,
)
from netbone.exceptions import (
    CompatibilityError,
    ConfigurationError,
    UndefinedMetricError,
)
from netbone.metrics.connectivity import (
    connected_component_count,
    isolated_node_count,
    strongly_connected_component_count,
    weakly_connected_component_count,
)
from netbone.results import BackboneResult

MetricValue = int | float
SingleMetricCompute = Callable[[BackboneResult], MetricValue]
PairwiseMetricCompute = Callable[[BackboneResult, BackboneResult], MetricValue]


@dataclass(frozen=True)
class MetricDefinition:
    """Registered metric metadata and execution hook."""

    name: str
    scope: str
    metadata: Mapping[str, object]
    compute: SingleMetricCompute | PairwiseMetricCompute

    def __post_init__(self) -> None:
        """Freeze metadata for registry callers."""

        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


def list_metrics(*, scope: str | None = None) -> tuple[str, ...]:
    """Return registered metric names."""

    if scope is None:
        return tuple(sorted(_METRICS))
    return tuple(
        sorted(name for name, metric in _METRICS.items() if metric.scope == scope)
    )


def describe_metric(name: str) -> dict[str, object]:
    """Return JSON-compatible metadata for a registered metric."""

    metric = get_metric(name)
    return {
        "name": metric.name,
        "scope": metric.scope,
        **dict(metric.metadata),
    }


def get_metric(name: str) -> MetricDefinition:
    """Return a registered metric definition.

    Raises:
        ConfigurationError: If the metric name is unknown.
    """

    try:
        return _METRICS[name]
    except KeyError as exc:
        allowed = ", ".join(list_metrics())
        raise ConfigurationError(
            f"Unknown metric {name!r}. Available metrics: {allowed}."
        ) from exc


def _node_count(result: BackboneResult) -> int:
    return result.graph.number_of_nodes()


def _edge_count(result: BackboneResult) -> int:
    return result.graph.number_of_edges()


def _node_retention(result: BackboneResult) -> float:
    return result.node_fraction


def _edge_retention(result: BackboneResult) -> float:
    return result.edge_fraction


def _weight_retention(result: BackboneResult) -> float:
    weight_attribute, require_attribute = _weight_attribute(result)
    original_weight = _total_edge_weight(
        result.original_graph,
        weight_attribute=weight_attribute,
        require_attribute=require_attribute,
    )
    if original_weight == 0.0:
        return 0.0
    return (
        _total_edge_weight(
            result.graph,
            weight_attribute=weight_attribute,
            require_attribute=require_attribute,
        )
        / original_weight
    )


def _connected_component_count(result: BackboneResult) -> int:
    return connected_component_count(result.graph)


def _isolated_node_count(result: BackboneResult) -> int:
    return isolated_node_count(result.graph)


def _weakly_connected_component_count(result: BackboneResult) -> int:
    return weakly_connected_component_count(result.graph)


def _strongly_connected_component_count(result: BackboneResult) -> int:
    return strongly_connected_component_count(result.graph)


def _node_overlap(left: BackboneResult, right: BackboneResult) -> int:
    return len(_node_set(left).intersection(_node_set(right)))


def _edge_overlap(left: BackboneResult, right: BackboneResult) -> int:
    return len(_edge_set(left).intersection(_edge_set(right)))


def _node_jaccard(left: BackboneResult, right: BackboneResult) -> float:
    return _jaccard(_node_set(left), _node_set(right))


def _edge_jaccard(left: BackboneResult, right: BackboneResult) -> float:
    return _jaccard(_edge_set(left), _edge_set(right))


def _node_overlap_coefficient(left: BackboneResult, right: BackboneResult) -> float:
    return _overlap_coefficient(_node_set(left), _node_set(right))


def _edge_overlap_coefficient(left: BackboneResult, right: BackboneResult) -> float:
    return _overlap_coefficient(_edge_set(left), _edge_set(right))


def _score_spearman(
    left: BackboneResult,
    right: BackboneResult,
) -> float:
    explanation = score_incompatibility(left, right)
    if explanation:
        raise CompatibilityError(explanation)
    aligned = aligned_score_table(
        "left",
        "right",
        left.method_result,
        right.method_result,
        directed=left.original_graph.is_directed(),
    )
    value = spearman(aligned["importance_rank_a"], aligned["importance_rank_b"])
    if value is None:
        raise UndefinedMetricError(
            "Spearman correlation is undefined for fewer than two aligned "
            "values or constant ranks."
        )
    return value


def _weight_attribute(result: BackboneResult) -> tuple[str, bool]:
    weight = result.method_result.parameters.get("weight")
    if isinstance(weight, str):
        return weight, True
    return "weight", False


def _total_edge_weight(
    result_graph: nx.Graph,
    *,
    weight_attribute: str,
    require_attribute: bool,
) -> float:
    total = 0.0
    for source, target, data in result_graph.edges(data=True):
        if require_attribute and weight_attribute not in data:
            raise CompatibilityError(
                "weight_retention metric requires edge weight attribute "
                f"{weight_attribute!r}; edge ({source!r}, {target!r}) is missing it."
            )
        value = data.get(weight_attribute, 1.0)
        if isinstance(value, bool) or not isinstance(value, Real):
            raise CompatibilityError(
                "weight_retention metric requires finite numeric, non-negative edge "
                f"weight attributes; edge ({source!r}, {target!r}) has invalid "
                f"{weight_attribute!r} value {value!r}."
            )
        weight = float(value)
        if not math.isfinite(weight) or weight < 0.0:
            raise CompatibilityError(
                "weight_retention metric requires finite numeric, non-negative edge "
                f"weight attributes; edge ({source!r}, {target!r}) has invalid "
                f"{weight_attribute!r} value {value!r}."
            )
        total += weight
    return total


def _node_set(result: BackboneResult) -> set[object]:
    return set(result.graph.nodes())


def _edge_set(result: BackboneResult) -> set[object]:
    if result.graph.is_directed():
        return set(result.graph.edges())
    return {frozenset((source, target)) for source, target in result.graph.edges()}


NodeOrEdgeSet = set[object]


def _jaccard(left: NodeOrEdgeSet, right: NodeOrEdgeSet) -> float:
    union = left.union(right)
    if not union:
        return 1.0
    return len(left.intersection(right)) / len(union)


def _overlap_coefficient(
    left: NodeOrEdgeSet,
    right: NodeOrEdgeSet,
) -> float:
    smaller = min(len(left), len(right))
    if smaller == 0:
        return 1.0 if not left and not right else 0.0
    return len(left.intersection(right)) / smaller


_METRICS: dict[str, MetricDefinition] = {
    "node_count": MetricDefinition(
        name="node_count",
        scope="single",
        metadata={"category": "retention"},
        compute=_node_count,
    ),
    "edge_count": MetricDefinition(
        name="edge_count",
        scope="single",
        metadata={"category": "retention"},
        compute=_edge_count,
    ),
    "node_retention": MetricDefinition(
        name="node_retention",
        scope="single",
        metadata={"category": "retention"},
        compute=_node_retention,
    ),
    "edge_retention": MetricDefinition(
        name="edge_retention",
        scope="single",
        metadata={"category": "retention"},
        compute=_edge_retention,
    ),
    "weight_retention": MetricDefinition(
        name="weight_retention",
        scope="single",
        metadata={"category": "retention"},
        compute=_weight_retention,
    ),
    "connected_component_count": MetricDefinition(
        name="connected_component_count",
        scope="single",
        metadata={"category": "connectivity"},
        compute=_connected_component_count,
    ),
    "weakly_connected_component_count": MetricDefinition(
        name="weakly_connected_component_count",
        scope="single",
        metadata={"category": "connectivity", "graph_type": "directed"},
        compute=_weakly_connected_component_count,
    ),
    "strongly_connected_component_count": MetricDefinition(
        name="strongly_connected_component_count",
        scope="single",
        metadata={"category": "connectivity", "graph_type": "directed"},
        compute=_strongly_connected_component_count,
    ),
    "isolated_node_count": MetricDefinition(
        name="isolated_node_count",
        scope="single",
        metadata={"category": "connectivity"},
        compute=_isolated_node_count,
    ),
    "node_overlap": MetricDefinition(
        name="node_overlap",
        scope="pairwise",
        metadata={"category": "similarity"},
        compute=_node_overlap,
    ),
    "edge_overlap": MetricDefinition(
        name="edge_overlap",
        scope="pairwise",
        metadata={"category": "similarity"},
        compute=_edge_overlap,
    ),
    "node_jaccard": MetricDefinition(
        name="node_jaccard",
        scope="pairwise",
        metadata={"category": "similarity"},
        compute=_node_jaccard,
    ),
    "edge_jaccard": MetricDefinition(
        name="edge_jaccard",
        scope="pairwise",
        metadata={"category": "similarity"},
        compute=_edge_jaccard,
    ),
    "node_overlap_coefficient": MetricDefinition(
        name="node_overlap_coefficient",
        scope="pairwise",
        metadata={"category": "similarity"},
        compute=_node_overlap_coefficient,
    ),
    "edge_overlap_coefficient": MetricDefinition(
        name="edge_overlap_coefficient",
        scope="pairwise",
        metadata={"category": "similarity"},
        compute=_edge_overlap_coefficient,
    ),
    "score_spearman": MetricDefinition(
        name="score_spearman",
        scope="pairwise",
        metadata={"category": "score_alignment", "rank_orientation": "importance"},
        compute=_score_spearman,
    ),
}
