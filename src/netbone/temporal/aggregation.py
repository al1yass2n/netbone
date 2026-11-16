"""Aggregate temporal interaction events into weighted static networks."""

from __future__ import annotations

import math
import re
import warnings
from collections.abc import Hashable
from dataclasses import dataclass, field
from datetime import timedelta
from numbers import Real
from pathlib import Path

import networkx as nx
import pandas as pd

from netbone.exceptions import ConfigurationError, ValidationError
from netbone.network import Network, normalize_loaded_graph
from netbone.temporal.model import (
    TemporalAggregationConfig,
    TemporalNetwork,
    _serialized_value,
)
from netbone.temporal.registry import get_temporal_weighting


@dataclass(frozen=True)
class _ResolvedTiming:
    ages: tuple[float, ...]
    age_basis: str
    evaluation_time: object
    evaluation_snapshot: int | None
    time_unit: object | None
    snapshot_size: object | None
    snapshot_origin: object | None
    future_mask: tuple[bool, ...]


@dataclass
class _EdgeAccumulator:
    source: Hashable
    target: Hashable
    contributions: list[float] = field(default_factory=list)
    persistent_contributions: list[float] = field(default_factory=list)
    transient_contributions: list[float] = field(default_factory=list)
    event_weights: list[float] = field(default_factory=list)
    event_count: int = 0
    first_time: object | None = None
    last_time: object | None = None

    def add(
        self,
        *,
        time: object,
        event_weight: float,
        contribution: float,
        persistent_contribution: float | None = None,
        transient_contribution: float | None = None,
    ) -> None:
        self.contributions.append(contribution)
        if persistent_contribution is not None:
            self.persistent_contributions.append(persistent_contribution)
        if transient_contribution is not None:
            self.transient_contributions.append(transient_contribution)
        self.event_weights.append(event_weight)
        self.event_count += 1
        if self.first_time is None or _time_before(time, self.first_time):
            self.first_time = time
        if self.last_time is None or _time_before(self.last_time, time):
            self.last_time = time


def aggregate_temporal(
    temporal_network: TemporalNetwork,
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
    """Aggregate temporal events into a static weighted `Network`.

    Snapshot-based weightings use discrete snapshot ages. Persistent-memory
    weightings use exact elapsed ages without binning. No data-range
    normalization is applied.

    Args:
        temporal_network: Validated temporal interaction events.
        config: Optional saved aggregation configuration. When supplied, no
            additional aggregation options may be provided.
        weighting: Registered temporal weighting name. Defaults to `baseline`.
        evaluation_time: Evaluation timestamp or snapshot. Defaults to the
            latest observed event time.
        time_unit: Positive numeric scale for numeric elapsed times, or a
            duration such as `"1h"` or `"1d"` for datetime elapsed times.
        snapshot_size: Positive numeric bin size or datetime duration string.
        snapshot_origin: Optional explicit first snapshot boundary. Defaults to
            the earliest observed event time when binning raw timestamps.
        zero_weight_policy: `drop` or `keep` for zero aggregate edges.
        **parameters: Weighting-specific parameters.

    Returns:
        A standard weighted `Network` accepted by existing Netbone pipelines.

    Raises:
        ConfigurationError: If saved and inline configuration are mixed.
        ValidationError: If times, snapshot settings, or resulting weights are
            invalid.
    """

    if not isinstance(temporal_network, TemporalNetwork):
        raise ValidationError(
            "aggregate_temporal() requires a TemporalNetwork created by "
            "from_temporal_edgelist()."
        )
    resolved_config = _resolve_config(
        config,
        weighting=weighting,
        evaluation_time=evaluation_time,
        time_unit=time_unit,
        snapshot_size=snapshot_size,
        snapshot_origin=snapshot_origin,
        zero_weight_policy=zero_weight_policy,
        parameters=parameters,
    )
    definition = get_temporal_weighting(resolved_config.weighting)
    timing = _resolve_timing(
        temporal_network,
        resolved_config,
        age_basis=definition.age_basis,
    )

    accumulators: dict[object, _EdgeAccumulator] = {}
    future_event_count = 0
    included_event_count = 0
    for position, row in enumerate(
        temporal_network.events.itertuples(index=False, name=None)
    ):
        source, target, event_time, event_weight_value = row
        if timing.future_mask[position]:
            future_event_count += 1
            continue
        age = timing.ages[position]
        if not math.isfinite(age) or age < 0:
            raise ValidationError(
                "Temporal event age must be finite and non-negative after future "
                "events are excluded."
            )
        persistent_contribution: float | None = None
        transient_contribution: float | None = None
        if definition.components is None:
            relevance = float(definition.weight(age, resolved_config.parameters))
        else:
            persistent_relevance, transient_relevance = definition.components(
                age,
                resolved_config.parameters,
            )
            _validate_relevance_component(
                persistent_relevance,
                weighting=resolved_config.weighting,
                component="persistent",
            )
            _validate_relevance_component(
                transient_relevance,
                weighting=resolved_config.weighting,
                component="transient",
            )
            relevance = math.fsum((persistent_relevance, transient_relevance))
        if not math.isfinite(relevance) or relevance < 0.0:
            raise ValidationError(
                f"Temporal weighting {resolved_config.weighting!r} produced an "
                "invalid relevance value."
            )
        event_weight = float(event_weight_value)
        contribution = event_weight * relevance
        if definition.components is not None:
            persistent_contribution = event_weight * persistent_relevance
            transient_contribution = event_weight * transient_relevance
        if not math.isfinite(contribution) or contribution < 0.0:
            raise ValidationError(
                f"Temporal weighting {resolved_config.weighting!r} produced an "
                "invalid weighted event contribution."
            )
        key = (
            (source, target)
            if temporal_network.directed
            else frozenset((source, target))
        )
        accumulator = accumulators.get(key)
        if accumulator is None:
            accumulator = _EdgeAccumulator(source=source, target=target)
            accumulators[key] = accumulator
        accumulator.add(
            time=event_time,
            event_weight=event_weight,
            contribution=contribution,
            persistent_contribution=persistent_contribution,
            transient_contribution=transient_contribution,
        )
        included_event_count += 1

    if future_event_count:
        future_warning = (
            f"Ignored {future_event_count} temporal event(s) after the evaluation time."
        )
        warnings.warn(future_warning, UserWarning, stacklevel=2)

    graph = nx.DiGraph() if temporal_network.directed else nx.Graph()
    graph.add_nodes_from(temporal_network.nodes)
    zero_weight_edge_count = 0
    for accumulator in accumulators.values():
        aggregate_weight = math.fsum(accumulator.contributions)
        if aggregate_weight == 0.0:
            zero_weight_edge_count += 1
            if resolved_config.zero_weight_policy == "drop":
                continue
        attributes: dict[str, object] = {
            "weight": aggregate_weight,
            "temporal_event_count": accumulator.event_count,
            "temporal_event_weight_sum": math.fsum(accumulator.event_weights),
            "temporal_first_time": _serialized_value(accumulator.first_time),
            "temporal_last_time": _serialized_value(accumulator.last_time),
        }
        if definition.components is not None:
            attributes["temporal_persistent_contribution"] = math.fsum(
                accumulator.persistent_contributions
            )
            attributes["temporal_transient_contribution"] = math.fsum(
                accumulator.transient_contributions
            )
        graph.add_edge(accumulator.source, accumulator.target, **attributes)

    aggregation_warnings: list[str] = []
    self_interaction_value = temporal_network.metadata.get(
        "self_interaction_count",
        0,
    )
    self_interaction_count = (
        int(float(self_interaction_value))
        if isinstance(self_interaction_value, Real)
        and not isinstance(self_interaction_value, bool)
        else 0
    )
    if self_interaction_count:
        aggregation_warnings.append(
            f"Removed {self_interaction_count} temporal self-interaction(s)."
        )
    if future_event_count:
        aggregation_warnings.append(future_warning)
    if zero_weight_edge_count and resolved_config.zero_weight_policy == "drop":
        zero_warning = (
            f"Dropped {zero_weight_edge_count} temporal edge(s) with zero "
            "aggregate weight."
        )
        aggregation_warnings.append(zero_warning)
        warnings.warn(zero_warning, UserWarning, stacklevel=2)

    reproducible_config = TemporalAggregationConfig(
        weighting=resolved_config.weighting,
        parameters=resolved_config.parameters,
        evaluation_time=timing.evaluation_time,
        time_unit=timing.time_unit,
        snapshot_size=timing.snapshot_size,
        snapshot_origin=timing.snapshot_origin,
        zero_weight_policy=resolved_config.zero_weight_policy,
    ).to_dict()

    aggregation_metadata = {
        "config": reproducible_config,
        "weighting": resolved_config.weighting,
        "weighting_parameters": dict(resolved_config.parameters),
        "age_basis": timing.age_basis,
        "evaluation_time": _serialized_value(timing.evaluation_time),
        "evaluation_snapshot": timing.evaluation_snapshot,
        "time_unit": _serialized_value(timing.time_unit),
        "snapshot_size": _serialized_value(timing.snapshot_size),
        "snapshot_origin": _serialized_value(timing.snapshot_origin),
        "zero_weight_policy": resolved_config.zero_weight_policy,
        "directed": temporal_network.directed,
        "included_event_count": included_event_count,
        "future_event_count": future_event_count,
        "zero_weight_edge_count": zero_weight_edge_count,
        "retained_edge_count": graph.number_of_edges(),
    }
    metadata = {
        **dict(temporal_network.metadata),
        "format": "temporal_edgelist_aggregation",
        "canonical_weight_attribute": "weight",
        "netbone_warnings": aggregation_warnings,
        "temporal_aggregation": aggregation_metadata,
    }
    return normalize_loaded_graph(
        graph,
        context=temporal_network.context,
        source_path=Path(temporal_network.source),
        metadata=metadata,
    )


def _resolve_config(
    config: TemporalAggregationConfig | None,
    *,
    weighting: str | None,
    evaluation_time: object | None,
    time_unit: object | None,
    snapshot_size: object | None,
    snapshot_origin: object | None,
    zero_weight_policy: str | None,
    parameters: dict[str, object],
) -> TemporalAggregationConfig:
    if config is not None:
        if not isinstance(config, TemporalAggregationConfig):
            raise ConfigurationError(
                "aggregate_temporal() config must be a TemporalAggregationConfig."
            )
        if (
            any(
                value is not None
                for value in (
                    weighting,
                    evaluation_time,
                    time_unit,
                    snapshot_size,
                    snapshot_origin,
                    zero_weight_policy,
                )
            )
            or parameters
        ):
            raise ConfigurationError(
                "aggregate_temporal() cannot combine a saved config with inline "
                "aggregation options."
            )
        return config
    return TemporalAggregationConfig(
        weighting=weighting or "baseline",
        parameters=parameters,
        evaluation_time=evaluation_time,
        time_unit=time_unit,
        snapshot_size=snapshot_size,
        snapshot_origin=snapshot_origin,
        zero_weight_policy=zero_weight_policy or "drop",
    )


def _resolve_timing(
    temporal_network: TemporalNetwork,
    config: TemporalAggregationConfig,
    *,
    age_basis: str,
) -> _ResolvedTiming:
    if age_basis == "elapsed":
        if temporal_network.time_kind == "numeric":
            return _resolve_numeric_elapsed_timing(temporal_network, config)
        return _resolve_datetime_elapsed_timing(temporal_network, config)
    if temporal_network.time_kind == "numeric":
        return _resolve_numeric_timing(temporal_network, config)
    return _resolve_datetime_timing(temporal_network, config)


def _resolve_numeric_timing(
    temporal_network: TemporalNetwork,
    config: TemporalAggregationConfig,
) -> _ResolvedTiming:
    times = tuple(
        _finite_numeric(value, name="temporal event time")
        for value in temporal_network.events["time"]
    )
    observed_start = _finite_numeric(
        temporal_network.observed_start,
        name="observed start time",
    )
    observed_end = _finite_numeric(
        temporal_network.observed_end,
        name="observed end time",
    )
    evaluation_time = (
        observed_end
        if config.evaluation_time is None
        else _finite_numeric(config.evaluation_time, name="evaluation_time")
    )
    future_mask = tuple(value > evaluation_time for value in times)

    if config.snapshot_size is None:
        if config.snapshot_origin is not None:
            raise ConfigurationError(
                "snapshot_origin requires snapshot_size for numeric temporal data."
            )
        snapshots = tuple(
            _snapshot_integer(value, name="event time") for value in times
        )
        evaluation_snapshot = _snapshot_integer(
            evaluation_time,
            name="evaluation_time",
        )
        return _ResolvedTiming(
            ages=tuple(float(evaluation_snapshot - value) for value in snapshots),
            age_basis="snapshot",
            evaluation_time=_compact_number(evaluation_time),
            evaluation_snapshot=evaluation_snapshot,
            time_unit=None,
            snapshot_size=None,
            snapshot_origin=None,
            future_mask=future_mask,
        )

    snapshot_size = _finite_numeric(config.snapshot_size, name="snapshot_size")
    if snapshot_size <= 0.0:
        raise ValidationError("Numeric snapshot_size must be positive.")
    snapshot_origin = (
        observed_start
        if config.snapshot_origin is None
        else _finite_numeric(config.snapshot_origin, name="snapshot_origin")
    )
    snapshots = tuple(
        math.floor((value - snapshot_origin) / snapshot_size) for value in times
    )
    evaluation_snapshot = math.floor(
        (evaluation_time - snapshot_origin) / snapshot_size
    )
    return _ResolvedTiming(
        ages=tuple(float(evaluation_snapshot - value) for value in snapshots),
        age_basis="snapshot",
        evaluation_time=_compact_number(evaluation_time),
        evaluation_snapshot=evaluation_snapshot,
        time_unit=None,
        snapshot_size=_compact_number(snapshot_size),
        snapshot_origin=_compact_number(snapshot_origin),
        future_mask=future_mask,
    )


def _resolve_datetime_timing(
    temporal_network: TemporalNetwork,
    config: TemporalAggregationConfig,
) -> _ResolvedTiming:
    times = tuple(
        _timestamp(value, name="temporal event time")
        for value in temporal_network.events["time"]
    )
    observed_start = _timestamp(
        temporal_network.observed_start,
        name="observed start time",
    )
    observed_end = _timestamp(
        temporal_network.observed_end,
        name="observed end time",
    )
    evaluation_time = (
        observed_end
        if config.evaluation_time is None
        else _timestamp(config.evaluation_time, name="evaluation_time")
    )
    if config.snapshot_size is None:
        raise ConfigurationError(
            "Datetime temporal data requires an explicit snapshot_size such as "
            "'40s', '5min', or '1h'."
        )
    snapshot_size = _duration(config.snapshot_size, name="snapshot_size")
    snapshot_origin = (
        observed_start
        if config.snapshot_origin is None
        else _timestamp(config.snapshot_origin, name="snapshot_origin")
    )
    snapshots = tuple(
        math.floor((value - snapshot_origin) / snapshot_size) for value in times
    )
    evaluation_snapshot = math.floor(
        (evaluation_time - snapshot_origin) / snapshot_size
    )
    return _ResolvedTiming(
        ages=tuple(float(evaluation_snapshot - value) for value in snapshots),
        age_basis="snapshot",
        evaluation_time=evaluation_time,
        evaluation_snapshot=evaluation_snapshot,
        time_unit=None,
        snapshot_size=snapshot_size,
        snapshot_origin=snapshot_origin,
        future_mask=tuple(value > evaluation_time for value in times),
    )


def _resolve_numeric_elapsed_timing(
    temporal_network: TemporalNetwork,
    config: TemporalAggregationConfig,
) -> _ResolvedTiming:
    times = tuple(
        _finite_numeric(value, name="temporal event time")
        for value in temporal_network.events["time"]
    )
    observed_end = _finite_numeric(
        temporal_network.observed_end,
        name="observed end time",
    )
    evaluation_time = (
        observed_end
        if config.evaluation_time is None
        else _finite_numeric(config.evaluation_time, name="evaluation_time")
    )
    unit = (
        1.0
        if config.time_unit is None
        else _finite_numeric(config.time_unit, name="time_unit")
    )
    if unit <= 0.0:
        raise ValidationError("Numeric time_unit must be positive.")
    return _ResolvedTiming(
        ages=tuple((evaluation_time - value) / unit for value in times),
        age_basis="elapsed",
        evaluation_time=_compact_number(evaluation_time),
        evaluation_snapshot=None,
        time_unit=(None if config.time_unit is None else _compact_number(unit)),
        snapshot_size=None,
        snapshot_origin=None,
        future_mask=tuple(value > evaluation_time for value in times),
    )


def _resolve_datetime_elapsed_timing(
    temporal_network: TemporalNetwork,
    config: TemporalAggregationConfig,
) -> _ResolvedTiming:
    times = tuple(
        _timestamp(value, name="temporal event time")
        for value in temporal_network.events["time"]
    )
    observed_end = _timestamp(
        temporal_network.observed_end,
        name="observed end time",
    )
    evaluation_time = (
        observed_end
        if config.evaluation_time is None
        else _timestamp(config.evaluation_time, name="evaluation_time")
    )
    if config.time_unit is None:
        raise ConfigurationError(
            "Persistent temporal weighting of datetime events requires an explicit "
            "time_unit such as '1h' or '1d'."
        )
    time_unit = _duration(config.time_unit, name="time_unit")
    return _ResolvedTiming(
        ages=tuple(float((evaluation_time - value) / time_unit) for value in times),
        age_basis="elapsed",
        evaluation_time=evaluation_time,
        evaluation_snapshot=None,
        time_unit=time_unit,
        snapshot_size=None,
        snapshot_origin=None,
        future_mask=tuple(value > evaluation_time for value in times),
    )


def _finite_numeric(value: object, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValidationError(f"Temporal {name} must be numeric.")
    result = float(value)
    if not math.isfinite(result):
        raise ValidationError(f"Temporal {name} must be finite.")
    return result


def _snapshot_integer(value: float, *, name: str) -> int:
    if not value.is_integer():
        raise ValidationError(
            f"Numeric temporal {name} must be an integer snapshot id when "
            "snapshot_size is omitted."
        )
    return int(value)


def _timestamp(value: object, *, name: str) -> pd.Timestamp:
    try:
        parsed = pd.to_datetime(value, errors="raise", utc=True)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValidationError(f"Temporal {name} must be a valid datetime.") from exc
    if not isinstance(parsed, pd.Timestamp):
        raise ValidationError(f"Temporal {name} must be a scalar datetime.")
    return parsed


def _duration(value: object, *, name: str) -> pd.Timedelta:
    if isinstance(value, bool | Real):
        raise ValidationError(
            f"Datetime {name} must include a unit, such as '40s' or '5min'."
        )
    try:
        duration_value = _normalized_duration_value(value)
        duration = pd.Timedelta(duration_value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValidationError(
            f"Datetime {name} must be a valid positive duration."
        ) from exc
    if duration <= pd.Timedelta(0):
        raise ValidationError(f"Datetime {name} must be positive.")
    return duration


def _normalized_duration_value(value: object) -> object:
    if isinstance(value, timedelta):
        return value
    if not isinstance(value, str):
        return value
    day_match = re.fullmatch(
        r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*d\s*",
        value,
        flags=re.IGNORECASE,
    )
    return f"{day_match.group(1)}D" if day_match else value


def _validate_relevance_component(
    value: float,
    *,
    weighting: str,
    component: str,
) -> None:
    if not math.isfinite(value) or value < 0.0:
        raise ValidationError(
            f"Temporal weighting {weighting!r} produced an invalid {component} "
            "relevance component."
        )


def _compact_number(value: float) -> int | float:
    return int(value) if value.is_integer() else value


def _time_before(left: object, right: object) -> bool:
    if isinstance(left, pd.Timestamp) and isinstance(right, pd.Timestamp):
        return bool(left < right)
    if (
        isinstance(left, Real)
        and not isinstance(left, bool)
        and isinstance(right, Real)
        and not isinstance(right, bool)
    ):
        return float(left) < float(right)
    raise ValidationError("Temporal event times must use one consistent type.")
