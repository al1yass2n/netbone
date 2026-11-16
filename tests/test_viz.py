from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb
from netbone import viz


class FakeAxes:
    def __init__(self) -> None:
        self.bars: list[tuple[list[object], list[object]]] = []
        self.lines: list[tuple[list[object], list[object], str | None]] = []
        self.labels: dict[str, object] = {}
        self.legend_called = False

    def bar(self, labels: list[object], values: list[object]) -> None:
        self.bars.append((labels, values))

    def plot(
        self,
        x_values: list[object],
        y_values: list[object],
        *,
        marker: str,
        label: str | None = None,
    ) -> None:
        self.lines.append((x_values, y_values, label))
        self.labels["marker"] = marker

    def set_xlabel(self, label: str) -> None:
        self.labels["x"] = label

    def set_ylabel(self, label: str) -> None:
        self.labels["y"] = label

    def set_title(self, title: str) -> None:
        self.labels["title"] = title

    def legend(self) -> None:
        self.legend_called = True


def _graph() -> nx.Graph:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=4.0)
    graph.add_edge("b", "c", weight=2.0)
    graph.add_edge("c", "d", weight=1.0)
    return graph


def _result(value: float) -> nb.BackboneResult:
    return (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("threshold", value=value, operator="greater_equal")
        .run(_graph())
    )


def test_plot_comparison_metric_uses_ok_single_metric_rows() -> None:
    axes = FakeAxes()
    comparison = nb.compare({"strict": _result(4.0), "loose": _result(2.0)})

    returned = viz.plot_comparison_metric(comparison, "edge_count", ax=axes)

    assert returned is axes
    assert axes.bars == [(["strict", "loose"], [1, 2])]
    assert axes.labels == {
        "x": "Result",
        "y": "edge_count",
        "title": "edge_count",
    }


def test_plot_pairwise_metric_uses_ok_pairwise_rows() -> None:
    axes = FakeAxes()
    comparison = nb.compare({"strict": _result(4.0), "loose": _result(2.0)})

    viz.plot_pairwise_metric(comparison, "edge_jaccard", ax=axes)

    assert axes.bars == [(["strict vs loose"], [0.5])]
    assert axes.labels["x"] == "Pair"
    assert axes.labels["y"] == "edge_jaccard"


def test_plot_sweep_metric_groups_metric_rows() -> None:
    axes = FakeAxes()
    result = (
        nb.sweep(_graph())
        .score("edge_weight", weight="weight")
        .filter("threshold", operator="greater_equal")
        .vary_filter(value=[4.0, 2.0])
        .measure(["edge_count"])
        .run()
    )

    viz.plot_sweep_metric(result, "edge_count", x="parameter_value", ax=axes)

    assert axes.lines == [([2.0, 4.0], [2, 1], "edge_weight")]
    assert axes.labels["x"] == "parameter_value"
    assert axes.labels["y"] == "edge_count"
    assert not axes.legend_called


def test_plotting_rejects_missing_matplotlib_when_no_axes_is_passed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    comparison = nb.compare({"strict": _result(4.0)})

    def missing_matplotlib(_: str) -> object:
        raise ImportError("missing matplotlib")

    monkeypatch.setattr(viz, "import_module", missing_matplotlib)

    with pytest.raises(nb.ConfigurationError, match="netbone\\[viz\\]"):
        viz.plot_comparison_metric(comparison, "edge_count")


def test_plotting_rejects_no_plottable_metric_rows() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight="bad")
    result = (
        nb.pipeline()
        .score("edge_weight", weight=None)
        .filter("threshold", value=0.5, operator="greater_equal")
        .run(graph)
    )

    with pytest.raises(nb.ConfigurationError, match="No plottable metric rows"):
        viz.plot_comparison_metric(
            nb.compare({"bad_weight": result}),
            "weight_retention",
            ax=FakeAxes(),
        )


def test_sweep_plot_rejects_unknown_columns() -> None:
    result = (
        nb.sweep(_graph())
        .score("edge_weight", weight="weight")
        .filter("threshold", value=2.0, operator="greater_equal")
        .measure(["edge_count"])
        .run()
    )

    with pytest.raises(nb.ConfigurationError, match="x column"):
        viz.plot_sweep_metric(result, "edge_count", x="missing", ax=FakeAxes())

    with pytest.raises(nb.ConfigurationError, match="group_by column"):
        viz.plot_sweep_metric(
            result,
            "edge_count",
            group_by="missing",
            ax=FakeAxes(),
        )
