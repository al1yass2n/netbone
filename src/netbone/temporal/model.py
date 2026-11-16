"""Temporal event and aggregation configuration models."""

from __future__ import annotations

import json
import math
from collections.abc import Hashable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from numbers import Real
from pathlib import Path
from types import MappingProxyType

import pandas as pd

from netbone._version import __version__
from netbone.exceptions import ConfigurationError, ValidationError
from netbone.network import Network
from netbone.temporal.registry import get_temporal_weighting

TEMPORAL_AGGREGATION_SCHEMA_VERSION = "1.1"
VALID_TIME_KINDS = frozenset({"numeric", "datetime"})
VALID_ZERO_WEIGHT_POLICIES = frozenset({"drop", "keep"})
EVENT_COLUMNS = ("source", "target", "time", "event_weight")


@dataclass(frozen=True)
class TemporalNetwork:
    """Validated temporal interaction events awaiting weighted aggregation."""

    events: pd.DataFrame
    nodes: tuple[Hashable, ...]
    directed: bool
    time_kind: str
    observed_start: object
    observed_end: object
    context: str | None
    source: str
    metadata: Mapping[str, object]

    def __post_init__(self) -> None:
        """Validate and freeze temporal input metadata."""

        missing = set(EVENT_COLUMNS).difference(self.events.columns)
        if missing:
            names = ", ".join(sorted(missing))
            raise ValidationError(
                f"TemporalNetwork events are missing required column(s): {names}."
            )
        if self.time_kind not in VALID_TIME_KINDS:
            raise ValidationError(
                f"TemporalNetwork time_kind must be one of {sorted(VALID_TIME_KINDS)}."
            )
        if not isinstance(self.directed, bool):
            raise ValidationError("TemporalNetwork directed must be a boolean.")
        object.__setattr__(self, "events", self.events.loc[:, EVENT_COLUMNS].copy())
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def event_count(self) -> int:
        """Return the number of retained non-self interaction events."""

        return len(self.events)

    @property
    def node_count(self) -> int:
        """Return the number of distinct nodes observed in the event input."""

        return len(self.nodes)

    def summary(self) -> dict[str, object]:
        """Return a JSON-compatible temporal input summary."""

        return {
            "node_count": self.node_count,
            "event_count": self.event_count,
            "directed": self.directed,
            "time_kind": self.time_kind,
            "observed_start": _serialized_value(self.observed_start),
            "observed_end": _serialized_value(self.observed_end),
            "source": self.source,
            "metadata": dict(self.metadata),
            "has_context": self.context is not None,
        }

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible temporal input summary."""

        return self.summary()

    def aggregate(
        self,
        config: TemporalAggregationConfig | None = None,
        *,
        weighting: str | None = None,
        evaluation_time: object | None = None,
        time_unit: object | None = None,
        snapshot_size: object | None = None,
        snapshot_origin: object | None = None,
        zero_weight_policy: str | None = None,
        **parameters: object,
    ) -> Network:
        """Aggregate temporal events into a standard weighted `Network`."""

        from netbone.temporal.aggregation import aggregate_temporal

        return aggregate_temporal(
            self,
            config=config,
            weighting=weighting,
            evaluation_time=evaluation_time,
            time_unit=time_unit,
            snapshot_size=snapshot_size,
            snapshot_origin=snapshot_origin,
            zero_weight_policy=zero_weight_policy,
            **parameters,
        )


@dataclass(frozen=True)
class TemporalAggregationConfig:
    """Serializable configuration for temporal edge-weight aggregation."""

    weighting: str = "baseline"
    parameters: Mapping[str, object] = field(default_factory=dict)
    evaluation_time: object | None = None
    snapshot_size: object | None = None
    snapshot_origin: object | None = None
    zero_weight_policy: str = "drop"
    time_unit: object | None = None

    def __post_init__(self) -> None:
        """Resolve defaults and freeze weighting parameters."""

        if not isinstance(self.weighting, str) or not self.weighting:
            raise ConfigurationError(
                "Temporal aggregation weighting must be a non-empty string."
            )
        definition = get_temporal_weighting(self.weighting)
        resolved = definition.resolve_parameters(self.parameters)
        if self.zero_weight_policy not in VALID_ZERO_WEIGHT_POLICIES:
            allowed = ", ".join(sorted(VALID_ZERO_WEIGHT_POLICIES))
            raise ConfigurationError(
                f"Temporal aggregation zero_weight_policy must be one of: {allowed}."
            )
        _validate_config_value(self.evaluation_time, name="evaluation_time")
        _validate_config_value(self.time_unit, name="time_unit")
        _validate_config_value(self.snapshot_size, name="snapshot_size")
        _validate_config_value(self.snapshot_origin, name="snapshot_origin")
        if definition.age_basis == "elapsed" and (
            self.snapshot_size is not None or self.snapshot_origin is not None
        ):
            raise ConfigurationError(
                f"Temporal weighting {self.weighting!r} uses exact elapsed time; "
                "snapshot_size and snapshot_origin are not applicable. Use "
                "time_unit to scale elapsed ages."
            )
        if definition.age_basis == "snapshot" and self.time_unit is not None:
            raise ConfigurationError(
                f"Temporal weighting {self.weighting!r} uses snapshot age and does "
                "not accept time_unit. Use snapshot_size instead."
            )
        object.__setattr__(self, "parameters", MappingProxyType(resolved))

    @classmethod
    def from_dict(cls, config: Mapping[str, object]) -> TemporalAggregationConfig:
        """Restore a configuration produced by `to_dict()`."""

        if not isinstance(config, Mapping):
            raise ConfigurationError(
                "TemporalAggregationConfig.from_dict() requires a mapping."
            )
        weighting_config = config.get("weighting")
        if not isinstance(weighting_config, Mapping):
            raise ConfigurationError(
                "Temporal aggregation config requires a 'weighting' mapping."
            )
        weighting = weighting_config.get("name")
        if not isinstance(weighting, str) or not weighting:
            raise ConfigurationError(
                "Temporal aggregation weighting requires a non-empty string 'name'."
            )
        parameters = weighting_config.get("parameters", {})
        if not isinstance(parameters, Mapping):
            raise ConfigurationError(
                "Temporal aggregation weighting parameters must be a mapping."
            )
        timing = config.get("timing", {})
        if not isinstance(timing, Mapping):
            raise ConfigurationError(
                "Temporal aggregation config 'timing' must be a mapping."
            )
        zero_weight_policy = config.get("zero_weight_policy", "drop")
        if not isinstance(zero_weight_policy, str):
            raise ConfigurationError(
                "Temporal aggregation zero_weight_policy must be a string."
            )
        return cls(
            weighting=weighting,
            parameters=dict(parameters),
            evaluation_time=timing.get("evaluation_time"),
            time_unit=timing.get("time_unit"),
            snapshot_size=timing.get("snapshot_size"),
            snapshot_origin=timing.get("snapshot_origin"),
            zero_weight_policy=zero_weight_policy,
        )

    @classmethod
    def from_json(cls, path: str | Path) -> TemporalAggregationConfig:
        """Restore a temporal aggregation configuration from JSON."""

        config_path = Path(path)
        try:
            raw_config = config_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ValidationError(
                f"Temporal aggregation config file does not exist: {config_path}."
            ) from exc
        except OSError as exc:
            raise ValidationError(
                f"Temporal aggregation config file could not be read: {config_path}."
            ) from exc
        try:
            config = json.loads(raw_config)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                f"Temporal aggregation config file is not valid JSON: {config_path}."
            ) from exc
        if not isinstance(config, Mapping):
            raise ConfigurationError(
                "Temporal aggregation config JSON must contain an object."
            )
        return cls.from_dict(config)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible aggregation configuration."""

        return {
            "schema_version": TEMPORAL_AGGREGATION_SCHEMA_VERSION,
            "package": {"name": "netbone", "version": __version__},
            "weighting": {
                "name": self.weighting,
                "parameters": dict(self.parameters),
            },
            "timing": {
                "evaluation_time": _serialized_value(self.evaluation_time),
                "time_unit": _serialized_value(self.time_unit),
                "snapshot_size": _serialized_value(self.snapshot_size),
                "snapshot_origin": _serialized_value(self.snapshot_origin),
            },
            "zero_weight_policy": self.zero_weight_policy,
        }

    def to_json(self, path: str | Path, *, indent: int | None = 2) -> None:
        """Write this temporal aggregation configuration to JSON."""

        config_path = Path(path)
        try:
            serialized = (
                json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"
            )
        except TypeError as exc:
            raise ConfigurationError(
                "Temporal aggregation configuration contains a value that cannot "
                "be serialized to JSON."
            ) from exc
        try:
            config_path.write_text(serialized, encoding="utf-8")
        except OSError as exc:
            raise ValidationError(
                f"Temporal aggregation config file could not be written: {config_path}."
            ) from exc


def _validate_config_value(value: object | None, *, name: str) -> None:
    if value is None or isinstance(
        value,
        str | datetime | timedelta | pd.Timestamp | pd.Timedelta,
    ):
        return
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ConfigurationError(
            f"Temporal aggregation {name} must be numeric, datetime-like, or None."
        )
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValidationError(f"Temporal aggregation {name} must be finite.")
    if name in {"snapshot_size", "time_unit"} and numeric <= 0.0:
        raise ValidationError(f"Temporal aggregation {name} must be positive.")


def _serialized_value(value: object | None) -> object | None:
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, timedelta):
        return pd.Timedelta(value).isoformat()
    if isinstance(value, Real) and not isinstance(value, bool):
        numeric = float(value)
        return int(numeric) if numeric.is_integer() else numeric
    return value
