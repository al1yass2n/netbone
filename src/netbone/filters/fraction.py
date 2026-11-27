"""Retained-fraction filter for method statistics."""

from __future__ import annotations

import math
import random

import pandas as pd

from netbone.exceptions import ConfigurationError, ValidationError
from netbone.filters._utils import id_column, numeric_parameter, numeric_statistic
from netbone.results import VALID_DIRECTIONS, MethodResult, Selection

TIE_POLICIES = frozenset(
    {"exact_stable", "include_all_ties", "raise_on_tie", "random_seeded"}
)


def apply_fraction(
    method_result: MethodResult,
    *,
    fraction: object,
    statistic: str | None = None,
    direction: str | None = None,
    tie_policy: str = "include_all_ties",
    random_seed: object | None = None,
    drop_isolates: bool = False,
) -> Selection:
    """Select the top retained fraction of method statistics.

    The method result's `preferred_direction` controls the ordering. Lower
    values are preferred for p-values and higher values are preferred for
    ordinary scores.

    Args:
        method_result: Method statistics to filter.
        fraction: Requested retained fraction in the closed interval [0, 1].
        statistic: Optional statistic column. Defaults to the method result's
            primary statistic.
        direction: Optional ranking direction override. When omitted, the
            method result's preferred direction is used unless the method
            requires explicit direction.
        tie_policy: One of `include_all_ties`, `exact_stable`, `raise_on_tie`,
            or `random_seeded`.
        random_seed: Required integer seed when `tie_policy="random_seeded"`.
        drop_isolates: Whether edge extraction should remove isolated nodes
            after filtering.

    Raises:
        ConfigurationError: If the tie policy or statistic is invalid.
        ValidationError: If the fraction or statistic values are invalid.
    """

    if tie_policy not in TIE_POLICIES:
        allowed = ", ".join(sorted(TIE_POLICIES))
        raise ConfigurationError(
            f"Unknown tie_policy {tie_policy!r}. Expected one of: {allowed}."
        )
    resolved_random_seed = _resolve_random_seed(tie_policy, random_seed)
    resolved_direction = _resolve_direction(method_result, direction)

    requested_fraction = numeric_parameter(fraction, name="Fraction")
    if requested_fraction < 0.0 or requested_fraction > 1.0:
        raise ValidationError("Fraction must be between 0 and 1.")

    resolved_statistic, series = numeric_statistic(method_result, statistic)
    count = len(method_result.statistics)
    # Round away binary floating-point noise first, so 0.07 * 100 keeps 7 items.
    requested_count = math.ceil(round(requested_fraction * count, 9))
    sorted_rows = _sorted_rows(method_result, series, direction=resolved_direction)
    affected_tied_ids: list[int] = []

    warnings: tuple[str, ...] = ()
    if count == 0 or requested_count == 0:
        mask = pd.Series(False, index=method_result.statistics.index)
    elif requested_count >= count:
        mask = pd.Series(True, index=method_result.statistics.index)
    elif tie_policy == "include_all_ties":
        cutoff = float(sorted_rows.iloc[requested_count - 1]["value"])
        affected_tied_ids = _cutoff_tied_ids(sorted_rows, cutoff)
        mask = series <= cutoff if resolved_direction == "lower" else series >= cutoff
        actual_count = int(mask.sum())
        if actual_count != requested_count:
            warnings = (
                "Fraction filter retained additional tied items at the cutoff; "
                f"requested {requested_count}, retained {actual_count}.",
            )
    elif tie_policy == "random_seeded":
        cutoff = float(sorted_rows.iloc[requested_count - 1]["value"])
        affected_tied_ids = _cutoff_tied_ids(sorted_rows, cutoff)
        mask = _random_seeded_mask(
            method_result,
            series,
            cutoff=cutoff,
            requested_count=requested_count,
            direction=resolved_direction,
            random_seed=resolved_random_seed,
        )
        if _tie_crosses_cutoff(sorted_rows, requested_count):
            warnings = (
                "Fraction filter selected tied items at the cutoff using "
                f"random_seed={resolved_random_seed}.",
            )
    else:
        if _tie_crosses_cutoff(sorted_rows, requested_count):
            cutoff = float(sorted_rows.iloc[requested_count - 1]["value"])
            affected_tied_ids = _cutoff_tied_ids(sorted_rows, cutoff)
            if tie_policy == "raise_on_tie":
                raise ConfigurationError(
                    "Fraction filter encountered a tie at the cutoff. Use "
                    "tie_policy='include_all_ties' to retain all tied items or "
                    "tie_policy='exact_stable' or tie_policy='random_seeded' "
                    "to break ties."
                )
            warnings = (
                "Fraction filter truncated tied items at the cutoff using stable "
                "id ordering.",
            )
        selected_index = set(sorted_rows.head(requested_count)["index"].tolist())
        mask = method_result.statistics.index.to_series().isin(selected_index)

    selected_ids, rejected_ids = _ids_from_mask(method_result, mask)
    return Selection(
        target=method_result.target,
        selected_ids=selected_ids,
        rejected_ids=rejected_ids,
        statistic=resolved_statistic,
        parameters={
            "strategy": "fraction",
            "statistic": resolved_statistic,
            "fraction": requested_fraction,
            "direction": resolved_direction,
            "tie_policy": tie_policy,
            "requested_count": requested_count,
            "actual_count": len(selected_ids),
            "drop_isolates": drop_isolates,
            **_random_seed_parameters(tie_policy, resolved_random_seed),
            "affected_tied_ids": affected_tied_ids,
        },
        mask=mask.astype(bool),
        warnings=warnings,
    )


def _resolve_direction(
    method_result: MethodResult,
    direction: str | None,
) -> str:
    if direction is None:
        if method_result.metadata.get("requires_fraction_direction") is True:
            raise ConfigurationError(
                f"Fraction filter for method {method_result.method_name!r} "
                "requires parameter direction='higher' or direction='lower'. "
                "Use direction='higher' for a high-similarity backbone and "
                "direction='lower' for a low-similarity backbone."
            )
        return method_result.preferred_direction
    if direction not in VALID_DIRECTIONS:
        allowed = ", ".join(sorted(VALID_DIRECTIONS))
        raise ConfigurationError(
            f"Unknown fraction direction {direction!r}. Expected one of: {allowed}."
        )
    return direction


def _sorted_rows(
    method_result: MethodResult,
    series: pd.Series,
    *,
    direction: str,
) -> pd.DataFrame:
    identifier_column = id_column(method_result)
    rows = pd.DataFrame(
        {
            "index": method_result.statistics.index,
            "value": series,
            "id": method_result.statistics[identifier_column].astype(int),
        }
    )
    return rows.sort_values(
        by=["value", "id"],
        ascending=[direction == "lower", True],
        kind="mergesort",
    ).reset_index(drop=True)


def _tie_crosses_cutoff(sorted_rows: pd.DataFrame, requested_count: int) -> bool:
    if requested_count <= 0 or requested_count >= len(sorted_rows):
        return False
    cutoff = float(sorted_rows.iloc[requested_count - 1]["value"])
    next_value = float(sorted_rows.iloc[requested_count]["value"])
    return cutoff == next_value


def _cutoff_tied_ids(sorted_rows: pd.DataFrame, cutoff: float) -> list[int]:
    tied_rows = sorted_rows[sorted_rows["value"] == cutoff]
    if len(tied_rows) <= 1:
        return []
    return [int(identifier) for identifier in tied_rows["id"].tolist()]


def _random_seeded_mask(
    method_result: MethodResult,
    series: pd.Series,
    *,
    cutoff: float,
    requested_count: int,
    direction: str,
    random_seed: int,
) -> pd.Series:
    identifier_column = id_column(method_result)
    better_mask = series < cutoff if direction == "lower" else series > cutoff
    tied_rows = method_result.statistics.loc[
        series == cutoff, [identifier_column]
    ].copy()
    tied_rows[identifier_column] = tied_rows[identifier_column].astype(int)
    tied_ids = sorted(tied_rows[identifier_column].tolist())
    needed_from_ties = requested_count - int(better_mask.sum())
    chosen_tie_ids = set(random.Random(random_seed).sample(tied_ids, needed_from_ties))
    chosen_tie_mask = (series == cutoff) & method_result.statistics[
        identifier_column
    ].astype(int).isin(chosen_tie_ids)
    return better_mask | chosen_tie_mask


def _resolve_random_seed(
    tie_policy: str,
    random_seed: object | None,
) -> int:
    if tie_policy != "random_seeded":
        return 0
    if isinstance(random_seed, bool) or not isinstance(random_seed, int):
        raise ConfigurationError(
            "Fraction tie_policy='random_seeded' requires integer parameter "
            "'random_seed'."
        )
    return random_seed


def _random_seed_parameters(
    tie_policy: str,
    random_seed: int,
) -> dict[str, object]:
    if tie_policy != "random_seeded":
        return {}
    return {"random_seed": random_seed}


def _ids_from_mask(
    method_result: MethodResult,
    mask: pd.Series,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
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
