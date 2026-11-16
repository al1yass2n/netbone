from __future__ import annotations

import networkx as nx
import pandas as pd
import pytest

import netbone as nb
from netbone.filters.significance import apply_significance
from netbone.results import MethodResult, Selection


def _pvalue_result() -> MethodResult:
    return MethodResult(
        method_name="disparity",
        target="edge",
        statistics=pd.DataFrame(
            {
                "edge_id": [0, 1, 2],
                "source_id": [0, 1, 2],
                "target_id": [1, 2, 3],
                "source": ["a", "b", "c"],
                "target": ["b", "c", "d"],
                "pvalue": [0.01, 0.03, 0.20],
            }
        ),
        primary_statistic="pvalue",
        output_type="pvalue",
        preferred_direction="lower",
        parameters={},
        metadata={"default_filter": "significance"},
    )


def test_significance_selects_pvalues_under_alpha() -> None:
    selection = apply_significance(_pvalue_result(), alpha=0.05)

    assert selection.selected_ids == (0, 1)
    assert selection.rejected_ids == (2,)
    assert selection.parameters["correction"] == "none"
    assert selection.warnings == (
        "Significance filter used without multiple-testing correction.",
    )


def test_significance_rejects_pvalues_equal_to_alpha() -> None:
    selection = apply_significance(_pvalue_result(), alpha=0.03)

    assert selection.selected_ids == (0,)
    assert selection.rejected_ids == (1, 2)


def test_significance_applies_bonferroni_correction() -> None:
    selection = apply_significance(
        _pvalue_result(),
        alpha=0.05,
        correction="bonferroni",
    )

    assert selection.selected_ids == (0,)
    assert selection.rejected_ids == (1, 2)
    assert selection.warnings == ()


def test_significance_applies_fdr_bh_correction() -> None:
    selection = apply_significance(
        _pvalue_result(),
        alpha=0.05,
        correction="fdr_bh",
    )

    assert selection.selected_ids == (0, 1)
    assert selection.rejected_ids == (2,)


def test_significance_rejects_score_outputs() -> None:
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
                "score": [1.0],
            }
        ),
        primary_statistic="score",
        output_type="score",
        preferred_direction="higher",
        parameters={},
        metadata={},
    )

    with pytest.raises(nb.ConfigurationError, match="output_type 'pvalue'"):
        apply_significance(result)


def test_default_filter_rejects_method_without_default() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1.0)

    with pytest.raises(nb.ConfigurationError, match="does not define a default"):
        (
            nb.pipeline()
            .score("edge_weight", weight="weight")
            .filter("default")
            .run(graph)
        )


def test_custom_filter_callable_can_select_from_method_result() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=3.0)
    graph.add_edge("b", "c", weight=1.0)

    def keep_first(
        method_result: MethodResult,
        original_graph: nx.Graph,
        *,
        label: str,
    ) -> Selection:
        assert sorted(original_graph.nodes()) == ["a", "b", "c"]
        mask = method_result.statistics["edge_id"] == 0
        return Selection(
            target="edge",
            selected_ids=(0,),
            rejected_ids=(1,),
            statistic=method_result.primary_statistic,
            parameters={"strategy": label},
            mask=mask,
        )

    result = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter(keep_first, label="custom_keep_first")
        .run(graph)
    )

    assert sorted(result.graph.edges()) == [("a", "b")]
    assert result.pipeline_config["filter"]["name"] == "custom"
    assert result.pipeline_config["filter"]["callable"] == "keep_first"
