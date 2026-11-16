"""P-value significance filter for method statistics."""

from __future__ import annotations

import pandas as pd

from netbone.exceptions import ConfigurationError, ValidationError
from netbone.filters._utils import (
    numeric_parameter,
    numeric_statistic,
    selected_and_rejected_ids,
)
from netbone.results import MethodResult, Selection

CORRECTIONS = frozenset({"none", "bonferroni", "holm", "fdr_bh"})


def apply_significance(
    method_result: MethodResult,
    *,
    alpha: object = 0.05,
    statistic: str | None = None,
    correction: str | None = "none",
    drop_isolates: bool = False,
) -> Selection:
    """Select method rows whose p-values are significant.

    Args:
        method_result: Method statistics with `output_type="pvalue"`.
        alpha: Significance level in the closed interval [0, 1].
        statistic: Optional p-value column. Defaults to the primary statistic.
        correction: Multiple-testing correction: `none`, `bonferroni`, `holm`,
            or `fdr_bh`.
        drop_isolates: Whether edge extraction should remove isolated nodes
            after filtering.

    Raises:
        ConfigurationError: If the method output or correction is incompatible.
        ValidationError: If alpha or p-values are invalid.
    """

    if method_result.output_type != "pvalue":
        raise ConfigurationError(
            "Significance filter requires method output_type 'pvalue'."
        )

    alpha_value = numeric_parameter(alpha, name="Alpha")
    if alpha_value < 0.0 or alpha_value > 1.0:
        raise ValidationError("Alpha must be between 0 and 1.")

    correction_name = "none" if correction is None else correction
    if correction_name not in CORRECTIONS:
        allowed = ", ".join(sorted(CORRECTIONS))
        raise ConfigurationError(
            f"Unknown correction {correction_name!r}. Expected one of: {allowed}."
        )

    resolved_statistic, pvalues = numeric_statistic(method_result, statistic)
    if ((pvalues < 0.0) | (pvalues > 1.0)).any():
        raise ValidationError(
            f"Statistic {resolved_statistic!r} must contain p-values between 0 and 1."
        )

    adjusted = _adjust_pvalues(pvalues, correction_name)
    mask = (adjusted < alpha_value).astype(bool)
    selected_ids, rejected_ids = selected_and_rejected_ids(method_result, mask)
    warnings = (
        ("Significance filter used without multiple-testing correction.",)
        if correction_name == "none"
        else ()
    )

    return Selection(
        target=method_result.target,
        selected_ids=selected_ids,
        rejected_ids=rejected_ids,
        statistic=resolved_statistic,
        parameters={
            "strategy": "significance",
            "statistic": resolved_statistic,
            "alpha": alpha_value,
            "correction": correction_name,
            "drop_isolates": drop_isolates,
        },
        mask=mask,
        warnings=warnings,
    )


def _adjust_pvalues(pvalues: pd.Series, correction: str) -> pd.Series:
    values = [float(value) for value in pvalues.tolist()]
    count = len(values)
    if correction == "none" or count == 0:
        return pd.Series(values, index=pvalues.index, dtype=float)
    if correction == "bonferroni":
        return pd.Series(
            [min(value * count, 1.0) for value in values],
            index=pvalues.index,
            dtype=float,
        )

    order = sorted(range(count), key=lambda index: values[index])
    adjusted = [0.0] * count

    if correction == "holm":
        maximum = 0.0
        for rank, original_index in enumerate(order):
            raw = (count - rank) * values[original_index]
            maximum = max(maximum, raw)
            adjusted[original_index] = min(maximum, 1.0)
        return pd.Series(adjusted, index=pvalues.index, dtype=float)

    minimum = 1.0
    for reverse_rank, original_index in enumerate(reversed(order), start=1):
        rank = count - reverse_rank + 1
        raw = values[original_index] * count / rank
        minimum = min(minimum, raw)
        adjusted[original_index] = min(minimum, 1.0)
    return pd.Series(adjusted, index=pvalues.index, dtype=float)
