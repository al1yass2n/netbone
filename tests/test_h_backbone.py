from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb


def test_h_backbone_marks_edges_passing_h_strength_or_bridge_threshold() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("a", "c", weight=1.0)
    graph.add_edge("b", "c", weight=2.0)

    result = nb.score(graph, method="h_backbone", weight="weight")

    assert list(result.statistics.columns) == [
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
    ]
    assert result.primary_statistic == "h_backbone_selected"
    assert result.statistics["h_backbone_h_strength"].tolist() == [2, 2, 2]
    assert result.statistics["h_backbone_selected"].tolist() == [1.0, 0.0, 1.0]


def test_h_backbone_default_filter_extracts_selected_edges() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("a", "c", weight=1.0)
    graph.add_edge("b", "c", weight=2.0)

    result = (
        nb.pipeline().score("h_backbone", weight="weight").filter("default").run(graph)
    )

    assert sorted(result.graph.edges()) == [("a", "b"), ("b", "c")]


def test_h_backbone_rejects_non_positive_weights_for_inverse_distance() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=0.0)

    with pytest.raises(nb.ValidationError, match="must be positive"):
        nb.score(graph, method="h_backbone", weight="weight")
