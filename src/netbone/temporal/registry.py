"""Registry for deterministic temporal weighting functions."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from numbers import Real
from types import MappingProxyType

from netbone._references import Paper, reference_metadata
from netbone.exceptions import ConfigurationError, ValidationError

TemporalWeight = Callable[[float, Mapping[str, object]], float]
TemporalComponents = Callable[
    [float, Mapping[str, object]],
    tuple[float, float],
]
ParameterResolver = Callable[[Mapping[str, object]], dict[str, object]]


@dataclass(frozen=True)
class TemporalWeightingDefinition:
    """Registered temporal weighting metadata and execution hooks."""

    name: str
    metadata: Mapping[str, object]
    age_basis: str
    resolve_parameters: ParameterResolver
    weight: TemporalWeight
    components: TemporalComponents | None = None

    def __post_init__(self) -> None:
        """Freeze metadata for registry callers."""

        if self.age_basis not in {"snapshot", "elapsed"}:
            raise ValueError(
                "Temporal weighting age_basis must be snapshot or elapsed."
            )
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


def list_temporal_weightings() -> tuple[str, ...]:
    """Return registered temporal weighting names."""

    return tuple(sorted(_WEIGHTINGS))


def describe_temporal_weighting(name: str) -> dict[str, object]:
    """Return JSON-compatible metadata for a temporal weighting.

    The metadata names the formula, the parameters, and the source paper in
    ``reference``, ``doi``, and ``references``, as method metadata does.
    """

    return dict(get_temporal_weighting(name).metadata)


def get_temporal_weighting(name: str) -> TemporalWeightingDefinition:
    """Return one registered temporal weighting definition.

    Raises:
        ConfigurationError: If the weighting name is unknown.
    """

    try:
        return _WEIGHTINGS[name]
    except KeyError as exc:
        allowed = ", ".join(list_temporal_weightings())
        raise ConfigurationError(
            f"Unknown temporal weighting {name!r}. Available weightings: {allowed}."
        ) from exc


def _baseline_parameters(parameters: Mapping[str, object]) -> dict[str, object]:
    _reject_unknown_parameters("baseline", parameters, set())
    return {}


def _asf_parameters(parameters: Mapping[str, object]) -> dict[str, object]:
    _reject_unknown_parameters("asf", parameters, {"a", "p", "q"})
    p = _finite_real(parameters.get("p", 3.0), name="p", weighting="asf")
    q = _finite_real(parameters.get("q", 0.0), name="q", weighting="asf")
    a = _finite_real(parameters.get("a", 5.0), name="a", weighting="asf")
    if p <= 0.0:
        raise ValidationError(
            "Temporal weighting 'asf' parameter 'p' must be positive."
        )
    if q < 0.0:
        raise ValidationError(
            "Temporal weighting 'asf' parameter 'q' must be non-negative."
        )
    return {"p": p, "q": q, "a": a}


def _persistent_exponential_parameters(
    parameters: Mapping[str, object],
) -> dict[str, object]:
    weighting = "persistent_exponential"
    _require_parameters(
        weighting,
        parameters,
        {"persistent_level", "decay_rate"},
    )
    persistent_level = _persistent_level(parameters, weighting=weighting)
    decay_rate = _finite_real(
        parameters["decay_rate"],
        name="decay_rate",
        weighting=weighting,
    )
    if decay_rate < 0.0:
        raise ValidationError(
            f"Temporal weighting {weighting!r} parameter 'decay_rate' must be "
            "non-negative."
        )
    return {
        "persistent_level": persistent_level,
        "decay_rate": decay_rate,
    }


def _persistent_weibull_parameters(
    parameters: Mapping[str, object],
) -> dict[str, object]:
    return _persistent_scale_shape_parameters(
        "persistent_weibull",
        parameters,
    )


def _persistent_log_logistic_parameters(
    parameters: Mapping[str, object],
) -> dict[str, object]:
    return _persistent_scale_shape_parameters(
        "persistent_log_logistic",
        parameters,
    )


def _baseline_weight(age: float, parameters: Mapping[str, object]) -> float:
    del age, parameters
    return 1.0


def _asf_weight(age: float, parameters: Mapping[str, object]) -> float:
    p = _resolved_float(parameters, "p", weighting="asf")
    q = _resolved_float(parameters, "q", weighting="asf")
    a = _resolved_float(parameters, "a", weighting="asf")
    exponent = age / p - a
    if exponent >= 0.0:
        decay = math.exp(-exponent)
        sigmoid = decay / (1.0 + decay)
    else:
        sigmoid = 1.0 / (1.0 + math.exp(exponent))
    return (sigmoid + q) / (q + 1.0)


def _persistent_exponential_components(
    age: float,
    parameters: Mapping[str, object],
) -> tuple[float, float]:
    weighting = "persistent_exponential"
    persistent_level = _resolved_float(
        parameters,
        "persistent_level",
        weighting=weighting,
    )
    decay_rate = _resolved_float(parameters, "decay_rate", weighting=weighting)
    transient_kernel = math.exp(-decay_rate * age)
    return persistent_level, (1.0 - persistent_level) * transient_kernel


def _persistent_weibull_components(
    age: float,
    parameters: Mapping[str, object],
) -> tuple[float, float]:
    weighting = "persistent_weibull"
    persistent_level = _resolved_float(
        parameters,
        "persistent_level",
        weighting=weighting,
    )
    scale = _resolved_float(parameters, "scale", weighting=weighting)
    shape = _resolved_float(parameters, "shape", weighting=weighting)
    powered_age = _scaled_power(age, scale=scale, shape=shape)
    transient_kernel = math.exp(-powered_age)
    return persistent_level, (1.0 - persistent_level) * transient_kernel


def _persistent_log_logistic_components(
    age: float,
    parameters: Mapping[str, object],
) -> tuple[float, float]:
    weighting = "persistent_log_logistic"
    persistent_level = _resolved_float(
        parameters,
        "persistent_level",
        weighting=weighting,
    )
    scale = _resolved_float(parameters, "scale", weighting=weighting)
    shape = _resolved_float(parameters, "shape", weighting=weighting)
    powered_age = _scaled_power(age, scale=scale, shape=shape)
    transient_kernel = 0.0 if math.isinf(powered_age) else 1.0 / (1.0 + powered_age)
    return persistent_level, (1.0 - persistent_level) * transient_kernel


def _components_weight(
    components: TemporalComponents,
) -> TemporalWeight:
    def weight(age: float, parameters: Mapping[str, object]) -> float:
        persistent, transient = components(age, parameters)
        return persistent + transient

    return weight


def _persistent_level(
    parameters: Mapping[str, object],
    *,
    weighting: str,
) -> float:
    value = _finite_real(
        parameters["persistent_level"],
        name="persistent_level",
        weighting=weighting,
    )
    if not 0.0 <= value <= 1.0:
        raise ValidationError(
            f"Temporal weighting {weighting!r} parameter 'persistent_level' "
            "must be between 0 and 1 inclusive."
        )
    return value


def _persistent_scale_shape_parameters(
    weighting: str,
    parameters: Mapping[str, object],
) -> dict[str, object]:
    _require_parameters(
        weighting,
        parameters,
        {"persistent_level", "scale", "shape"},
    )
    persistent_level = _persistent_level(parameters, weighting=weighting)
    scale = _finite_real(parameters["scale"], name="scale", weighting=weighting)
    shape = _finite_real(parameters["shape"], name="shape", weighting=weighting)
    if scale <= 0.0:
        raise ValidationError(
            f"Temporal weighting {weighting!r} parameter 'scale' must be positive."
        )
    if shape <= 0.0:
        raise ValidationError(
            f"Temporal weighting {weighting!r} parameter 'shape' must be positive."
        )
    return {
        "persistent_level": persistent_level,
        "scale": scale,
        "shape": shape,
    }


def _scaled_power(age: float, *, scale: float, shape: float) -> float:
    if age == 0.0:
        return 0.0
    try:
        return (age / scale) ** shape
    except OverflowError:
        return math.inf


def _require_parameters(
    weighting: str,
    parameters: Mapping[str, object],
    required: set[str],
) -> None:
    _reject_unknown_parameters(weighting, parameters, required)
    missing = required.difference(parameters)
    if missing:
        names = ", ".join(sorted(missing))
        raise ConfigurationError(
            f"Temporal weighting {weighting!r} requires parameter(s): {names}."
        )


def _reject_unknown_parameters(
    weighting: str,
    parameters: Mapping[str, object],
    allowed: set[str],
) -> None:
    unknown = set(parameters).difference(allowed)
    if unknown:
        names = ", ".join(sorted(str(name) for name in unknown))
        raise ConfigurationError(
            f"Temporal weighting {weighting!r} does not accept parameter(s): {names}."
        )


def _finite_real(value: object, *, name: str, weighting: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValidationError(
            f"Temporal weighting {weighting!r} parameter {name!r} must be numeric."
        )
    result = float(value)
    if not math.isfinite(result):
        raise ValidationError(
            f"Temporal weighting {weighting!r} parameter {name!r} must be finite."
        )
    return result


def _resolved_float(
    parameters: Mapping[str, object],
    name: str,
    *,
    weighting: str,
) -> float:
    return _finite_real(parameters[name], name=name, weighting=weighting)


_FRAMEWORK_PAPER = Paper(
    authors=(
        ("Yassin", "A."),
        ("Cherifi", "H."),
        ("Seba", "H."),
        ("Togni", "O."),
    ),
    year=2026,
    title=(
        "A framework for backbone extraction from temporal networks: "
        "An ASF-based case study"
    ),
    booktitle="2026 IEEE Workshop on Complexity in Engineering (COMPENG)",
    publisher="IEEE",
    doi="10.1109/COMPENG69955.2026.11766128",
)
_BASELINE_NOTE = (
    "The baseline sums event magnitudes without temporal decay, so it has no "
    "single source paper."
)

_WEIGHTINGS = {
    "baseline": TemporalWeightingDefinition(
        name="baseline",
        metadata={
            "name": "baseline",
            "description": "Aggregate event magnitudes without temporal decay.",
            "formula": "phi(x) = 1",
            "uses_age": False,
            "age_basis": "snapshot",
            "default_parameters": {},
            "required_parameters": (),
            "parameters": {},
            **reference_metadata((), _BASELINE_NOTE),
        },
        age_basis="snapshot",
        resolve_parameters=_baseline_parameters,
        weight=_baseline_weight,
    ),
    "asf": TemporalWeightingDefinition(
        name="asf",
        metadata={
            "name": "asf",
            "description": "Adaptive sigmoid temporal relevance weighting.",
            "formula": "phi(x) = (1 / (1 + exp(x / p - a)) + q) / (q + 1)",
            "uses_age": True,
            "age_basis": "snapshot",
            "default_parameters": {"p": 3.0, "q": 0.0, "a": 5.0},
            "required_parameters": (),
            "parameters": {
                "p": "positive number",
                "q": "non-negative number",
                "a": "finite number",
            },
            **reference_metadata((_FRAMEWORK_PAPER,)),
        },
        age_basis="snapshot",
        resolve_parameters=_asf_parameters,
        weight=_asf_weight,
    ),
    "persistent_exponential": TemporalWeightingDefinition(
        name="persistent_exponential",
        metadata={
            "name": "persistent_exponential",
            "description": (
                "Persistent memory with constant proportional transient forgetting."
            ),
            "formula": (
                "phi(tau) = persistent_level + (1 - persistent_level) * "
                "exp(-decay_rate * tau)"
            ),
            "uses_age": True,
            "age_basis": "elapsed",
            "default_parameters": {},
            "required_parameters": ("persistent_level", "decay_rate"),
            "parameters": {
                "persistent_level": "number from 0 to 1 inclusive",
                "decay_rate": "non-negative number",
            },
            **reference_metadata((_FRAMEWORK_PAPER,)),
        },
        age_basis="elapsed",
        resolve_parameters=_persistent_exponential_parameters,
        weight=_components_weight(_persistent_exponential_components),
        components=_persistent_exponential_components,
    ),
    "persistent_weibull": TemporalWeightingDefinition(
        name="persistent_weibull",
        metadata={
            "name": "persistent_weibull",
            "description": (
                "Persistent memory with independently controlled transient scale "
                "and shape."
            ),
            "formula": (
                "phi(tau) = persistent_level + (1 - persistent_level) * "
                "exp(-(tau / scale) ** shape)"
            ),
            "uses_age": True,
            "age_basis": "elapsed",
            "default_parameters": {},
            "required_parameters": ("persistent_level", "scale", "shape"),
            "parameters": {
                "persistent_level": "number from 0 to 1 inclusive",
                "scale": "positive number in elapsed-time units",
                "shape": "positive number",
            },
            **reference_metadata((_FRAMEWORK_PAPER,)),
        },
        age_basis="elapsed",
        resolve_parameters=_persistent_weibull_parameters,
        weight=_components_weight(_persistent_weibull_components),
        components=_persistent_weibull_components,
    ),
    "persistent_log_logistic": TemporalWeightingDefinition(
        name="persistent_log_logistic",
        metadata={
            "name": "persistent_log_logistic",
            "description": (
                "Persistent memory with a smooth transition and a polynomial "
                "transient tail."
            ),
            "formula": (
                "phi(tau) = persistent_level + (1 - persistent_level) / "
                "(1 + (tau / scale) ** shape)"
            ),
            "uses_age": True,
            "age_basis": "elapsed",
            "default_parameters": {},
            "required_parameters": ("persistent_level", "scale", "shape"),
            "parameters": {
                "persistent_level": "number from 0 to 1 inclusive",
                "scale": "positive number in elapsed-time units",
                "shape": "positive number",
            },
            **reference_metadata((_FRAMEWORK_PAPER,)),
        },
        age_basis="elapsed",
        resolve_parameters=_persistent_log_logistic_parameters,
        weight=_components_weight(_persistent_log_logistic_components),
        components=_persistent_log_logistic_components,
    ),
}
