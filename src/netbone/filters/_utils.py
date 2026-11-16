"""Shared helpers for filters."""

from __future__ import annotations

import math
from numbers import Real

import pandas as pd

from netbone.exceptions import ConfigurationError, ValidationError
from netbone.results import MethodResult


def id_column(method_result: MethodResult) -> str:
    """Return the identifier column for a method result target."""

    if method_result.target == "edge":
        return "edge_id"
    if "node_id" not in method_result.statistics.columns:
        raise ConfigurationError("Node statistics must include node_id to be filtered.")
    return "node_id"


def numeric_statistic(
    method_result: MethodResult,
    statistic: str | None,
) -> tuple[str, pd.Series]:
    """Resolve and validate a numeric statistic column."""

    resolved_statistic = (
        method_result.primary_statistic if statistic is None else statistic
    )
    if resolved_statistic not in method_result.statistics.columns:
        raise ConfigurationError(
            f"Statistic {resolved_statistic!r} is not present in method "
            f"{method_result.method_name!r} output."
        )

    series = pd.to_numeric(
        method_result.statistics[resolved_statistic], errors="coerce"
    )
    if series.isna().any():
        raise ValidationError(
            f"Statistic {resolved_statistic!r} contains missing or non-numeric values."
        )
    if not series.map(math.isfinite).all():
        raise ValidationError(f"Statistic {resolved_statistic!r} must be finite.")
    return resolved_statistic, series


def numeric_parameter(
    value: object,
    *,
    name: str,
) -> float:
    """Validate a finite numeric parameter value."""

    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValidationError(f"{name} must be numeric.")
    resolved = float(value)
    if not math.isfinite(resolved):
        raise ValidationError(f"{name} must be finite.")
    return resolved


def selected_and_rejected_ids(
    method_result: MethodResult,
    mask: pd.Series,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Return selected and rejected ids from a boolean mask."""

    identifier_column = id_column(method_result)
    selected_ids = tuple(
        int(identifier)
        for identifier in method_result.statistics.loc[mask, identifier_column].tolist()
    )
    rejected_ids = tuple(
        int(identifier)
        for identifier in method_result.statistics.loc[
            ~mask, identifier_column
        ].tolist()
    )
    return selected_ids, rejected_ids
