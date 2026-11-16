"""Registry for built-in filters."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from netbone.exceptions import ConfigurationError
from netbone.filters.fraction import TIE_POLICIES, apply_fraction
from netbone.filters.significance import CORRECTIONS, apply_significance
from netbone.filters.threshold import apply_threshold
from netbone.results import MethodResult, Selection

FilterApply = Callable[[MethodResult, Mapping[str, object]], Selection]


@dataclass(frozen=True)
class FilterDefinition:
    """Registered filter metadata and execution hook."""

    name: str
    metadata: Mapping[str, object]
    apply: FilterApply

    def __post_init__(self) -> None:
        """Freeze metadata for registry callers."""

        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


def list_filters() -> tuple[str, ...]:
    """Return registered built-in filter names."""

    return tuple(sorted(_FILTERS))


def describe_filter(name: str) -> dict[str, object]:
    """Return JSON-compatible metadata for a registered filter."""

    return dict(get_filter(name).metadata)


def get_filter(name: str) -> FilterDefinition:
    """Return a registered filter definition.

    Raises:
        ConfigurationError: If the filter name is unknown.
    """

    try:
        return _FILTERS[name]
    except KeyError as exc:
        allowed = ", ".join(list_filters())
        raise ConfigurationError(
            f"Unknown filter strategy {name!r}. Available filters: {allowed}."
        ) from exc


def _reject_unknown_parameters(
    filter_name: str,
    parameters: Mapping[str, object],
    allowed: set[str],
) -> None:
    unknown_parameters = set(parameters).difference(allowed)
    if unknown_parameters:
        unknown = ", ".join(sorted(str(name) for name in unknown_parameters))
        raise ConfigurationError(
            f"{filter_name} filter does not accept parameter(s): {unknown}."
        )


def _apply_threshold(
    method_result: MethodResult,
    parameters: Mapping[str, object],
) -> Selection:
    _reject_unknown_parameters(
        "threshold",
        parameters,
        {"drop_isolates", "operator", "statistic", "value"},
    )
    missing = {name for name in ("value", "operator") if name not in parameters}
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ConfigurationError(
            f"Threshold filter is missing required parameter(s): {missing_text}."
        )
    statistic = parameters.get("statistic")
    operator = parameters["operator"]
    drop_isolates = parameters.get("drop_isolates", False)
    if statistic is not None and not isinstance(statistic, str):
        raise ConfigurationError("Threshold parameter 'statistic' must be a string.")
    if not isinstance(operator, str):
        raise ConfigurationError("Threshold parameter 'operator' must be a string.")
    if not isinstance(drop_isolates, bool):
        raise ConfigurationError(
            "Threshold parameter 'drop_isolates' must be a boolean."
        )
    return apply_threshold(
        method_result,
        statistic=statistic,
        value=parameters["value"],
        operator=operator,
        drop_isolates=drop_isolates,
    )


def _apply_fraction(
    method_result: MethodResult,
    parameters: Mapping[str, object],
) -> Selection:
    _reject_unknown_parameters(
        "fraction",
        parameters,
        {
            "direction",
            "drop_isolates",
            "fraction",
            "random_seed",
            "statistic",
            "tie_policy",
        },
    )
    if "fraction" not in parameters:
        raise ConfigurationError(
            "Fraction filter is missing required parameter(s): fraction."
        )
    statistic = parameters.get("statistic")
    direction = parameters.get("direction")
    tie_policy = parameters.get("tie_policy", "include_all_ties")
    random_seed = parameters.get("random_seed")
    drop_isolates = parameters.get("drop_isolates", False)
    if statistic is not None and not isinstance(statistic, str):
        raise ConfigurationError("Fraction parameter 'statistic' must be a string.")
    if direction is not None and not isinstance(direction, str):
        raise ConfigurationError("Fraction parameter 'direction' must be a string.")
    if not isinstance(tie_policy, str):
        raise ConfigurationError("Fraction parameter 'tie_policy' must be a string.")
    if not isinstance(drop_isolates, bool):
        raise ConfigurationError(
            "Fraction parameter 'drop_isolates' must be a boolean."
        )
    return apply_fraction(
        method_result,
        fraction=parameters["fraction"],
        statistic=statistic,
        direction=direction,
        tie_policy=tie_policy,
        random_seed=random_seed,
        drop_isolates=drop_isolates,
    )


def _apply_significance(
    method_result: MethodResult,
    parameters: Mapping[str, object],
) -> Selection:
    _reject_unknown_parameters(
        "significance",
        parameters,
        {"alpha", "correction", "drop_isolates", "statistic"},
    )
    statistic = parameters.get("statistic")
    correction = parameters.get("correction", "none")
    drop_isolates = parameters.get("drop_isolates", False)
    if statistic is not None and not isinstance(statistic, str):
        raise ConfigurationError("Significance parameter 'statistic' must be a string.")
    if correction is not None and not isinstance(correction, str):
        raise ConfigurationError(
            "Significance parameter 'correction' must be a string or None."
        )
    if not isinstance(drop_isolates, bool):
        raise ConfigurationError(
            "Significance parameter 'drop_isolates' must be a boolean."
        )
    return apply_significance(
        method_result,
        alpha=parameters.get("alpha", 0.05),
        statistic=statistic,
        correction=correction,
        drop_isolates=drop_isolates,
    )


def _apply_default(
    method_result: MethodResult,
    parameters: Mapping[str, object],
) -> Selection:
    default_filter = method_result.metadata.get("default_filter")
    if not isinstance(default_filter, str):
        raise ConfigurationError(
            f"Method {method_result.method_name!r} does not define a default filter."
        )
    if default_filter == "default":
        raise ConfigurationError(
            f"Method {method_result.method_name!r} defines an invalid recursive "
            "default filter."
        )
    default_parameters = method_result.metadata.get("default_filter_parameters", {})
    if not isinstance(default_parameters, Mapping):
        raise ConfigurationError(
            f"Method {method_result.method_name!r} defines invalid default filter "
            "parameters."
        )
    resolved_parameters = {**dict(default_parameters), **dict(parameters)}
    return get_filter(default_filter).apply(method_result, resolved_parameters)


_FILTERS: dict[str, FilterDefinition] = {
    "threshold": FilterDefinition(
        name="threshold",
        metadata={
            "name": "threshold",
            "display_name": "Threshold Filter",
            "compatible_output_types": ("score", "pvalue", "custom"),
            "requires_parameters": ("value", "operator"),
        },
        apply=_apply_threshold,
    ),
    "fraction": FilterDefinition(
        name="fraction",
        metadata={
            "name": "fraction",
            "display_name": "Retained Fraction Filter",
            "compatible_output_types": ("score", "pvalue", "custom"),
            "requires_parameters": ("fraction",),
            "direction_options": ("higher", "lower"),
            "default_direction": "method_preferred_direction",
            "tie_policies": tuple(sorted(TIE_POLICIES)),
            "default_tie_policy": "include_all_ties",
        },
        apply=_apply_fraction,
    ),
    "significance": FilterDefinition(
        name="significance",
        metadata={
            "name": "significance",
            "display_name": "Significance Filter",
            "compatible_output_types": ("pvalue",),
            "default_alpha": 0.05,
            "corrections": tuple(sorted(CORRECTIONS)),
        },
        apply=_apply_significance,
    ),
    "default": FilterDefinition(
        name="default",
        metadata={
            "name": "default",
            "display_name": "Method Default Filter",
            "compatible_output_types": ("score", "pvalue", "custom"),
        },
        apply=_apply_default,
    ),
}
