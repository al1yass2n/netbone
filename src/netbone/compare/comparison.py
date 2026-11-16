"""Comparison tables for backbone extraction results."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from types import MappingProxyType
from typing import cast

import pandas as pd

from netbone.compare.alignment import (
    aligned_score_table,
    same_original_graph,
    same_original_topology,
    score_incompatibility,
)
from netbone.exceptions import (
    CompatibilityError,
    ConfigurationError,
    NetboneError,
    UndefinedMetricError,
)
from netbone.metrics.registry import (
    MetricDefinition,
    PairwiseMetricCompute,
    SingleMetricCompute,
    get_metric,
)
from netbone.results import BackboneResult

DEFAULT_SINGLE_METRICS = (
    "node_count",
    "edge_count",
    "node_retention",
    "edge_retention",
    "weight_retention",
    "connected_component_count",
    "isolated_node_count",
)
DEFAULT_PAIRWISE_METRICS = (
    "node_overlap",
    "edge_overlap",
    "node_jaccard",
    "edge_jaccard",
    "node_overlap_coefficient",
    "edge_overlap_coefficient",
)


@dataclass(frozen=True)
class Comparison:
    """Compare multiple named backbone extraction results."""

    results: Mapping[str, BackboneResult]

    def __post_init__(self) -> None:
        """Validate and freeze named results."""

        if not self.results:
            raise ConfigurationError("compare() requires at least one named result.")

        copied: dict[str, BackboneResult] = {}
        for name, result in self.results.items():
            if not isinstance(name, str) or not name:
                raise ConfigurationError(
                    "Comparison result names must be non-empty strings."
                )
            if not isinstance(result, BackboneResult):
                raise ConfigurationError(
                    f"Comparison entry {name!r} must be a BackboneResult."
                )
            copied[name] = result
        object.__setattr__(self, "results", MappingProxyType(copied))

    def table(self, metrics: Sequence[str] | None = None) -> pd.DataFrame:
        """Return tidy single-result metric rows."""

        metric_names = DEFAULT_SINGLE_METRICS if metrics is None else tuple(metrics)
        rows: list[dict[str, object]] = []
        for result_name, result in self.results.items():
            for metric_name in metric_names:
                metric = get_metric(metric_name)
                if metric.scope != "single":
                    rows.append(
                        _single_row(
                            result_name=result_name,
                            metric_name=metric_name,
                            value=None,
                            status="invalid",
                            explanation=(
                                f"Metric {metric_name!r} has scope {metric.scope!r}, "
                                "not 'single'."
                            ),
                        )
                    )
                    continue
                compute = cast(SingleMetricCompute, metric.compute)
                try:
                    value = compute(result)
                except UndefinedMetricError as exc:
                    rows.append(
                        _single_row(
                            result_name=result_name,
                            metric_name=metric_name,
                            value=None,
                            status="undefined",
                            explanation=str(exc),
                        )
                    )
                    continue
                except NetboneError as exc:
                    rows.append(
                        _single_row(
                            result_name=result_name,
                            metric_name=metric_name,
                            value=None,
                            status="invalid",
                            explanation=str(exc),
                        )
                    )
                    continue
                rows.append(
                    _single_row(
                        result_name=result_name,
                        metric_name=metric_name,
                        value=value,
                        status="ok",
                        explanation="",
                    )
                )
        return pd.DataFrame(
            rows,
            columns=["result", "metric", "value", "status", "explanation"],
        )

    def metric(self, name: str) -> pd.DataFrame:
        """Return one single-result metric for every result."""

        return self.table(metrics=[name])

    def pairwise(self, metrics: Sequence[str] | None = None) -> pd.DataFrame:
        """Return tidy pairwise metric rows."""

        metric_names = DEFAULT_PAIRWISE_METRICS if metrics is None else tuple(metrics)
        rows: list[dict[str, object]] = []
        for left_name, right_name in combinations(self.results, 2):
            left = self.results[left_name]
            right = self.results[right_name]
            for metric_name in metric_names:
                metric = get_metric(metric_name)
                rows.append(
                    self._pairwise_metric_row(
                        left_name=left_name,
                        right_name=right_name,
                        left=left,
                        right=right,
                        metric=metric,
                    )
                )
        return pd.DataFrame(
            rows,
            columns=[
                "result_a",
                "result_b",
                "metric",
                "value",
                "status",
                "explanation",
                "same_original_graph",
                "same_original_topology",
                "same_target",
            ],
        )

    def score_alignment(self, result_a: str, result_b: str) -> pd.DataFrame:
        """Return aligned method statistics for two compatible results."""

        left = self._result(result_a)
        right = self._result(result_b)
        explanation = score_incompatibility(left, right)
        if explanation:
            raise ConfigurationError(explanation)
        return aligned_score_table(
            result_a,
            result_b,
            left.method_result,
            right.method_result,
            directed=left.original_graph.is_directed(),
        )

    def spearman(self) -> pd.DataFrame:
        """Return pairwise Spearman score correlations where valid."""

        return self.pairwise(metrics=["score_spearman"])

    @property
    def plot_data(self) -> dict[str, pd.DataFrame]:
        """Return plot-ready comparison data."""

        return {
            "single_metrics": self.table(),
            "pairwise_metrics": self.pairwise(),
        }

    def _result(self, name: str) -> BackboneResult:
        try:
            return self.results[name]
        except KeyError as exc:
            available = ", ".join(self.results)
            raise ConfigurationError(
                f"Unknown comparison result {name!r}. Available results: {available}."
            ) from exc

    def _pairwise_metric_row(
        self,
        *,
        left_name: str,
        right_name: str,
        left: BackboneResult,
        right: BackboneResult,
        metric: MetricDefinition,
    ) -> dict[str, object]:
        same_original = same_original_graph(left, right)
        same_topology = same_original_topology(left, right)
        same_target = left.method_result.target == right.method_result.target
        if metric.scope != "pairwise":
            return _pairwise_row(
                left_name=left_name,
                right_name=right_name,
                metric_name=metric.name,
                value=None,
                status="invalid",
                explanation=(
                    f"Metric {metric.name!r} has scope {metric.scope!r}, "
                    "not 'pairwise'."
                ),
                same_original_graph=same_original,
                same_original_topology=same_topology,
                same_target=same_target,
            )
        if not same_topology:
            return _pairwise_row(
                left_name=left_name,
                right_name=right_name,
                metric_name=metric.name,
                value=None,
                status="invalid",
                explanation=(
                    "Pairwise backbone metrics require the same original graph "
                    "topology."
                ),
                same_original_graph=same_original,
                same_original_topology=False,
                same_target=same_target,
            )

        compute = cast(PairwiseMetricCompute, metric.compute)
        try:
            value = compute(left, right)
        except UndefinedMetricError as exc:
            return _pairwise_row(
                left_name=left_name,
                right_name=right_name,
                metric_name=metric.name,
                value=None,
                status="undefined",
                explanation=str(exc),
                same_original_graph=same_original,
                same_original_topology=True,
                same_target=same_target,
            )
        except CompatibilityError as exc:
            return _pairwise_row(
                left_name=left_name,
                right_name=right_name,
                metric_name=metric.name,
                value=None,
                status="invalid",
                explanation=str(exc),
                same_original_graph=same_original,
                same_original_topology=True,
                same_target=same_target,
            )
        return _pairwise_row(
            left_name=left_name,
            right_name=right_name,
            metric_name=metric.name,
            value=value,
            status="ok",
            explanation="",
            same_original_graph=same_original,
            same_original_topology=True,
            same_target=same_target,
        )


def compare(results: Mapping[str, BackboneResult]) -> Comparison:
    """Return a comparison object for named backbone results."""

    return Comparison(results=results)


def _single_row(
    *,
    result_name: str,
    metric_name: str,
    value: object,
    status: str,
    explanation: str,
) -> dict[str, object]:
    return {
        "result": result_name,
        "metric": metric_name,
        "value": value,
        "status": status,
        "explanation": explanation,
    }


def _pairwise_row(
    *,
    left_name: str,
    right_name: str,
    metric_name: str,
    value: object,
    status: str,
    explanation: str,
    same_original_graph: bool,
    same_original_topology: bool,
    same_target: bool,
) -> dict[str, object]:
    return {
        "result_a": left_name,
        "result_b": right_name,
        "metric": metric_name,
        "value": value,
        "status": status,
        "explanation": explanation,
        "same_original_graph": same_original_graph,
        "same_original_topology": same_original_topology,
        "same_target": same_target,
    }
