"""H-backbone scoring method."""

from __future__ import annotations

from typing import Any

import pandas as pd

from netbone.methods._utils import (
    DISTANCE_TRANSFORMS,
    edge_betweenness_by_edge_id,
    edge_weights_and_distances,
    h_index,
)
from netbone.network import EDGE_ID_ATTR, Network
from netbone.results import MethodResult

H_BACKBONE_DISTANCE_ATTR = "_netbone_h_backbone_distance"

H_BACKBONE_METADATA: dict[str, object] = {
    "name": "h_backbone",
    "display_name": "H-Backbone",
    "target": "edge",
    "output_type": "score",
    "primary_statistic": "h_backbone_selected",
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
        "value": 1.0,
        "operator": "equal",
    },
    "default_weight": "auto",
    "default_distance_transform": "inverse",
    "distance_transform_options": tuple(sorted(DISTANCE_TRANSFORMS)),
    "reference": "Zhang, Stanley, and Ye, Scientific Reports 8, 14356 (2018).",
    "doi": "10.1038/s41598-018-32430-1",
}


def compute_h_backbone(
    network: Network,
    *,
    weight: str = "weight",
    distance_transform: str = "inverse",
) -> MethodResult:
    """Mark edges passing the h-strength or h-bridge threshold."""

    weights, distances = edge_weights_and_distances(
        network,
        weight=weight,
        distance_transform=distance_transform,
        method_name="h_backbone",
    )
    betweenness = edge_betweenness_by_edge_id(
        network,
        distances=distances,
        weighted=True,
        normalized=False,
        distance_attr=H_BACKBONE_DISTANCE_ATTR,
    )
    node_count = network.graph.number_of_nodes()
    bridges = {
        edge_id: value / node_count if node_count else 0.0
        for edge_id, value in betweenness.items()
    }
    h_strength_threshold = h_index(list(weights.values()))
    h_bridge_threshold = h_index(list(bridges.values()))

    rows: list[dict[str, Any]] = []
    for source_id, target_id, attributes in sorted(
        network.graph.edges(data=True),
        key=lambda edge: edge[2][EDGE_ID_ATTR],
    ):
        edge_id = int(attributes[EDGE_ID_ATTR])
        selected = (
            h_strength_threshold > 0 and weights[edge_id] >= h_strength_threshold
        ) or (h_bridge_threshold > 0 and bridges[edge_id] >= h_bridge_threshold)
        rows.append(
            {
                "edge_id": edge_id,
                "source_id": source_id,
                "target_id": target_id,
                "source": network.node_id_to_original[source_id],
                "target": network.node_id_to_original[target_id],
                "h_backbone_weight": weights[edge_id],
                "h_backbone_bridge": bridges[edge_id],
                "h_backbone_h_strength": h_strength_threshold,
                "h_backbone_h_bridge": h_bridge_threshold,
                "h_backbone_selected": 1.0 if selected else 0.0,
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
            "h_backbone_weight",
            "h_backbone_bridge",
            "h_backbone_h_strength",
            "h_backbone_h_bridge",
            "h_backbone_selected",
        ],
    )
    return MethodResult(
        method_name="h_backbone",
        target="edge",
        statistics=statistics,
        primary_statistic="h_backbone_selected",
        output_type="score",
        preferred_direction="higher",
        parameters={
            "weight": weight,
            "distance_transform": distance_transform,
        },
        metadata=H_BACKBONE_METADATA,
        warnings=(),
    )
