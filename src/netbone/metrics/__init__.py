"""Internal metric helpers for result summaries."""

from netbone.metrics.connectivity import (
    connected_component_count,
    isolated_node_count,
    strongly_connected_component_count,
    weakly_connected_component_count,
)
from netbone.metrics.registry import describe_metric, list_metrics
from netbone.metrics.retention import (
    edge_retention_fraction,
    fraction,
    node_retention_fraction,
)

__all__ = [
    "connected_component_count",
    "describe_metric",
    "edge_retention_fraction",
    "fraction",
    "isolated_node_count",
    "list_metrics",
    "node_retention_fraction",
    "strongly_connected_component_count",
    "weakly_connected_component_count",
]
