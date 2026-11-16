"""Optional Matplotlib plotting helpers for Netbone results."""

from __future__ import annotations

import math
from importlib import import_module
from typing import Any

import pandas as pd

from netbone.compare import Comparison
from netbone.exceptions import ConfigurationError
from netbone.sweep import SweepResult


def plot_comparison_metric(
    comparison: Comparison,
    metric: str,
    *,
    ax: Any | None = None,
) -> Any:
    """Plot one single-result comparison metric and return a Matplotlib axes."""

    table = _plottable_rows(
        comparison.metric(metric),
        label_column="result",
        value_column="value",
    )
    axes = _axes(ax)
    axes.bar(table["result"].astype(str).tolist(), table["value"].tolist())
    axes.set_xlabel("Result")
    axes.set_ylabel(metric)
    axes.set_title(metric)
    return axes


def plot_pairwise_metric(
    comparison: Comparison,
    metric: str,
    *,
    ax: Any | None = None,
) -> Any:
    """Plot one pairwise comparison metric and return a Matplotlib axes."""

    table = comparison.pairwise(metrics=[metric]).copy()
    table["pair"] = (
        table["result_a"].astype(str) + " vs " + table["result_b"].astype(str)
    )
    table = _plottable_rows(table, label_column="pair", value_column="value")
    axes = _axes(ax)
    axes.bar(table["pair"].tolist(), table["value"].tolist())
    axes.set_xlabel("Pair")
    axes.set_ylabel(metric)
    axes.set_title(metric)
    return axes


def plot_sweep_metric(
    sweep_result: SweepResult,
    metric: str,
    *,
    x: str = "parameter_value",
    group_by: str = "method",
    ax: Any | None = None,
) -> Any:
    """Plot one sweep metric trajectory and return a Matplotlib axes."""

    table = sweep_result.table()
    if x not in table.columns:
        raise ConfigurationError(f"Sweep plot x column {x!r} does not exist.")
    if group_by not in table.columns:
        raise ConfigurationError(
            f"Sweep plot group_by column {group_by!r} does not exist."
        )

    metric_rows = table[table["metric"] == metric].copy()
    metric_rows = _plottable_rows(
        metric_rows,
        label_column=x,
        value_column="value",
    )
    axes = _axes(ax)
    for group_name, group in metric_rows.groupby(group_by, dropna=False):
        group = group.sort_values(by=x, key=lambda values: values.astype(str))
        x_values = group[x].tolist()
        axes.plot(x_values, group["value"].tolist(), marker="o", label=str(group_name))
    axes.set_xlabel(x)
    axes.set_ylabel(metric)
    axes.set_title(metric)
    if metric_rows[group_by].nunique(dropna=False) > 1:
        axes.legend()
    return axes


def _axes(ax: Any | None) -> Any:
    if ax is not None:
        return ax
    pyplot = _require_pyplot()
    axes = _subplots(pyplot)
    return axes


def _require_pyplot() -> Any:
    try:
        pyplot = import_module("matplotlib.pyplot")
    except ImportError as exc:
        raise ConfigurationError(
            "Optional plotting requires Matplotlib. Install Netbone with "
            "`netbone[viz]` to use netbone.viz plotting helpers."
        ) from exc
    return pyplot


def _subplots(pyplot: Any) -> Any:
    try:
        _, axes = pyplot.subplots()
    except Exception as exc:
        try:
            pyplot.switch_backend("Agg")
            _, axes = pyplot.subplots()
        except Exception as fallback_exc:
            raise ConfigurationError(
                "Matplotlib is installed but could not create a figure. Configure "
                "a working Matplotlib backend or use a non-interactive backend "
                "such as 'Agg'."
            ) from fallback_exc
        if axes is None:
            raise ConfigurationError(
                "Matplotlib did not return an axes object."
            ) from exc
    return axes


def _plottable_rows(
    table: pd.DataFrame,
    *,
    label_column: str,
    value_column: str,
) -> pd.DataFrame:
    ok_rows = table[table["status"] == "ok"].copy()
    ok_rows[value_column] = pd.to_numeric(ok_rows[value_column], errors="coerce")
    ok_rows = ok_rows[
        ok_rows[value_column].map(
            lambda value: isinstance(value, int | float) and math.isfinite(value)
        )
    ]
    if ok_rows.empty:
        raise ConfigurationError(
            "No plottable metric rows are available. Plotting uses rows with "
            "status 'ok' and finite numeric values."
        )
    if label_column not in ok_rows.columns:
        raise ConfigurationError(f"Plot label column {label_column!r} does not exist.")
    return ok_rows
