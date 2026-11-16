from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb


def test_marginal_likelihood_computes_method_specific_pvalues() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3)
    graph.add_edge("a", "c", weight=1)
    graph.add_edge("b", "c", weight=2)

    result = nb.score(graph, method="marginal_likelihood", weight="weight")

    assert result.target == "edge"
    assert result.output_type == "pvalue"
    assert result.primary_statistic == "marginal_likelihood_pvalue"
    assert result.preferred_direction == "lower"
    assert result.statistics["marginal_likelihood_pvalue"].tolist() == pytest.approx(
        [0.215695, 0.665102, 0.365113],
        abs=1e-6,
    )


def test_marginal_likelihood_default_filter_resolves_to_significance() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3)
    graph.add_edge("a", "c", weight=1)
    graph.add_edge("b", "c", weight=2)

    result = (
        nb.pipeline()
        .score("marginal_likelihood", weight="weight")
        .filter("default", alpha=0.3)
        .run(graph)
    )

    assert result.selection.statistic == "marginal_likelihood_pvalue"
    assert sorted(result.graph.edges()) == [("a", "b")]


def test_marginal_likelihood_requires_integer_count_weights() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1.5)

    with pytest.raises(nb.ValidationError, match="integer count"):
        nb.score(graph, method="marginal_likelihood", weight="weight")
