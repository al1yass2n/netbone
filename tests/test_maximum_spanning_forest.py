from __future__ import annotations

import networkx as nx
import pandas as pd
import pytest

import netbone as nb


def _selected_by_edge(result: nb.MethodResult) -> dict[frozenset[object], float]:
    return {
        frozenset((row["source"], row["target"])): row[
            "maximum_spanning_forest_selected"
        ]
        for row in result.statistics.to_dict(orient="records")
    }


def test_maximum_spanning_forest_scores_membership() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("b", "c", weight=2.0)
    graph.add_edge("a", "c", weight=1.0)

    result = nb.score(graph, method="maximum_spanning_forest", weight="weight")

    assert list(result.statistics.columns) == [
        "edge_id",
        "source_id",
        "target_id",
        "source",
        "target",
        "maximum_spanning_forest_weight",
        "maximum_spanning_forest_order",
        "maximum_spanning_forest_selected",
    ]
    assert result.target == "edge"
    assert result.output_type == "score"
    assert result.primary_statistic == "maximum_spanning_forest_selected"
    assert result.preferred_direction == "higher"
    assert result.parameters == {"weight": "weight", "tie_policy": "stable_edge_id"}
    assert _selected_by_edge(result) == {
        frozenset(("a", "b")): 1.0,
        frozenset(("b", "c")): 1.0,
        frozenset(("a", "c")): 0.0,
    }


def test_maximum_spanning_forest_default_filter_extracts_forest() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("b", "c", weight=2.0)
    graph.add_edge("a", "c", weight=1.0)

    result = (
        nb.pipeline()
        .score("maximum_spanning_forest", weight="weight")
        .filter("default")
        .run(graph)
    )

    assert result.selection.parameters["strategy"] == "threshold"
    assert result.selection.parameters["statistic"] == (
        "maximum_spanning_forest_selected"
    )
    assert result.selection.parameters["value"] == 1.0
    assert result.selection.parameters["operator"] == "equal"
    assert sorted(result.graph.edges()) == [("a", "b"), ("b", "c")]


def test_maximum_spanning_forest_handles_disconnected_graphs() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1.0)
    graph.add_edge("c", "d", weight=2.0)

    result = (
        nb.pipeline()
        .score("maximum_spanning_forest", weight="weight")
        .filter("default")
        .run(graph)
    )

    assert sorted(result.graph.edges()) == [("a", "b"), ("c", "d")]
    assert result.summary()["connected_component_count"] == 2


def test_maximum_spanning_forest_breaks_ties_by_stable_edge_id() -> None:
    graph = nx.Graph()
    graph.add_edge("c", "a", weight=1.0)
    graph.add_edge("b", "c", weight=1.0)
    graph.add_edge("a", "b", weight=1.0)

    result = nb.score(graph, method="maximum_spanning_forest", weight="weight")

    assert result.statistics["edge_id"].tolist() == [0, 1, 2]
    assert result.statistics["maximum_spanning_forest_selected"].tolist() == [
        1.0,
        1.0,
        0.0,
    ]
    assert result.warnings == (
        "Maximum spanning forest encountered tied weights across selected "
        "and rejected edges; ties were broken by stable edge_id order.",
    )


def test_maximum_spanning_forest_can_score_unweighted_graphs() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    graph.add_edge("a", "c")

    result = nb.score(graph, method="maximum_spanning_forest", weight=None)

    assert result.statistics["maximum_spanning_forest_weight"].tolist() == [
        1.0,
        1.0,
        1.0,
    ]
    assert result.statistics["maximum_spanning_forest_selected"].sum() == 2.0


def test_maximum_spanning_forest_rejects_missing_and_bad_weights() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")

    with pytest.raises(nb.ValidationError, match="missing required weight"):
        nb.score(graph, method="maximum_spanning_forest", weight="weight")

    graph["a"]["b"]["weight"] = "heavy"
    with pytest.raises(nb.ValidationError, match="must be numeric"):
        nb.score(graph, method="maximum_spanning_forest", weight="weight")

    graph["a"]["b"]["weight"] = float("nan")
    with pytest.raises(nb.ValidationError, match="must be finite"):
        nb.score(graph, method="maximum_spanning_forest", weight="weight")


def test_maximum_spanning_forest_rejects_bad_parameter_type() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")

    with pytest.raises(nb.ConfigurationError, match="weight"):
        nb.score(graph, method="maximum_spanning_forest", weight=123)


def test_maximum_spanning_forest_unselected_order_is_missing() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("b", "c", weight=2.0)
    graph.add_edge("a", "c", weight=1.0)

    result = nb.score(graph, method="maximum_spanning_forest", weight="weight")
    unselected_order = result.statistics.loc[
        result.statistics["maximum_spanning_forest_selected"] == 0.0,
        "maximum_spanning_forest_order",
    ].iloc[0]

    assert pd.isna(unselected_order)
