"""Temporal interaction aggregation tools."""

from netbone.temporal.aggregation import aggregate_temporal
from netbone.temporal.model import TemporalAggregationConfig, TemporalNetwork
from netbone.temporal.registry import (
    describe_temporal_weighting,
    list_temporal_weightings,
)

__all__ = [
    "TemporalAggregationConfig",
    "TemporalNetwork",
    "aggregate_temporal",
    "describe_temporal_weighting",
    "list_temporal_weightings",
]
