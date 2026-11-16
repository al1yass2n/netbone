from __future__ import annotations

import networkx as nx
import pandas as pd
import pytest

import netbone as nb
from netbone.filters.fraction import apply_fraction
from netbone.results import MethodResult


def _score_result() -> MethodResult:
    return MethodResult(
        method_name="edge_weight",
        target="edge",
        statistics=pd.DataFrame(
            {
                "edge_id": [0, 1, 2, 3],
                "source_id": [0, 1, 2, 3],
                "target_id": [1, 2, 3, 4],
                "source": ["a", "b", "c", "d"],
                "target": ["b", "c", "d", "e"],
                "score": [10.0, 8.0, 8.0, 1.0],
            }
        ),
        primary_statistic="score",
        output_type="score",
        preferred_direction="higher",
        parameters={},
        metadata={},
    )


def test_fraction_include_all_ties_retains_boundary_ties() -> None:
    selection = apply_fraction(_score_result(), fraction=0.5)

    assert selection.selected_ids == (0, 1, 2)
    assert selection.rejected_ids == (3,)
    assert selection.parameters["requested_count"] == 2
    assert selection.parameters["actual_count"] == 3
    assert selection.warnings


def test_fraction_exact_stable_truncates_ties_by_id() -> None:
    selection = apply_fraction(
        _score_result(),
        fraction=0.5,
        tie_policy="exact_stable",
    )

    assert selection.selected_ids == (0, 1)
    assert selection.rejected_ids == (2, 3)
    assert selection.warnings


def test_fraction_raise_on_tie_rejects_boundary_ties() -> None:
    with pytest.raises(nb.ConfigurationError, match="tie at the cutoff"):
        apply_fraction(_score_result(), fraction=0.5, tie_policy="raise_on_tie")


def test_fraction_random_seeded_breaks_ties_reproducibly() -> None:
    first = apply_fraction(
        _score_result(),
        fraction=0.5,
        tie_policy="random_seeded",
        random_seed=17,
    )
    second = apply_fraction(
        _score_result(),
        fraction=0.5,
        tie_policy="random_seeded",
        random_seed=17,
    )

    assert first.selected_ids == second.selected_ids
    assert len(first.selected_ids) == 2
    assert first.selected_ids[0] == 0
    assert set(first.selected_ids[1:]).issubset({1, 2})
    assert first.parameters["random_seed"] == 17
    assert first.parameters["affected_tied_ids"] == [1, 2]
    assert first.warnings


def test_fraction_random_seeded_requires_seed() -> None:
    with pytest.raises(nb.ConfigurationError, match="requires integer"):
        apply_fraction(_score_result(), fraction=0.5, tie_policy="random_seeded")


def test_fraction_uses_lower_preferred_direction_for_pvalues() -> None:
    result = MethodResult(
        method_name="pvalue_method",
        target="edge",
        statistics=pd.DataFrame(
            {
                "edge_id": [0, 1, 2],
                "source_id": [0, 1, 2],
                "target_id": [1, 2, 3],
                "source": ["a", "b", "c"],
                "target": ["b", "c", "d"],
                "pvalue": [0.02, 0.30, 0.01],
            }
        ),
        primary_statistic="pvalue",
        output_type="pvalue",
        preferred_direction="lower",
        parameters={},
        metadata={},
    )

    selection = apply_fraction(result, fraction=1 / 3)

    assert selection.selected_ids == (2,)
    assert selection.rejected_ids == (0, 1)


def test_fraction_direction_overrides_method_preferred_direction() -> None:
    selection = apply_fraction(_score_result(), fraction=0.25, direction="lower")

    assert selection.selected_ids == (3,)
    assert selection.rejected_ids == (0, 1, 2)
    assert selection.parameters["direction"] == "lower"


def test_fraction_can_require_explicit_direction() -> None:
    result = MethodResult(
        method_name="directional_method",
        target="edge",
        statistics=pd.DataFrame(
            {
                "edge_id": [0, 1],
                "source_id": [0, 1],
                "target_id": [1, 2],
                "source": ["a", "b"],
                "target": ["b", "c"],
                "score": [2.0, 1.0],
            }
        ),
        primary_statistic="score",
        output_type="score",
        preferred_direction="higher",
        parameters={},
        metadata={"requires_fraction_direction": True},
    )

    with pytest.raises(nb.ConfigurationError, match="requires parameter direction"):
        apply_fraction(result, fraction=0.5)


def test_fraction_rejects_unknown_direction() -> None:
    with pytest.raises(nb.ConfigurationError, match="Unknown fraction direction"):
        apply_fraction(_score_result(), fraction=0.25, direction="sideways")


def test_pipeline_runs_fraction_filter() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("b", "c", weight=2.0)
    graph.add_edge("c", "d", weight=1.0)

    result = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("fraction", fraction=1 / 3)
        .run(graph)
    )

    assert sorted(result.graph.edges()) == [("a", "b")]
    assert result.selection.parameters["tie_policy"] == "include_all_ties"
