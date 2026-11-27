from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb

EXTRA_PARAMETERS: dict[str, dict[str, object]] = {
    "glanb": {"c": 1.0},
    "link_prediction": {"similarity": "shortest_path"},
    "link_prediction_iforest": {"similarities": "shortest_path"},
}


def _weighted_graph() -> nx.Graph:
    graph = nx.karate_club_graph()
    for index, (source, target) in enumerate(graph.edges()):
        graph[source][target]["weight"] = float((index * 7) % 11 + 1)
    return graph


def _score(graph: nx.Graph, method: str, **parameters: object) -> nb.MethodResult:
    if method == "link_prediction_iforest":
        pytest.importorskip("sklearn")
    return nb.score(graph, method, **{**EXTRA_PARAMETERS.get(method, {}), **parameters})


def _methods(mode: str) -> list[str]:
    return [
        name
        for name in nb.list_methods()
        if nb.describe_method(name)["weight_mode"] == mode
    ]


def test_every_method_declares_a_consistent_weight_mode() -> None:
    for name in nb.list_methods():
        metadata = nb.describe_method(name)
        mode = metadata["weight_mode"]
        assert mode in {"ignored", "optional", "required"}
        assert metadata["requires_weights"] is (mode == "required")
        if mode == "ignored":
            assert "default_weight" not in metadata
        else:
            assert metadata["default_weight"] == "auto"


@pytest.mark.parametrize("method", _methods("optional") + _methods("required"))
def test_auto_weight_uses_weights_when_every_edge_has_them(method: str) -> None:
    graph = _weighted_graph()

    automatic = _score(graph, method)
    explicit = _score(graph, method, weight="weight")

    assert automatic.parameters["weight"] == "weight"
    assert automatic.statistics.equals(explicit.statistics)


@pytest.mark.parametrize("method", _methods("optional"))
def test_auto_weight_runs_unweighted_when_no_edge_has_weights(method: str) -> None:
    graph = nx.Graph(nx.karate_club_graph().edges())

    automatic = _score(graph, method)
    explicit = _score(graph, method, weight=None)

    assert automatic.parameters.get("weight") is None
    assert automatic.statistics.equals(explicit.statistics)


@pytest.mark.parametrize("method", _methods("required"))
def test_weight_only_methods_explain_missing_weights(method: str) -> None:
    graph = nx.Graph(nx.karate_club_graph().edges())

    with pytest.raises(nb.ValidationError, match="requires edge weights"):
        _score(graph, method)


@pytest.mark.parametrize("method", _methods("optional") + _methods("required"))
def test_auto_weight_rejects_partially_weighted_graphs(method: str) -> None:
    graph = _weighted_graph()
    del graph[0][1]["weight"]

    with pytest.raises(nb.ValidationError, match="Only 77 of 78 edges"):
        _score(graph, method)


def test_weight_none_still_forces_unweighted_scoring() -> None:
    graph = _weighted_graph()
    stripped = graph.copy()
    for _, _, attributes in stripped.edges(data=True):
        attributes.clear()

    weighted = nb.score(graph, "edge_betweenness", weight=None)
    unweighted = nb.score(stripped, "edge_betweenness")

    assert weighted.statistics["edge_betweenness"].tolist() == pytest.approx(
        unweighted.statistics["edge_betweenness"].tolist()
    )


def test_auto_weight_warns_how_shortest_path_methods_read_weights() -> None:
    result = nb.score(_weighted_graph(), "link_salience")
    explicit = nb.score(
        _weighted_graph(), "link_salience", distance_transform="inverse"
    )

    assert any("tie strength" in warning for warning in result.warnings)
    assert not any("tie strength" in warning for warning in explicit.warnings)


def test_ignored_weight_methods_accept_weighted_graphs() -> None:
    for method in _methods("ignored"):
        result = nb.score(_weighted_graph(), method)
        assert "weight" not in result.parameters


def test_empty_graph_still_scores_with_weight_only_methods() -> None:
    result = nb.score(nx.Graph(), "disparity")

    assert result.statistics.empty


def test_edge_weight_supports_directed_graphs() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("b", "a", weight=1.0)

    result = nb.score(graph, "edge_weight")

    assert result.statistics["score"].tolist() == [3.0, 1.0]
