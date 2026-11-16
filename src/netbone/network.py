"""NetworkX graph normalization and identity handling."""

from __future__ import annotations

import json
import math
from collections.abc import Hashable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, TypeGuard

import networkx as nx

from netbone.exceptions import CompatibilityError, ValidationError

NODE_ORIGINAL_ATTR = "_netbone_original_id"
EDGE_ID_ATTR = "_netbone_edge_id"
RESERVED_NODE_ATTRIBUTES = frozenset({NODE_ORIGINAL_ATTR})
RESERVED_EDGE_ATTRIBUTES = frozenset({EDGE_ID_ATTR})
ReciprocalMerge = Literal["sum", "mean", "max", "min"]
RECIPROCAL_MERGES = frozenset({"sum", "mean", "max", "min"})
DIRECTIONAL_CONFLICTS_ATTR = "netbone_directional_conflicts"


@dataclass(frozen=True)
class Network:
    """A normalized NetworkX graph with stable internal node and edge ids.

    The stored graph uses integer node identifiers. Original node ids and edge
    attributes are preserved and result graphs are exported with original node
    ids.
    """

    graph: nx.Graph
    context: str | None
    source: str | None
    metadata: Mapping[str, object]
    node_id_to_original: Mapping[int, Hashable]
    original_to_node_id: Mapping[Hashable, int]
    edge_id_to_endpoints: Mapping[int, tuple[int, int]]

    @property
    def node_count(self) -> int:
        """Return the number of nodes in the normalized graph."""

        return self.graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        """Return the number of edges in the normalized graph."""

        return self.graph.number_of_edges()

    @property
    def directed(self) -> bool:
        """Return whether the normalized graph is directed."""

        return self.graph.is_directed()

    @property
    def multigraph(self) -> bool:
        """Return whether the normalized graph is a multigraph."""

        return self.graph.is_multigraph()

    @property
    def weighted(self) -> bool:
        """Return whether any edge has a `weight` attribute."""

        return any("weight" in data for _, _, data in self.graph.edges(data=True))

    def summary(self) -> dict[str, object]:
        """Return a small JSON-compatible summary of the network."""

        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "directed": self.directed,
            "multigraph": self.multigraph,
            "weighted": self.weighted,
            "source": self.source,
            "metadata": dict(self.metadata),
            "has_context": self.context is not None,
        }

    def to_original_graph(
        self,
        *,
        node_ids: Iterable[int] | None = None,
        edge_ids: Iterable[int] | None = None,
        drop_isolates: bool = False,
    ) -> nx.Graph:
        """Return a new NetworkX graph using original node ids.

        Args:
            node_ids: Optional internal node ids to include. When omitted, all
                nodes are eligible unless `edge_ids` and `drop_isolates=True`
                restrict them.
            edge_ids: Optional internal edge ids to include. When omitted, all
                edges between included nodes are included.
            drop_isolates: Whether to omit nodes without retained incident
                edges.

        Raises:
            ValidationError: If unknown node or edge ids are requested.
        """

        selected_node_ids = (
            frozenset(self.node_id_to_original)
            if node_ids is None
            else frozenset(int(node_id) for node_id in node_ids)
        )
        unknown_nodes = selected_node_ids.difference(self.node_id_to_original)
        if unknown_nodes:
            unknown_text = ", ".join(str(node_id) for node_id in sorted(unknown_nodes))
            raise ValidationError(f"Unknown node id(s) requested: {unknown_text}.")

        selected_edge_ids = (
            frozenset(self.edge_id_to_endpoints)
            if edge_ids is None
            else frozenset(edge_ids)
        )
        unknown = selected_edge_ids.difference(self.edge_id_to_endpoints)
        if unknown:
            unknown_text = ", ".join(str(edge_id) for edge_id in sorted(unknown))
            raise ValidationError(f"Unknown edge id(s) requested: {unknown_text}.")

        output = nx.DiGraph() if self.directed else nx.Graph()
        output.graph.update(self.graph.graph)
        retained_internal_nodes: set[int] = set()
        retained_edge_ids: set[int] = set()

        for edge_id in sorted(selected_edge_ids):
            source_id, target_id = self.edge_id_to_endpoints[edge_id]
            if source_id in selected_node_ids and target_id in selected_node_ids:
                retained_internal_nodes.update((source_id, target_id))
                retained_edge_ids.add(edge_id)

        node_ids = (
            sorted(retained_internal_nodes)
            if drop_isolates
            else sorted(selected_node_ids)
        )
        for node_id in node_ids:
            original_id = self.node_id_to_original[node_id]
            attributes = _public_attributes(self.graph.nodes[node_id])
            output.add_node(original_id, **attributes)

        for edge_id in sorted(retained_edge_ids):
            source_id, target_id = self.edge_id_to_endpoints[edge_id]
            original_source = self.node_id_to_original[source_id]
            original_target = self.node_id_to_original[target_id]
            if original_source not in output or original_target not in output:
                continue
            attributes = _public_attributes(self.graph.edges[source_id, target_id])
            output.add_edge(original_source, original_target, **attributes)

        return output

    def to_dict(self) -> dict[str, object]:
        """Return a minimal JSON-compatible summary of this network."""

        return self.summary()


def from_graph(graph: nx.Graph, *, context: str | None = None) -> Network:
    """Normalize a simple NetworkX graph into a `Network`.

    Args:
        graph: A simple `networkx.Graph` or `networkx.DiGraph`.
        context: Optional user-supplied context retained in result metadata.

    Raises:
        CompatibilityError: If the graph type is unsupported.
        ValidationError: If reserved internal attributes are present.
    """

    if not isinstance(graph, nx.Graph):
        raise CompatibilityError(
            "from_graph() requires a networkx.Graph or networkx.DiGraph instance."
        )
    _validate_supported_graph(graph)
    _validate_reserved_attributes(graph)
    return _normalize_graph(graph, context=context, source=None, metadata=None)


def ensure_network(graph_or_network: nx.Graph | Network) -> Network:
    """Return a `Network`, normalizing NetworkX input when needed."""

    if isinstance(graph_or_network, Network):
        return graph_or_network
    return from_graph(graph_or_network)


def to_undirected(
    graph_or_network: nx.Graph | Network,
    *,
    weight: str | None,
    reciprocal_merge: ReciprocalMerge | None,
) -> Network:
    """Return a deterministic undirected projection of a directed network.

    One-way arcs become undirected edges without changing their attributes.
    When both arc directions exist, the selected finite numeric weight is
    combined with ``reciprocal_merge``. Equal other attributes are retained;
    conflicting or missing values are stored as directional provenance on the
    projected edge.

    Args:
        graph_or_network: Directed simple NetworkX graph or normalized network.
        weight: Edge attribute to combine on reciprocal arcs, or ``None`` for
            an unweighted projection.
        reciprocal_merge: Rule used for the selected weight on reciprocal arcs:
            ``"sum"``, ``"mean"``, ``"max"``, or ``"min"``. Must be ``None``
            when ``weight`` is ``None``.

    Raises:
        ValidationError: If the input is undirected or the merge rule is
            unsupported.
    """

    network = ensure_network(graph_or_network)
    if not network.directed:
        raise ValidationError(
            "to_undirected() requires a directed graph or Network input."
        )
    if weight is not None and (not isinstance(weight, str) or not weight.strip()):
        raise ValidationError("weight must be a non-empty attribute name or None.")
    if weight is None and reciprocal_merge is not None:
        raise ValidationError(
            "reciprocal_merge must be None when no weight attribute is selected."
        )
    if weight is not None and reciprocal_merge not in RECIPROCAL_MERGES:
        raise ValidationError(
            "reciprocal_merge must be one of "
            f"{sorted(RECIPROCAL_MERGES)}, got {reciprocal_merge!r}."
        )

    directed = network.to_original_graph()
    if weight is not None:
        for source, target, attributes in directed.edges(data=True):
            if weight not in attributes or not _is_finite_numeric(attributes[weight]):
                raise ValidationError(
                    f"Weight attribute {weight!r} must contain a finite numeric "
                    f"value on every arc; arc ({source!r}, {target!r}) does not."
                )
    projected = nx.Graph()
    projected.graph.update(directed.graph)
    projected.add_nodes_from(
        (node, dict(attributes)) for node, attributes in directed.nodes(data=True)
    )

    node_order = {node: index for index, node in enumerate(directed.nodes)}
    grouped_arcs: dict[
        tuple[int, int], list[tuple[Hashable, Hashable, dict[str, Any]]]
    ] = {}
    for source, target, attributes in directed.edges(data=True):
        source_index = node_order[source]
        target_index = node_order[target]
        key = (
            (source_index, target_index)
            if source_index < target_index
            else (target_index, source_index)
        )
        grouped_arcs.setdefault(key, []).append((source, target, dict(attributes)))

    reciprocal_pair_count = 0
    for key in sorted(grouped_arcs):
        arcs = sorted(
            grouped_arcs[key],
            key=lambda arc: (node_order[arc[0]], node_order[arc[1]]),
        )
        source = arcs[0][0]
        target = arcs[0][1]
        if len(arcs) == 1:
            attributes = arcs[0][2]
        else:
            reciprocal_pair_count += 1
            attributes = _merge_reciprocal_attributes(
                arcs,
                weight=weight,
                reciprocal_merge=reciprocal_merge,
            )
        projected.add_edge(source, target, **attributes)

    metadata = dict(network.metadata)
    conversion = {
        "mode": "undirected",
        "weight_attribute": weight,
        "reciprocal_merge": reciprocal_merge,
        "original_arc_count": directed.number_of_edges(),
        "undirected_edge_count": projected.number_of_edges(),
        "reciprocal_pair_count": reciprocal_pair_count,
        "one_way_edge_count": projected.number_of_edges() - reciprocal_pair_count,
    }
    metadata["direction_conversion"] = conversion
    merge_description = (
        f"with {reciprocal_merge!r} for weight attribute {weight!r}"
        if weight is not None
        else "without numeric aggregation because no weight was selected"
    )
    warning = (
        "Converted the directed network to an undirected graph: "
        f"{reciprocal_pair_count} reciprocal arc pair(s) were merged "
        f"{merge_description}. Arc direction is not represented in the resulting "
        "network."
    )
    existing_warnings = metadata.get("netbone_warnings", ())
    warnings = (
        [str(value) for value in existing_warnings]
        if isinstance(existing_warnings, list | tuple)
        else []
    )
    metadata["netbone_warnings"] = [*warnings, warning]
    return _normalize_graph(
        projected,
        context=network.context,
        source=network.source,
        metadata=metadata,
    )


def _merge_reciprocal_attributes(
    arcs: list[tuple[Hashable, Hashable, dict[str, Any]]],
    *,
    weight: str | None,
    reciprocal_merge: ReciprocalMerge | None,
) -> dict[str, Any]:
    first_source, first_target, first = arcs[0]
    second_source, second_target, second = arcs[1]
    merged: dict[str, Any] = {}
    conflicts: list[dict[str, object]] = []
    attribute_names = sorted(set(first).union(second), key=str)

    for name in attribute_names:
        first_present = name in first
        second_present = name in second
        first_value = first.get(name)
        second_value = second.get(name)
        if name == weight and (
            first_present
            and second_present
            and _is_finite_numeric(first_value)
            and _is_finite_numeric(second_value)
        ):
            assert reciprocal_merge is not None
            merged[name] = _merge_numeric_values(
                float(first_value),
                float(second_value),
                reciprocal_merge=reciprocal_merge,
            )
        elif first_present and second_present and first_value == second_value:
            merged[name] = first_value
        else:
            conflicts.append(
                {
                    "attribute": str(name),
                    "arcs": [
                        {
                            "source": repr(first_source),
                            "target": repr(first_target),
                            "value": (
                                repr(first_value) if first_present else "<missing>"
                            ),
                        },
                        {
                            "source": repr(second_source),
                            "target": repr(second_target),
                            "value": (
                                repr(second_value) if second_present else "<missing>"
                            ),
                        },
                    ],
                }
            )

    if conflicts:
        provenance_name = DIRECTIONAL_CONFLICTS_ATTR
        while provenance_name in attribute_names:
            provenance_name = f"{provenance_name}_projected"
        merged[provenance_name] = json.dumps(
            conflicts,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
    return merged


def _is_finite_numeric(value: object) -> TypeGuard[int | float]:
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _merge_numeric_values(
    first: float,
    second: float,
    *,
    reciprocal_merge: ReciprocalMerge,
) -> float:
    if reciprocal_merge == "sum":
        return first + second
    if reciprocal_merge == "mean":
        return (first + second) / 2.0
    if reciprocal_merge == "max":
        return max(first, second)
    return min(first, second)


def normalize_edgelist_graph(
    graph: nx.Graph,
    *,
    context: str | None,
    source_path: Path,
    metadata: Mapping[str, object] | None = None,
) -> Network:
    """Normalize a graph created by an edge-list loader."""

    return normalize_loaded_graph(
        graph,
        context=context,
        source_path=source_path,
        metadata=metadata,
    )


def normalize_loaded_graph(
    graph: nx.Graph,
    *,
    context: str | None,
    source_path: Path,
    metadata: Mapping[str, object] | None = None,
) -> Network:
    """Normalize a graph created by a file loader."""

    _validate_supported_graph(graph)
    _validate_reserved_attributes(graph)
    return _normalize_graph(
        graph,
        context=context,
        source=str(source_path),
        metadata=metadata,
    )


def _validate_supported_graph(graph: nx.Graph) -> None:
    if graph.is_multigraph():
        raise CompatibilityError(
            "Multigraphs and multidigraphs are not supported in the current "
            "simple-graph slice."
        )
    if nx.number_of_selfloops(graph) > 0:
        raise CompatibilityError(
            "Self-loops are not supported in the current simple-graph slice."
        )


def _validate_reserved_attributes(graph: nx.Graph) -> None:
    for node, attributes in graph.nodes(data=True):
        overlap = RESERVED_NODE_ATTRIBUTES.intersection(attributes)
        if overlap:
            raise ValidationError(
                f"Node {node!r} uses reserved Netbone attribute(s): "
                f"{', '.join(sorted(overlap))}."
            )
    for source, target, attributes in graph.edges(data=True):
        overlap = RESERVED_EDGE_ATTRIBUTES.intersection(attributes)
        if overlap:
            raise ValidationError(
                f"Edge ({source!r}, {target!r}) uses reserved Netbone "
                f"attribute(s): {', '.join(sorted(overlap))}."
            )


def _normalize_graph(
    graph: nx.Graph,
    *,
    context: str | None,
    source: str | None,
    metadata: Mapping[str, object] | None,
) -> Network:
    normalized = nx.DiGraph() if graph.is_directed() else nx.Graph()
    normalized.graph.update(graph.graph)
    original_to_node_id: dict[Hashable, int] = {}
    node_id_to_original: dict[int, Hashable] = {}

    for node_id, (node, attributes) in enumerate(graph.nodes(data=True)):
        original_to_node_id[node] = node_id
        node_id_to_original[node_id] = node
        copied_attributes = dict(attributes)
        copied_attributes[NODE_ORIGINAL_ATTR] = node
        normalized.add_node(node_id, **copied_attributes)

    edge_id_to_endpoints: dict[int, tuple[int, int]] = {}
    seen_edges: set[tuple[int, int]] = set()

    for edge_id, (source_node, target_node, attributes) in enumerate(
        graph.edges(data=True)
    ):
        source_id = original_to_node_id[source_node]
        target_id = original_to_node_id[target_node]
        key = (
            (source_id, target_id)
            if graph.is_directed()
            else (min(source_id, target_id), max(source_id, target_id))
        )
        if key in seen_edges:
            raise ValidationError(
                f"Duplicate edge ({source_node!r}, {target_node!r}) is not "
                "supported for simple graphs."
            )
        seen_edges.add(key)
        copied_attributes = dict(attributes)
        copied_attributes[EDGE_ID_ATTR] = edge_id
        normalized.add_edge(source_id, target_id, **copied_attributes)
        edge_id_to_endpoints[edge_id] = (source_id, target_id)

    return Network(
        graph=normalized,
        context=context,
        source=source,
        metadata=MappingProxyType(dict(metadata or {})),
        node_id_to_original=MappingProxyType(node_id_to_original),
        original_to_node_id=MappingProxyType(original_to_node_id),
        edge_id_to_endpoints=MappingProxyType(edge_id_to_endpoints),
    )


def _public_attributes(attributes: Mapping[str, Any]) -> dict[str, Any]:
    reserved = RESERVED_NODE_ATTRIBUTES.union(RESERVED_EDGE_ATTRIBUTES)
    return {key: value for key, value in attributes.items() if key not in reserved}
