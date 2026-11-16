from __future__ import annotations

from itertools import combinations

import networkx as nx
import pytest

import netbone as nb


def test_pmfg_selects_descending_edges_subject_to_planarity() -> None:
    graph = nx.Graph()
    nodes = range(5)
    for index, (source, target) in enumerate(combinations(nodes, 2)):
        graph.add_edge(source, target, weight=10.0 - index)

    result = nb.score(
        graph,
        method="planar_maximally_filtered_graph",
        weight="weight",
    )

    assert result.primary_statistic == "pmfg_selected"
    assert result.statistics["pmfg_selected"].sum() == 9.0
    assert result.statistics["pmfg_selected"].tolist()[-1] == 0.0


def test_pmfg_default_filter_extracts_planar_graph() -> None:
    graph = nx.Graph()
    nodes = range(5)
    for index, (source, target) in enumerate(combinations(nodes, 2)):
        graph.add_edge(source, target, weight=10.0 - index)

    result = (
        nb.pipeline()
        .score("planar_maximally_filtered_graph", weight="weight")
        .filter("default")
        .run(graph)
    )

    is_planar, _embedding = nx.check_planarity(result.graph)
    assert is_planar
    assert result.graph.number_of_edges() == 9


def test_pmfg_can_score_unweighted_graphs() -> None:
    graph = nx.complete_graph(4)

    result = nb.score(graph, method="planar_maximally_filtered_graph", weight=None)

    assert result.statistics["pmfg_weight"].tolist() == pytest.approx([1.0] * 6)
    assert result.statistics["pmfg_selected"].sum() == 6.0
