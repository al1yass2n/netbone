from __future__ import annotations

import networkx as nx
import pandas as pd
import pytest

import netbone as nb


def test_link_prediction_preferential_attachment_scores_removed_edges() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")
    graph.add_edge("a", "c")
    graph.add_edge("b", "c")
    graph.add_edge("b", "d")
    graph.add_edge("c", "d")

    result = nb.score(
        graph,
        method="link_prediction",
        similarity="preferential_attachment",
    )
    by_edge = _rows_by_edge(result.statistics.to_dict(orient="records"))

    assert result.target == "edge"
    assert result.output_type == "score"
    assert result.primary_statistic == "link_prediction_similarity"
    assert result.preferred_direction == "higher"
    assert result.parameters == {"similarity": "preferential_attachment"}
    assert by_edge[frozenset(("a", "b"))]["link_prediction_similarity"] == 2.0
    assert by_edge[frozenset(("b", "c"))]["link_prediction_similarity"] == 4.0
    assert by_edge[frozenset(("a", "b"))]["link_prediction_source_degree"] == 1
    assert by_edge[frozenset(("a", "b"))]["link_prediction_target_degree"] == 2
    assert by_edge[frozenset(("a", "b"))]["link_prediction_source_strength"] == 1.0
    assert by_edge[frozenset(("a", "b"))]["link_prediction_target_strength"] == 2.0


def test_link_prediction_shortest_path_scores_disconnected_removed_edges() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    graph.add_edge("b", "d")
    graph.add_edge("c", "d")

    result = nb.score(graph, method="link_prediction", similarity="shortest_path")
    by_edge = _rows_by_edge(result.statistics.to_dict(orient="records"))

    assert by_edge[frozenset(("a", "b"))]["link_prediction_similarity"] == 0.0
    assert by_edge[frozenset(("a", "b"))]["link_prediction_disconnected"] is True
    assert pd.isna(
        by_edge[frozenset(("a", "b"))]["link_prediction_shortest_path_length"]
    )
    assert by_edge[frozenset(("b", "c"))]["link_prediction_similarity"] == 0.5
    assert by_edge[frozenset(("b", "c"))]["link_prediction_shortest_path_length"] == 2


def test_link_prediction_local_path_counts_length_two_and_three_paths() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")
    graph.add_edge("a", "c")
    graph.add_edge("b", "c")
    graph.add_edge("b", "d")
    graph.add_edge("c", "d")

    result = nb.score(
        graph,
        method="link_prediction",
        similarity="local_path",
        epsilon=0.5,
    )
    by_edge = _rows_by_edge(result.statistics.to_dict(orient="records"))

    assert result.parameters == {"similarity": "local_path", "epsilon": 0.5}
    assert by_edge[frozenset(("a", "b"))]["link_prediction_paths_length_2"] == 1
    assert by_edge[frozenset(("a", "b"))]["link_prediction_paths_length_3"] == 1
    assert (
        by_edge[frozenset(("a", "b"))]["link_prediction_weighted_paths_length_2"] == 1.0
    )
    assert (
        by_edge[frozenset(("a", "b"))]["link_prediction_weighted_paths_length_3"] == 1.0
    )
    assert by_edge[frozenset(("a", "b"))]["link_prediction_similarity"] == 1.5
    assert by_edge[frozenset(("b", "c"))]["link_prediction_paths_length_2"] == 2
    assert by_edge[frozenset(("b", "c"))]["link_prediction_paths_length_3"] == 0
    assert by_edge[frozenset(("b", "c"))]["link_prediction_similarity"] == 2.0


def test_directed_link_prediction_preferential_attachment_uses_out_and_in() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b", weight=1.0)
    graph.add_edge("a", "c", weight=2.0)
    graph.add_edge("a", "d", weight=3.0)
    graph.add_edge("c", "b", weight=5.0)
    graph.add_edge("d", "b", weight=7.0)
    graph.add_edge("x", "a", weight=11.0)
    graph.add_edge("b", "y", weight=13.0)

    result = nb.score(
        graph,
        method="link_prediction",
        similarity="preferential_attachment",
        weight="weight",
    )
    edge = _directed_rows_by_edge(result.statistics.to_dict(orient="records"))[
        ("a", "b")
    ]

    assert edge["link_prediction_source_degree"] == 2
    assert edge["link_prediction_target_degree"] == 2
    assert edge["link_prediction_source_strength"] == 5.0
    assert edge["link_prediction_target_strength"] == 12.0
    assert edge["link_prediction_similarity"] == 60.0
    assert "source out-connectivity" in result.warnings[0]


def test_directed_link_prediction_shortest_path_keeps_arc_orientation() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "a")
    graph.add_edge("a", "c")
    graph.add_edge("c", "b")

    result = nb.score(graph, method="link_prediction", similarity="shortest_path")
    by_arc = _directed_rows_by_edge(result.statistics.to_dict(orient="records"))

    assert by_arc[("a", "b")]["link_prediction_shortest_path_length"] == 2.0
    assert by_arc[("a", "b")]["link_prediction_similarity"] == 0.5
    assert by_arc[("b", "a")]["link_prediction_disconnected"] is True
    assert by_arc[("b", "a")]["link_prediction_similarity"] == 0.0


def test_directed_link_prediction_local_path_counts_only_forward_paths() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b", weight=1.0)
    graph.add_edge("a", "c", weight=2.0)
    graph.add_edge("c", "b", weight=3.0)
    graph.add_edge("a", "d", weight=5.0)
    graph.add_edge("d", "e", weight=7.0)
    graph.add_edge("e", "b", weight=11.0)
    graph.add_edge("b", "f", weight=13.0)
    graph.add_edge("f", "a", weight=17.0)

    result = nb.score(
        graph,
        method="link_prediction",
        similarity="local_path",
        weight="weight",
        epsilon=0.1,
    )
    edge = _directed_rows_by_edge(result.statistics.to_dict(orient="records"))[
        ("a", "b")
    ]

    assert edge["link_prediction_paths_length_2"] == 1
    assert edge["link_prediction_paths_length_3"] == 1
    assert edge["link_prediction_weighted_paths_length_2"] == 6.0
    assert edge["link_prediction_weighted_paths_length_3"] == 385.0
    assert edge["link_prediction_similarity"] == pytest.approx(44.5)


def test_directed_link_prediction_pipeline_preserves_reciprocal_arcs() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "a")
    graph.add_edge("a", "c")
    original = graph.copy()

    result = (
        nb.pipeline()
        .score("link_prediction", similarity="shortest_path")
        .filter("threshold", value=0.0, operator="greater_equal")
        .run(graph)
    )

    assert isinstance(result.graph, nx.DiGraph)
    assert set(result.graph.edges()) == {("a", "b"), ("b", "a"), ("a", "c")}
    assert nx.utils.graphs_equal(graph, original)


def test_link_prediction_fraction_direction_extracts_high_and_low_backbones() -> None:
    graph = _direction_graph()

    high = (
        nb.pipeline()
        .score("link_prediction", similarity="preferential_attachment")
        .filter("fraction", fraction=0.1, direction="higher")
        .run(graph)
    )
    low = (
        nb.pipeline()
        .score("link_prediction", similarity="preferential_attachment")
        .filter("fraction", fraction=0.1, direction="lower")
        .run(graph)
    )

    assert high.selection.parameters["direction"] == "higher"
    assert sorted(high.graph.edges()) == [("b", "c"), ("c", "d"), ("c", "e")]
    assert low.selection.parameters["direction"] == "lower"
    assert sorted(low.graph.edges()) == [("a", "b")]


def test_link_prediction_default_filter_requires_direction() -> None:
    graph = _direction_graph()

    with pytest.raises(nb.ConfigurationError, match="requires parameter direction"):
        nb.pipeline().score(
            "link_prediction",
            similarity="preferential_attachment",
        ).filter("default").run(graph)

    result = (
        nb.pipeline()
        .score("link_prediction", similarity="preferential_attachment")
        .filter("default", direction="lower")
        .run(graph)
    )

    assert result.selection.parameters["fraction"] == 0.1
    assert result.selection.parameters["direction"] == "lower"
    assert sorted(result.graph.edges()) == [("a", "b")]


def test_link_prediction_weight_none_ignores_weights_and_preserves_input() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight="heavy")
    graph.add_edge("a", "c", weight="light")
    graph.add_edge("b", "c", weight="medium")
    original_edges = sorted(graph.edges(data=True))

    result = nb.score(
        graph,
        method="link_prediction",
        similarity="preferential_attachment",
        weight=None,
    )

    assert sorted(graph.edges(data=True)) == original_edges
    assert result.metadata["default_weight"] == "auto"
    assert result.parameters.get("weight") is None
    assert result.statistics["link_prediction_similarity"].tolist() == [1.0, 1.0, 1.0]


def test_link_prediction_default_uses_weights_when_every_edge_has_them() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=10.0)
    graph.add_edge("a", "c", weight=2.0)
    graph.add_edge("b", "c", weight=3.0)

    automatic = nb.score(
        graph, method="link_prediction", similarity="preferential_attachment"
    )
    explicit = nb.score(
        graph,
        method="link_prediction",
        similarity="preferential_attachment",
        weight="weight",
    )

    assert automatic.parameters["weight"] == "weight"
    assert automatic.statistics.equals(explicit.statistics)


def test_link_prediction_weighted_preferential_attachment_uses_strengths() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=10.0)
    graph.add_edge("a", "c", weight=2.0)
    graph.add_edge("b", "c", weight=3.0)

    result = nb.score(
        graph,
        method="link_prediction",
        similarity="preferential_attachment",
        weight="weight",
        weight_alpha=2.0,
    )
    by_edge = _rows_by_edge(result.statistics.to_dict(orient="records"))

    edge = by_edge[frozenset(("a", "b"))]
    assert result.parameters == {
        "similarity": "preferential_attachment",
        "weight": "weight",
        "weight_alpha": 2.0,
        "distance_transform": "inverse",
    }
    assert edge["link_prediction_edge_weight"] == 10.0
    assert edge["link_prediction_edge_effective_weight"] == 100.0
    assert edge["link_prediction_edge_strength"] == 100.0
    assert edge["link_prediction_edge_distance"] == 0.01
    assert edge["link_prediction_source_degree"] == 1
    assert edge["link_prediction_target_degree"] == 1
    assert edge["link_prediction_source_strength"] == 4.0
    assert edge["link_prediction_target_strength"] == 9.0
    assert edge["link_prediction_similarity"] == 36.0


def test_link_prediction_weighted_pa_identity_uses_inverse_strengths() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1.0)
    graph.add_edge("a", "c", weight=2.0)
    graph.add_edge("b", "c", weight=4.0)

    result = nb.score(
        graph,
        method="link_prediction",
        similarity="preferential_attachment",
        weight="weight",
        distance_transform="identity",
    )
    by_edge = _rows_by_edge(result.statistics.to_dict(orient="records"))

    edge = by_edge[frozenset(("a", "b"))]
    assert edge["link_prediction_source_strength"] == 0.5
    assert edge["link_prediction_target_strength"] == 0.25
    assert edge["link_prediction_similarity"] == pytest.approx(0.125)


def test_link_prediction_weighted_shortest_path_uses_inverse_distance() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1.0)
    graph.add_edge("a", "c", weight=4.0)
    graph.add_edge("c", "b", weight=2.0)

    result = nb.score(
        graph,
        method="link_prediction",
        similarity="shortest_path",
        weight="weight",
    )
    by_edge = _rows_by_edge(result.statistics.to_dict(orient="records"))

    edge = by_edge[frozenset(("a", "b"))]
    assert edge["link_prediction_shortest_path_length"] == 0.75
    assert edge["link_prediction_similarity"] == pytest.approx(1.0 / 0.75)
    assert edge["link_prediction_disconnected"] is False


def test_link_prediction_weighted_shortest_path_identity_uses_distances() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1.0)
    graph.add_edge("a", "c", weight=4.0)
    graph.add_edge("c", "b", weight=2.0)

    result = nb.score(
        graph,
        method="link_prediction",
        similarity="shortest_path",
        weight="weight",
        distance_transform="identity",
    )
    by_edge = _rows_by_edge(result.statistics.to_dict(orient="records"))

    edge = by_edge[frozenset(("a", "b"))]
    assert result.parameters == {
        "similarity": "shortest_path",
        "weight": "weight",
        "weight_alpha": 1.0,
        "distance_transform": "identity",
    }
    assert edge["link_prediction_shortest_path_length"] == 6.0
    assert edge["link_prediction_similarity"] == pytest.approx(1.0 / 6.0)
    assert edge["link_prediction_edge_strength"] == 1.0
    assert edge["link_prediction_edge_distance"] == 1.0


def test_link_prediction_weighted_local_path_uses_path_weight_products() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1.0)
    graph.add_edge("a", "c", weight=2.0)
    graph.add_edge("c", "b", weight=3.0)
    graph.add_edge("a", "d", weight=5.0)
    graph.add_edge("d", "e", weight=7.0)
    graph.add_edge("e", "b", weight=11.0)

    result = nb.score(
        graph,
        method="link_prediction",
        similarity="local_path",
        weight="weight",
        epsilon=0.1,
    )
    by_edge = _rows_by_edge(result.statistics.to_dict(orient="records"))

    edge = by_edge[frozenset(("a", "b"))]
    assert edge["link_prediction_paths_length_2"] == 1
    assert edge["link_prediction_paths_length_3"] == 1
    assert edge["link_prediction_weighted_paths_length_2"] == 6.0
    assert edge["link_prediction_weighted_paths_length_3"] == 385.0
    assert edge["link_prediction_similarity"] == pytest.approx(44.5)


def test_link_prediction_weighted_local_path_identity_uses_inverse_strengths() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1.0)
    graph.add_edge("a", "c", weight=2.0)
    graph.add_edge("c", "b", weight=4.0)

    result = nb.score(
        graph,
        method="link_prediction",
        similarity="local_path",
        weight="weight",
        distance_transform="identity",
    )
    by_edge = _rows_by_edge(result.statistics.to_dict(orient="records"))

    edge = by_edge[frozenset(("a", "b"))]
    assert edge["link_prediction_paths_length_2"] == 1
    assert edge["link_prediction_weighted_paths_length_2"] == pytest.approx(0.125)
    assert edge["link_prediction_similarity"] == pytest.approx(0.125)


def test_link_prediction_validates_parameters() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b")

    with pytest.raises(nb.ConfigurationError, match="requires string parameter"):
        nb.score(graph, method="link_prediction")
    with pytest.raises(nb.ConfigurationError, match="must be one of"):
        nb.score(graph, method="link_prediction", similarity="adamic_adar")
    with pytest.raises(nb.ConfigurationError, match="only applies"):
        nb.score(
            graph,
            method="link_prediction",
            similarity="shortest_path",
            epsilon=0.5,
        )
    with pytest.raises(nb.ValidationError, match="must be nonnegative"):
        nb.score(
            graph,
            method="link_prediction",
            similarity="local_path",
            epsilon=-0.1,
        )
    with pytest.raises(nb.ConfigurationError, match="only applies"):
        nb.score(
            graph,
            method="link_prediction",
            similarity="shortest_path",
            weight_alpha=0.5,
        )
    with pytest.raises(nb.ConfigurationError, match="only applies"):
        nb.score(
            graph,
            method="link_prediction",
            similarity="shortest_path",
            distance_transform="identity",
        )
    with pytest.raises(nb.ConfigurationError, match="must be a string or None"):
        nb.score(
            graph,
            method="link_prediction",
            similarity="shortest_path",
            weight=1,
        )
    with pytest.raises(nb.ConfigurationError, match="must be a string"):
        nb.score(
            graph,
            method="link_prediction",
            similarity="shortest_path",
            weight="weight",
            distance_transform=1,
        )
    graph["a"]["b"]["weight"] = 1.0
    with pytest.raises(nb.ConfigurationError, match="must be one of"):
        nb.score(
            graph,
            method="link_prediction",
            similarity="shortest_path",
            weight="weight",
            distance_transform="log",
        )
    del graph["a"]["b"]["weight"]
    with pytest.raises(nb.ConfigurationError, match="must be numeric"):
        nb.score(
            graph,
            method="link_prediction",
            similarity="shortest_path",
            weight="weight",
            weight_alpha=True,
        )
    with pytest.raises(nb.ValidationError, match="missing required weight"):
        nb.score(
            graph,
            method="link_prediction",
            similarity="shortest_path",
            weight="weight",
        )
    graph["a"]["b"]["weight"] = 0.0
    with pytest.raises(nb.ValidationError, match="must be positive"):
        nb.score(
            graph,
            method="link_prediction",
            similarity="shortest_path",
            weight="weight",
        )


def test_link_prediction_pipeline_config_round_trips() -> None:
    graph = _direction_graph()
    pipeline = (
        nb.pipeline()
        .score("link_prediction", similarity="preferential_attachment")
        .filter("default", direction="lower")
    )

    restored = nb.Pipeline.from_dict(pipeline.to_dict())
    result = restored.run(graph)

    assert restored == pipeline
    assert sorted(result.graph.edges()) == [("a", "b")]


def _direction_graph() -> nx.Graph:
    graph = nx.Graph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    graph.add_edge("c", "d")
    graph.add_edge("c", "e")
    graph.add_edge("d", "e")
    return graph


def _rows_by_edge(
    rows: list[dict[str, object]],
) -> dict[frozenset[str], dict[str, object]]:
    return {frozenset((str(row["source"]), str(row["target"]))): row for row in rows}


def _directed_rows_by_edge(
    rows: list[dict[str, object]],
) -> dict[tuple[str, str], dict[str, object]]:
    return {(str(row["source"]), str(row["target"])): row for row in rows}
