"""Planar Maximally Filtered Graph scoring method."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import networkx as nx
import pandas as pd

from netbone.methods._references import reference_metadata
from netbone.methods._utils import edge_weights
from netbone.network import EDGE_ID_ATTR, Network
from netbone.results import MethodResult

PLANAR_MAXIMALLY_FILTERED_GRAPH_METADATA: dict[str, object] = {
    "name": "planar_maximally_filtered_graph",
    "display_name": "Planar Maximally Filtered Graph",
    "target": "edge",
    "output_type": "score",
    "primary_statistic": "pmfg_selected",
    "preferred_direction": "higher",
    "supports_directed": False,
    "supports_weighted": True,
    "requires_weights": False,
    "weight_mode": "optional",
    "requires_positive_weights": False,
    "supports_multigraph": False,
    "supports_self_loops": False,
    "default_filter": "threshold",
    "default_filter_parameters": {
        "value": 1.0,
        "operator": "equal",
    },
    "default_weight": "auto",
    "tie_policy": "stable_edge_id",
    **reference_metadata("planar_maximally_filtered_graph"),
}


def compute_planar_maximally_filtered_graph(
    network: Network,
    *,
    weight: str | None = "weight",
) -> MethodResult:
    """Mark edges selected by descending weight subject to graph planarity."""

    weights = edge_weights(
        network,
        weight=weight,
        method_name="planar_maximally_filtered_graph",
    )
    selected_order = _selected_edge_order(network, weights)
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
                "pmfg_weight": weights[edge_id],
                "pmfg_order": selected_order.get(edge_id),
                "pmfg_selected": 1.0 if edge_id in selected_ids else 0.0,
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
            "pmfg_weight",
            "pmfg_order",
            "pmfg_selected",
        ],
    )
    return MethodResult(
        method_name="planar_maximally_filtered_graph",
        target="edge",
        statistics=statistics,
        primary_statistic="pmfg_selected",
        output_type="score",
        preferred_direction="higher",
        parameters={"weight": weight, "tie_policy": "stable_edge_id"},
        metadata=PLANAR_MAXIMALLY_FILTERED_GRAPH_METADATA,
        warnings=_warnings(weights, selected_ids),
    )


def _selected_edge_order(
    network: Network,
    weights: Mapping[int, float],
) -> dict[int, int]:
    candidate = nx.Graph()
    candidate.add_nodes_from(network.graph.nodes)
    selected_order: dict[int, int] = {}
    max_edges = _max_planar_edges(network.graph.number_of_nodes())

    edge_rows = [
        (edge_id, endpoints[0], endpoints[1], weights[edge_id])
        for edge_id, endpoints in network.edge_id_to_endpoints.items()
    ]
    for edge_id, source_id, target_id, _weight in sorted(
        edge_rows,
        key=lambda row: (-row[3], row[0]),
    ):
        candidate.add_edge(source_id, target_id)
        is_planar, _embedding = nx.check_planarity(candidate)
        if is_planar:
            selected_order[edge_id] = len(selected_order) + 1
        else:
            candidate.remove_edge(source_id, target_id)
        if len(selected_order) >= max_edges:
            break
    return selected_order


def _max_planar_edges(node_count: int) -> int:
    if node_count <= 1:
        return 0
    if node_count == 2:
        return 1
    return 3 * (node_count - 2)


def _warnings(
    weights: Mapping[int, float],
    selected_ids: set[int],
) -> tuple[str, ...]:
    rejected_ids = set(weights).difference(selected_ids)
    selected_weights = {weights[edge_id] for edge_id in selected_ids}
    rejected_weights = {weights[edge_id] for edge_id in rejected_ids}
    if selected_weights.intersection(rejected_weights):
        return (
            "PMFG encountered tied weights across selected and rejected edges; "
            "ties were broken by stable edge_id order.",
        )
    return ()
