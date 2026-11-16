"""Result containers for scoring, filtering, and extraction."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from numbers import Integral
from types import MappingProxyType

import networkx as nx
import pandas as pd

from netbone.exceptions import ValidationError
from netbone.metrics.connectivity import (
    connected_component_count,
    isolated_node_count,
    strongly_connected_component_count,
    weakly_connected_component_count,
)
from netbone.metrics.retention import edge_retention_fraction, node_retention_fraction

VALID_TARGETS = frozenset({"node", "edge"})
VALID_OUTPUT_TYPES = frozenset({"score", "pvalue", "custom"})
VALID_DIRECTIONS = frozenset({"higher", "lower"})
EDGE_STATISTICS_COLUMNS = frozenset(
    {"edge_id", "source_id", "target_id", "source", "target"}
)
NODE_STATISTICS_COLUMNS = frozenset({"node_id", "node"})


@dataclass(frozen=True)
class MethodResult:
    """Normalized statistics returned by a scoring method."""

    method_name: str
    target: str
    statistics: pd.DataFrame
    primary_statistic: str
    output_type: str
    preferred_direction: str
    parameters: Mapping[str, object]
    metadata: Mapping[str, object]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate result metadata and freeze mapping fields."""

        if self.target not in VALID_TARGETS:
            raise ValidationError(
                f"MethodResult target must be one of {sorted(VALID_TARGETS)}."
            )
        if self.output_type not in VALID_OUTPUT_TYPES:
            raise ValidationError(
                f"MethodResult output_type must be one of {sorted(VALID_OUTPUT_TYPES)}."
            )
        if self.preferred_direction not in VALID_DIRECTIONS:
            raise ValidationError(
                "MethodResult preferred_direction must be one of "
                f"{sorted(VALID_DIRECTIONS)}."
            )
        if self.primary_statistic not in self.statistics.columns:
            raise ValidationError(
                f"Primary statistic {self.primary_statistic!r} is not present "
                "in the statistics table."
            )
        if self.target == "edge":
            missing_columns = EDGE_STATISTICS_COLUMNS.difference(
                self.statistics.columns
            )
            if missing_columns:
                missing = ", ".join(sorted(missing_columns))
                raise ValidationError(
                    f"Edge MethodResult statistics must include column(s): {missing}."
                )
            if self.statistics["edge_id"].duplicated().any():
                raise ValidationError(
                    "Edge MethodResult edge_id values must be unique."
                )
        if self.target == "node":
            missing_columns = NODE_STATISTICS_COLUMNS.difference(
                self.statistics.columns
            )
            if missing_columns:
                missing = ", ".join(sorted(missing_columns))
                raise ValidationError(
                    f"Node MethodResult statistics must include column(s): {missing}."
                )
            if self.statistics["node_id"].duplicated().any():
                raise ValidationError(
                    "Node MethodResult node_id values must be unique."
                )

        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
        object.__setattr__(self, "warnings", tuple(self.warnings))

    def to_dict(self) -> dict[str, object]:
        """Return a minimal JSON-compatible summary of the method result."""

        return {
            "method": self.method_name,
            "target": self.target,
            "output_type": self.output_type,
            "primary_statistic": self.primary_statistic,
            "preferred_direction": self.preferred_direction,
            "parameters": dict(self.parameters),
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "statistics": {
                "row_count": len(self.statistics),
                "columns": list(self.statistics.columns),
            },
        }


@dataclass(frozen=True)
class Selection:
    """A normalized selection produced by a filter."""

    target: str
    selected_ids: tuple[int, ...]
    rejected_ids: tuple[int, ...]
    statistic: str
    parameters: Mapping[str, object]
    mask: pd.Series
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate selected and rejected identifiers."""

        if self.target not in VALID_TARGETS:
            raise ValidationError(
                f"Selection target must be one of {sorted(VALID_TARGETS)}."
            )

        selected = tuple(self.selected_ids)
        rejected = tuple(self.rejected_ids)
        for label, values in (("selected_ids", selected), ("rejected_ids", rejected)):
            invalid = [
                value
                for value in values
                if isinstance(value, bool) or not isinstance(value, Integral)
            ]
            if invalid:
                raise ValidationError(
                    f"Selection {label} must contain integer identifiers."
                )
            if len(set(values)) != len(values):
                raise ValidationError(f"Selection {label} cannot contain duplicates.")
        overlap = set(selected).intersection(rejected)
        if overlap:
            raise ValidationError("Selection ids cannot be both selected and rejected.")
        if len(self.mask) != len(selected) + len(rejected):
            raise ValidationError(
                "Selection mask length must match selected plus rejected id count."
            )

        object.__setattr__(
            self, "selected_ids", tuple(int(value) for value in selected)
        )
        object.__setattr__(
            self, "rejected_ids", tuple(int(value) for value in rejected)
        )
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))
        object.__setattr__(self, "warnings", tuple(self.warnings))

    def summary(self) -> dict[str, object]:
        """Return counts describing this selection."""

        total = len(self.selected_ids) + len(self.rejected_ids)
        selected_fraction = len(self.selected_ids) / total if total else 0.0
        return {
            "target": self.target,
            "statistic": self.statistic,
            "selected_count": len(self.selected_ids),
            "rejected_count": len(self.rejected_ids),
            "selected_fraction": selected_fraction,
        }

    def to_dict(self) -> dict[str, object]:
        """Return a minimal JSON-compatible summary of this selection."""

        return {
            **self.summary(),
            "selected_ids": list(self.selected_ids),
            "rejected_ids": list(self.rejected_ids),
            "parameters": dict(self.parameters),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class BackboneResult:
    """Final result of applying a selection to a network."""

    graph: nx.Graph
    original_graph: nx.Graph
    method_result: MethodResult
    selection: Selection
    pipeline_config: Mapping[str, object]
    context: str | None
    network_metadata: Mapping[str, object] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @property
    def statistics(self) -> pd.DataFrame:
        """Return the method statistics table used for this extraction."""

        return self.method_result.statistics

    @property
    def node_fraction(self) -> float:
        """Return the fraction of original nodes present in the backbone graph."""

        return node_retention_fraction(self.original_graph, self.graph)

    @property
    def edge_fraction(self) -> float:
        """Return the fraction of original edges present in the backbone graph."""

        return edge_retention_fraction(self.original_graph, self.graph)

    def __post_init__(self) -> None:
        """Freeze mapping and warning fields."""

        object.__setattr__(
            self, "pipeline_config", MappingProxyType(dict(self.pipeline_config))
        )
        object.__setattr__(
            self, "network_metadata", MappingProxyType(dict(self.network_metadata))
        )
        object.__setattr__(self, "warnings", tuple(self.warnings))

    def summary(self) -> dict[str, object]:
        """Return a compact summary of graph retention and connectivity."""

        backbone_nodes = self.graph.number_of_nodes()
        backbone_edges = self.graph.number_of_edges()
        summary = {
            "method": self.method_result.method_name,
            "filter": self.selection.parameters.get("strategy"),
            "original_node_count": self.original_graph.number_of_nodes(),
            "original_edge_count": self.original_graph.number_of_edges(),
            "backbone_node_count": backbone_nodes,
            "backbone_edge_count": backbone_edges,
            "node_fraction": self.node_fraction,
            "edge_fraction": self.edge_fraction,
            "drop_isolates": self.selection.parameters.get("drop_isolates", False),
            "isolated_node_count": isolated_node_count(self.graph),
        }
        if self.graph.is_directed():
            summary["weakly_connected_component_count"] = (
                weakly_connected_component_count(self.graph)
            )
            summary["strongly_connected_component_count"] = (
                strongly_connected_component_count(self.graph)
            )
        else:
            summary["connected_component_count"] = connected_component_count(self.graph)
        if self.selection.target == "edge":
            summary["selected_edge_count"] = len(self.selection.selected_ids)
        if self.selection.target == "node":
            summary["selected_node_count"] = len(self.selection.selected_ids)
        return summary

    def to_dict(self) -> dict[str, object]:
        """Return a minimal JSON-compatible summary of the backbone result."""

        return {
            "summary": self.summary(),
            "method_result": self.method_result.to_dict(),
            "selection": self.selection.to_dict(),
            "pipeline": dict(self.pipeline_config),
            "network_metadata": dict(self.network_metadata),
            "warnings": list(self.warnings),
            "has_context": self.context is not None,
        }
