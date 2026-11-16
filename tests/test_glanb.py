from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb


def test_glanb_computes_shortest_path_significance_values() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=2.0)
    graph.add_edge("b", "c", weight=1.0)

    result = nb.score(graph, method="glanb", weight="weight", c=1.0)

    assert list(result.statistics.columns) == [
        "edge_id",
        "source_id",
        "target_id",
        "source",
        "target",
        "glanb_weight",
        "glanb_distance",
        "glanb_source_involvement",
        "glanb_target_involvement",
        "glanb_source_significance",
        "glanb_target_significance",
        "glanb_significance",
    ]
    assert result.output_type == "pvalue"
    assert result.primary_statistic == "glanb_significance"
    assert result.preferred_direction == "lower"
    assert result.statistics["glanb_significance"].tolist() == pytest.approx([0.5, 0.5])


def test_glanb_involvement_uses_shortest_path_multiplicity_ratios() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")
    graph.add_edge("a", "c")
    graph.add_edge("b", "d")
    graph.add_edge("c", "d")
    graph.add_edge("b", "e")

    result = nb.score(graph, method="glanb", c=1.0)
    by_edge = {
        frozenset((row["source"], row["target"])): row
        for row in result.statistics.to_dict(orient="records")
    }

    assert by_edge[frozenset(("a", "b"))]["glanb_source_involvement"] == (
        pytest.approx(0.625)
    )
    assert by_edge[frozenset(("a", "c"))]["glanb_source_involvement"] == (
        pytest.approx(0.375)
    )


def test_glanb_default_filter_resolves_to_significance() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=2.0)
    graph.add_edge("b", "c", weight=1.0)

    result = (
        nb.pipeline()
        .score("glanb", weight="weight", c=1.0)
        .filter("default", alpha=0.6)
        .run(graph)
    )

    assert result.selection.statistic == "glanb_significance"
    assert sorted(result.graph.edges()) == [("a", "b"), ("b", "c")]


def test_glanb_requires_c_parameter_and_positive_weights() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1.0)

    with pytest.raises(nb.ConfigurationError, match="requires numeric parameter 'c'"):
        nb.score(graph, method="glanb", weight="weight")

    with pytest.raises(nb.ValidationError, match="must be nonnegative"):
        nb.score(graph, method="glanb", weight="weight", c=-0.1)

    graph["a"]["b"]["weight"] = 0.0
    with pytest.raises(nb.ValidationError, match="must be positive"):
        nb.score(graph, method="glanb", weight="weight", c=1.0)
