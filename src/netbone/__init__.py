"""Public API for Netbone."""

from netbone._version import __version__
from netbone.compare import Comparison, compare
from netbone.exceptions import (
    CompatibilityError,
    ConfigurationError,
    NetboneError,
    UndefinedMetricError,
    ValidationError,
)
from netbone.experiment import save_experiment
from netbone.filters.registry import describe_filter, list_filters
from netbone.io import from_edgelist, from_graphml, from_temporal_edgelist
from netbone.methods.registry import describe_method, list_methods
from netbone.metrics.registry import describe_metric, list_metrics
from netbone.network import Network, from_graph, to_undirected
from netbone.pipeline import Pipeline, filter_scores, pipeline, score
from netbone.report import Report, report
from netbone.results import BackboneResult, MethodResult, Selection
from netbone.sweep import Sweep, SweepResult, sweep
from netbone.temporal import (
    TemporalAggregationConfig,
    TemporalNetwork,
    aggregate_temporal,
    describe_temporal_weighting,
    list_temporal_weightings,
)

__all__ = [
    "BackboneResult",
    "CompatibilityError",
    "Comparison",
    "ConfigurationError",
    "MethodResult",
    "NetboneError",
    "Network",
    "Pipeline",
    "Report",
    "Selection",
    "Sweep",
    "SweepResult",
    "TemporalAggregationConfig",
    "TemporalNetwork",
    "UndefinedMetricError",
    "ValidationError",
    "__version__",
    "aggregate_temporal",
    "compare",
    "describe_filter",
    "describe_method",
    "describe_metric",
    "describe_temporal_weighting",
    "filter_scores",
    "from_edgelist",
    "from_graph",
    "from_graphml",
    "from_temporal_edgelist",
    "list_filters",
    "list_methods",
    "list_metrics",
    "list_temporal_weightings",
    "pipeline",
    "report",
    "score",
    "save_experiment",
    "sweep",
    "to_undirected",
]
