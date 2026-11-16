from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb


def test_gspar_scores_open_neighborhood_jaccard_similarity() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")
    graph.add_edge("a", "c")
    graph.add_edge("b", "c")
    graph.add_edge("c", "d")

    result = nb.score(graph, method="gspar")

    assert result.target == "edge"
    assert result.output_type == "score"
    assert result.primary_statistic == "gspar_jaccard_similarity"
    assert result.preferred_direction == "higher"
    assert result.parameters["neighborhood"] == "open"
    assert result.statistics["gspar_jaccard_similarity"].tolist() == pytest.approx(
        [1 / 3, 0.25, 0.25, 0.0]
    )


def test_gspar_default_filter_uses_fraction() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")
    graph.add_edge("a", "c")
    graph.add_edge("b", "c")
    graph.add_edge("c", "d")

    result = nb.pipeline().score("gspar").filter("default").run(graph)

    assert result.selection.parameters["strategy"] == "fraction"
    assert result.selection.parameters["fraction"] == 0.1
    assert sorted(result.graph.edges()) == [("a", "b")]


def test_gspar_rejects_unknown_parameters() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")

    with pytest.raises(nb.ConfigurationError, match="does not accept"):
        nb.score(graph, method="gspar", weight="weight")
