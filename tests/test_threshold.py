from __future__ import annotations

import networkx as nx
import pandas as pd
import pytest

import netbone as nb
from netbone.filters.threshold import apply_threshold
from netbone.results import MethodResult


def _method_result() -> MethodResult:
    return MethodResult(
        method_name="edge_weight",
        target="edge",
        statistics=pd.DataFrame(
            {
                "edge_id": [0, 1, 2],
                "source_id": [0, 1, 2],
                "target_id": [1, 2, 3],
                "source": ["a", "b", "c"],
                "target": ["b", "c", "d"],
                "score": [1.0, 2.0, 3.0],
            }
        ),
        primary_statistic="score",
        output_type="score",
        preferred_direction="higher",
        parameters={},
        metadata={},
    )


def test_threshold_greater_equal_includes_boundary() -> None:
    selection = apply_threshold(
        _method_result(),
        value=2.0,
        operator="greater_equal",
    )

    assert selection.selected_ids == (1, 2)
    assert selection.rejected_ids == (0,)
    assert selection.statistic == "score"
    assert selection.summary()["selected_fraction"] == 2 / 3


def test_threshold_allows_explicit_statistic_override() -> None:
    selection = apply_threshold(
        _method_result(),
        statistic="score",
        value=2.0,
        operator="less",
        drop_isolates=True,
    )

    assert selection.selected_ids == (0,)
    assert selection.parameters["drop_isolates"] is True


def test_threshold_rejects_missing_statistic() -> None:
    with pytest.raises(nb.ConfigurationError, match="not present"):
        apply_threshold(
            _method_result(),
            statistic="pvalue",
            value=0.05,
            operator="less_equal",
        )


def test_threshold_rejects_unknown_operator() -> None:
    with pytest.raises(nb.ConfigurationError, match="Unknown threshold operator"):
        apply_threshold(
            _method_result(),
            statistic="score",
            value=2.0,
            operator="above",
        )


def test_threshold_rejects_non_numeric_statistic() -> None:
    result = MethodResult(
        method_name="edge_weight",
        target="edge",
        statistics=pd.DataFrame(
            {
                "edge_id": [0],
                "source_id": [0],
                "target_id": [1],
                "source": ["a"],
                "target": ["b"],
                "score": ["high"],
            }
        ),
        primary_statistic="score",
        output_type="score",
        preferred_direction="higher",
        parameters={},
        metadata={},
    )

    with pytest.raises(nb.ValidationError, match="non-numeric"):
        apply_threshold(
            result,
            statistic="score",
            value=2.0,
            operator="greater",
        )


def test_drop_isolates_controls_edge_filter_node_retention() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=5)
    graph.add_edge("b", "c", weight=1)
    graph.add_node("d")

    keep_isolates = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("threshold", value=5, operator="greater_equal")
        .run(graph)
    )
    drop_isolates = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter(
            "threshold",
            value=5,
            operator="greater_equal",
            drop_isolates=True,
        )
        .run(graph)
    )

    assert sorted(keep_isolates.graph.nodes()) == ["a", "b", "c", "d"]
    assert sorted(drop_isolates.graph.nodes()) == ["a", "b"]
