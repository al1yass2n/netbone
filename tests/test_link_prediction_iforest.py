from __future__ import annotations

from importlib.util import find_spec

import networkx as nx
import pandas as pd
import pytest

import netbone as nb
import netbone.methods.link_prediction_iforest as iforest_method

SKLEARN_AVAILABLE = find_spec("sklearn") is not None


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="requires optional ml dependency")
def test_link_prediction_iforest_treats_both_feature_tails_as_anomalous() -> None:
    scores = iforest_method._isolation_scores(
        [[-10.0], [-0.2], [0.0], [0.2], [10.0]],
        n_estimators=256,
        max_samples="auto",
        max_features=1.0,
        bootstrap=False,
        random_state=0,
    )

    assert scores[0] > scores[2]
    assert scores[-1] > scores[2]


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="requires optional ml dependency")
def test_link_prediction_iforest_scores_one_similarity_deterministically() -> None:
    graph = _feature_graph()
    original = graph.copy()

    first = nb.score(
        graph,
        method="link_prediction_iforest",
        similarities="preferential_attachment",
        n_estimators=64,
    )
    second = nb.score(
        graph,
        method="link_prediction_iforest",
        similarities="preferential_attachment",
        n_estimators=64,
    )

    assert first.target == "edge"
    assert first.output_type == "score"
    assert first.primary_statistic == "link_prediction_iforest_score"
    assert first.preferred_direction == "higher"
    assert first.parameters["similarities"] == ["preferential_attachment"]
    assert first.parameters["random_state"] == 0
    assert "link_prediction_iforest_preferential_attachment_similarity" in (
        first.statistics.columns
    )
    assert first.statistics[first.primary_statistic].notna().all()
    pd.testing.assert_frame_equal(first.statistics, second.statistics)
    assert nx.utils.graphs_equal(graph, original)


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="requires optional ml dependency")
def test_link_prediction_iforest_accepts_multiple_similarity_features() -> None:
    result = nb.score(
        _feature_graph(),
        method="link_prediction_iforest",
        similarities=["preferential_attachment", "shortest_path", "local_path"],
        epsilon=0.25,
        max_features=2,
        random_state=17,
    )

    assert result.parameters["similarities"] == [
        "preferential_attachment",
        "shortest_path",
        "local_path",
    ]
    assert result.parameters["epsilon"] == 0.25
    assert result.parameters["max_features"] == 2
    assert result.parameters["random_state"] == 17
    for similarity in ("preferential_attachment", "shortest_path", "local_path"):
        assert f"link_prediction_iforest_{similarity}_similarity" in (
            result.statistics.columns
        )


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="requires optional ml dependency")
def test_link_prediction_iforest_supports_directed_similarity_features() -> None:
    graph = nx.DiGraph()
    graph.add_edges_from(
        [
            ("a", "b"),
            ("a", "c"),
            ("c", "b"),
            ("b", "d"),
            ("d", "a"),
            ("c", "d"),
        ]
    )
    original = graph.copy()

    result = nb.score(
        graph,
        method="link_prediction_iforest",
        similarities=["preferential_attachment", "shortest_path", "local_path"],
        n_estimators=32,
    )

    assert len(result.statistics) == graph.number_of_edges()
    assert result.statistics[result.primary_statistic].notna().all()
    assert "forward replacement paths" in result.warnings[-1]
    assert nx.utils.graphs_equal(graph, original)


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="requires optional ml dependency")
def test_link_prediction_iforest_uses_fraction_and_threshold_filters() -> None:
    graph = _feature_graph()
    scores = nb.score(
        graph,
        method="link_prediction_iforest",
        similarities="preferential_attachment",
        n_estimators=64,
    )
    score_column = scores.primary_statistic
    maximum_edge_id = int(
        scores.statistics.sort_values(
            [score_column, "edge_id"],
            ascending=[False, True],
        ).iloc[0]["edge_id"]
    )

    fraction = nb.filter_scores(
        graph,
        scores,
        strategy="fraction",
        fraction=1.0 / graph.number_of_edges(),
        tie_policy="exact_stable",
    )
    cutoff = float(scores.statistics[score_column].median())
    threshold = nb.filter_scores(
        graph,
        scores,
        strategy="threshold",
        value=cutoff,
        operator="greater_equal",
    )

    assert fraction.selection.selected_ids == (maximum_edge_id,)
    assert set(threshold.selection.selected_ids) == set(
        scores.statistics.loc[
            scores.statistics[score_column] >= cutoff,
            "edge_id",
        ].astype(int)
    )


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="requires optional ml dependency")
def test_link_prediction_iforest_pipeline_config_round_trips() -> None:
    pipeline = (
        nb.pipeline()
        .score(
            "link_prediction_iforest",
            similarities=["preferential_attachment", "shortest_path"],
            random_state=9,
        )
        .filter("fraction", fraction=0.25, tie_policy="exact_stable")
    )

    restored = nb.Pipeline.from_dict(pipeline.to_dict())
    result = restored.run(_feature_graph())

    assert restored == pipeline
    assert result.method_result.method_name == "link_prediction_iforest"
    assert result.method_result.parameters["random_state"] == 9


@pytest.mark.parametrize(
    ("parameters", "message"),
    [
        ({"similarities": []}, "cannot be empty"),
        (
            {"similarities": ["local_path", "local_path"]},
            "cannot contain duplicates",
        ),
        ({"similarities": ["jaccard"]}, "unknown value"),
        (
            {"similarities": "shortest_path", "epsilon": 0.5},
            "only applies",
        ),
        ({"similarities": "local_path", "n_estimators": 0}, "must be positive"),
        (
            {"similarities": "local_path", "max_features": 2},
            "selected similarities",
        ),
        (
            {"similarities": "local_path", "contamination": 0.1},
            "does not accept",
        ),
    ],
)
def test_link_prediction_iforest_validates_parameters(
    parameters: dict[str, object],
    message: str,
) -> None:
    with pytest.raises((nb.ConfigurationError, nb.ValidationError), match=message):
        nb.score(
            _feature_graph(),
            method="link_prediction_iforest",
            **parameters,
        )


def test_link_prediction_iforest_reports_missing_optional_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_dependency(_: str) -> object:
        raise ImportError("missing scikit-learn")

    monkeypatch.setattr(iforest_method, "import_module", missing_dependency)

    with pytest.raises(nb.ConfigurationError, match=r"pip install \"\.\[ml\]\""):
        nb.score(
            _feature_graph(),
            method="link_prediction_iforest",
            similarities="preferential_attachment",
        )


def _feature_graph() -> nx.Graph:
    graph = nx.Graph()
    graph.add_edges_from(
        [
            ("a", "b"),
            ("a", "c"),
            ("b", "c"),
            ("b", "d"),
            ("c", "d"),
            ("c", "e"),
            ("d", "e"),
            ("e", "f"),
        ]
    )
    return graph
