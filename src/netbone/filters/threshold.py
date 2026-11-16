"""Threshold filter for method statistics."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from netbone.exceptions import ConfigurationError
from netbone.filters._utils import (
    numeric_parameter,
    numeric_statistic,
    selected_and_rejected_ids,
)
from netbone.results import MethodResult, Selection

_OPERATORS: dict[str, Callable[[pd.Series, float], pd.Series]] = {
    "greater": lambda series, value: series > value,
    "greater_equal": lambda series, value: series >= value,
    "less": lambda series, value: series < value,
    "less_equal": lambda series, value: series <= value,
    "equal": lambda series, value: series == value,
    "not_equal": lambda series, value: series != value,
}


def apply_threshold(
    method_result: MethodResult,
    *,
    statistic: str | None = None,
    value: object,
    operator: str,
    drop_isolates: bool = False,
) -> Selection:
    """Select rows from method statistics using an explicit threshold operator.

    Args:
        method_result: Method statistics to filter.
        statistic: Optional statistic column to compare. When omitted, the
            method result's primary statistic is used.
        value: Numeric threshold value.
        operator: One of `greater`, `greater_equal`, `less`, `less_equal`,
            `equal`, or `not_equal`.
        drop_isolates: Whether edge extraction should remove isolated nodes
            after filtering.

    Raises:
        ConfigurationError: If the statistic or operator is invalid.
        ValidationError: If the threshold value or statistic values are not
            numeric.
    """

    if operator not in _OPERATORS:
        allowed = ", ".join(sorted(_OPERATORS))
        raise ConfigurationError(
            f"Unknown threshold operator {operator!r}. Expected one of: {allowed}."
        )
    threshold_value = numeric_parameter(value, name="Threshold value")
    resolved_statistic, series = numeric_statistic(method_result, statistic)

    mask = _OPERATORS[operator](series, threshold_value).astype(bool)
    selected_ids, rejected_ids = selected_and_rejected_ids(method_result, mask)

    return Selection(
        target=method_result.target,
        selected_ids=selected_ids,
        rejected_ids=rejected_ids,
        statistic=resolved_statistic,
        parameters={
            "strategy": "threshold",
            "statistic": resolved_statistic,
            "value": threshold_value,
            "operator": operator,
            "drop_isolates": drop_isolates,
        },
        mask=mask,
        warnings=(),
    )
