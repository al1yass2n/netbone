"""Parameter sweep coordination for pipeline configurations."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from itertools import product
from types import MappingProxyType

import networkx as nx
import pandas as pd

from netbone._json import json_records
from netbone.compare import compare
from netbone.compare.comparison import DEFAULT_SINGLE_METRICS
from netbone.exceptions import ConfigurationError
from netbone.metrics.registry import get_metric
from netbone.network import Network, ensure_network
from netbone.pipeline import Pipeline, filter_scores, pipeline
from netbone.results import BackboneResult, MethodResult, Selection

FilterCallable = Callable[..., Selection]
MethodCacheKey = tuple[int, str, tuple[tuple[str, object], ...]]

_METRIC_TABLE_COLUMNS = [
    "run_id",
    "pipeline_name",
    "method",
    "method_parameters",
    "filter",
    "filter_parameters",
    "varied_parameter",
    "parameter_value",
    "varied_parameters",
    "metric",
    "value",
    "status",
    "explanation",
    "warning",
    "failure_detail",
    "score_cache_key",
    "score_cache_hit",
]
_RUN_TABLE_COLUMNS = [
    "run_id",
    "pipeline_name",
    "method",
    "method_parameters",
    "filter",
    "filter_parameters",
    "varied_parameter",
    "parameter_value",
    "varied_parameters",
    "status",
    "explanation",
    "warning",
    "failure_detail",
    "score_cache_key",
    "score_cache_hit",
]


@dataclass(frozen=True)
class SweepResult:
    """Results from executing a parameter sweep.

    Successful configurations are available in `results`. Failed
    configurations are preserved in `runs`, `failures`, and `table()` rows
    instead of aborting the whole sweep.
    """

    results: Mapping[str, BackboneResult]
    _table: pd.DataFrame
    _runs: pd.DataFrame
    score_cache_hits: int
    score_cache_misses: int

    def __post_init__(self) -> None:
        """Freeze result mappings."""

        object.__setattr__(self, "results", MappingProxyType(dict(self.results)))

    def table(self) -> pd.DataFrame:
        """Return tidy metric rows for successful and failed configurations."""

        return self._table.copy()

    @property
    def runs(self) -> pd.DataFrame:
        """Return one tidy status row per sweep configuration."""

        return self._runs.copy()

    @property
    def failures(self) -> pd.DataFrame:
        """Return run rows for configurations that failed."""

        runs = self.runs
        return runs[runs["status"] == "failed"].copy()

    @property
    def plot_data(self) -> dict[str, pd.DataFrame]:
        """Return plot-ready sweep tables without requiring plotting packages."""

        return {
            "sweep_metrics": self.table(),
            "sweep_runs": self.runs,
        }

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible summary of the sweep result."""

        return {
            "results": list(self.results),
            "score_cache_hits": self.score_cache_hits,
            "score_cache_misses": self.score_cache_misses,
            "runs": json_records(self.runs),
            "table": json_records(self.table()),
        }


@dataclass(frozen=True)
class Sweep:
    """Immutable builder for parameter sweeps over pipelines."""

    network: Network
    base_pipeline: Pipeline = field(default_factory=Pipeline)
    _pipelines: Mapping[str, _SweepPipeline] = field(default_factory=dict)
    metric_names: tuple[str, ...] = DEFAULT_SINGLE_METRICS

    def __post_init__(self) -> None:
        """Freeze sweep configuration mappings."""

        object.__setattr__(self, "_pipelines", MappingProxyType(dict(self._pipelines)))
        object.__setattr__(self, "metric_names", tuple(self.metric_names))

    def score(self, method: str, **parameters: object) -> Sweep:
        """Return a new sweep with the base scoring method configured."""

        return replace(
            self,
            base_pipeline=self.base_pipeline.score(method, **parameters),
        )

    def filter(
        self,
        strategy: str | FilterCallable,
        **parameters: object,
    ) -> Sweep:
        """Return a new sweep with the base filter configured."""

        return replace(
            self,
            base_pipeline=self.base_pipeline.filter(strategy, **parameters),
        )

    def vary_filter(
        self,
        strategy: str | None = None,
        **parameter_grid: object,
    ) -> Sweep:
        """Add filter-parameter configurations to the sweep.

        Grid values may be scalars or finite sequences. Changing only filter
        parameters reuses cached method scores during `run()`.
        """

        if self.base_pipeline.method_name is None:
            raise ConfigurationError(
                "vary_filter() requires a scoring method. Call score() first."
            )
        filter_name = strategy or self.base_pipeline.filter_name
        if filter_name is None:
            raise ConfigurationError(
                "vary_filter() requires a filter strategy argument or a base "
                "filter configured with filter()."
            )
        if filter_name != "custom":
            pipeline().filter(filter_name)

        base_filter_parameters = (
            dict(self.base_pipeline.filter_parameters)
            if filter_name == self.base_pipeline.filter_name
            else {}
        )
        generated: dict[str, _SweepPipeline] = {}
        for parameters in _parameter_product(parameter_grid):
            filter_parameters = {**base_filter_parameters, **parameters}
            candidate = Pipeline(
                method_name=self.base_pipeline.method_name,
                method_parameters=self.base_pipeline.method_parameters,
                filter_name=filter_name,
                filter_parameters=filter_parameters,
                filter_callable=(
                    self.base_pipeline.filter_callable
                    if filter_name == "custom"
                    else None
                ),
            )
            name = _generated_name(
                candidate,
                varied_parameters=parameters,
                fallback="filter",
            )
            generated[_unique_name(name, self._pipelines, generated)] = _SweepPipeline(
                pipeline=candidate,
                varied_parameters=parameters,
            )
        return replace(self, _pipelines={**self._pipelines, **generated})

    def vary_method(
        self,
        method: str | None = None,
        **parameter_grid: object,
    ) -> Sweep:
        """Add method-parameter configurations to the sweep.

        Each distinct method-parameter combination gets its own score
        computation and cache entry.
        """

        method_name = method or self.base_pipeline.method_name
        if method_name is None:
            raise ConfigurationError(
                "vary_method() requires a method argument or a base scoring "
                "method configured with score()."
            )
        if self.base_pipeline.filter_name is None:
            raise ConfigurationError(
                "vary_method() requires a filter. Call filter() first."
            )
        pipeline().score(method_name)

        base_method_parameters = (
            dict(self.base_pipeline.method_parameters)
            if method_name == self.base_pipeline.method_name
            else {}
        )
        generated: dict[str, _SweepPipeline] = {}
        for parameters in _parameter_product(parameter_grid):
            method_parameters = {**base_method_parameters, **parameters}
            candidate = Pipeline(
                method_name=method_name,
                method_parameters=method_parameters,
                filter_name=self.base_pipeline.filter_name,
                filter_parameters=self.base_pipeline.filter_parameters,
                filter_callable=self.base_pipeline.filter_callable,
            )
            name = _generated_name(
                candidate,
                varied_parameters=parameters,
                fallback="method",
            )
            generated[_unique_name(name, self._pipelines, generated)] = _SweepPipeline(
                pipeline=candidate,
                varied_parameters=parameters,
            )
        return replace(self, _pipelines={**self._pipelines, **generated})

    def grid(
        self,
        *,
        methods: Mapping[str, Mapping[str, object]],
        filters: Mapping[str, Mapping[str, object]],
    ) -> Sweep:
        """Add a Cartesian product of method and filter configurations.

        Method and filter mapping values are parameter grids. Scalars are fixed
        values and finite sequences expand into grid values.
        """

        generated: dict[str, _SweepPipeline] = {}
        method_configs = _method_configurations(methods, caller="grid")
        filter_configs = _filter_configurations(filters, caller="grid")

        for method_config in method_configs:
            for filter_config in filter_configs:
                candidate = Pipeline(
                    method_name=method_config.name,
                    method_parameters=method_config.parameters,
                    filter_name=filter_config.name,
                    filter_parameters=filter_config.parameters,
                )
                name = _generated_name(
                    candidate,
                    varied_parameters=_qualified_parameters(
                        method_parameters=method_config.parameters,
                        filter_parameters=filter_config.parameters,
                    ),
                    fallback="grid",
                )
                generated[_unique_name(name, self._pipelines, generated)] = (
                    _SweepPipeline(
                        pipeline=candidate,
                        varied_parameters={
                            "method": method_config.name,
                            "filter": filter_config.name,
                            "method_parameters": dict(method_config.parameters),
                            "filter_parameters": dict(filter_config.parameters),
                        },
                    )
                )
        return replace(self, _pipelines={**self._pipelines, **generated})

    def measure(self, metrics: Sequence[str]) -> Sweep:
        """Return a new sweep configured with requested metric names."""

        if isinstance(metrics, (str, bytes)):
            raise ConfigurationError(
                "measure() requires a sequence of metric names, not a string."
            )
        if not metrics:
            raise ConfigurationError("measure() requires at least one metric.")
        metric_names = tuple(metrics)
        for metric_name in metric_names:
            if not isinstance(metric_name, str) or not metric_name:
                raise ConfigurationError("Metric names must be non-empty strings.")
            get_metric(metric_name)
        return replace(self, metric_names=metric_names)

    def describe(self) -> dict[str, object]:
        """Return a reproducible summary of this sweep configuration."""

        return {
            "network": self.network.summary(),
            "base_pipeline": self.base_pipeline.to_dict(),
            "configurations": {
                name: spec.pipeline.to_dict() for name, spec in self._pipelines.items()
            },
            "metrics": list(self.metric_names),
        }

    def run(self) -> SweepResult:
        """Execute the configured sweep and return tidy result tables."""

        sweep_pipelines = self._execution_pipelines()
        method_cache: dict[MethodCacheKey, MethodResult] = {}
        results: dict[str, BackboneResult] = {}
        metric_rows: list[dict[str, object]] = []
        run_rows: list[dict[str, object]] = []
        score_cache_hits = 0
        score_cache_misses = 0

        for run_id, (name, spec) in enumerate(sweep_pipelines.items(), start=1):
            pipeline_config = spec.pipeline
            row_base = _row_base(run_id, name, spec)
            score_cache_key = _score_cache_key_text(self.network, pipeline_config)
            score_cache_hit: bool | None = None
            try:
                method_result, score_cache_hit = _cached_method_result(
                    self.network,
                    pipeline_config,
                    method_cache,
                )
                if score_cache_hit:
                    score_cache_hits += 1
                else:
                    score_cache_misses += 1
                result = _filter_method_result(
                    self.network,
                    method_result,
                    pipeline_config,
                )
            except Exception as exc:
                failure_detail = f"{type(exc).__name__}: {exc}"
                run_rows.append(
                    {
                        **row_base,
                        "status": "failed",
                        "explanation": str(exc),
                        "warning": "",
                        "failure_detail": failure_detail,
                        "score_cache_key": score_cache_key,
                        "score_cache_hit": score_cache_hit,
                    }
                )
                metric_rows.append(
                    {
                        **row_base,
                        "metric": None,
                        "value": None,
                        "status": "failed",
                        "explanation": str(exc),
                        "warning": "",
                        "failure_detail": failure_detail,
                        "score_cache_key": score_cache_key,
                        "score_cache_hit": score_cache_hit,
                    }
                )
                continue

            warning = "; ".join(result.warnings)
            results[name] = result
            run_rows.append(
                {
                    **row_base,
                    "status": "ok",
                    "explanation": "",
                    "warning": warning,
                    "failure_detail": "",
                    "score_cache_key": score_cache_key,
                    "score_cache_hit": score_cache_hit,
                }
            )
            metric_rows.extend(
                _metric_rows(
                    name=name,
                    result=result,
                    row_base=row_base,
                    metric_names=self.metric_names,
                    warning=warning,
                    score_cache_key=score_cache_key,
                    score_cache_hit=score_cache_hit,
                )
            )

        return SweepResult(
            results=results,
            _table=pd.DataFrame(metric_rows, columns=_METRIC_TABLE_COLUMNS),
            _runs=pd.DataFrame(run_rows, columns=_RUN_TABLE_COLUMNS),
            score_cache_hits=score_cache_hits,
            score_cache_misses=score_cache_misses,
        )

    def _execution_pipelines(self) -> Mapping[str, _SweepPipeline]:
        if self._pipelines:
            return self._pipelines
        if (
            self.base_pipeline.method_name is None
            or self.base_pipeline.filter_name is None
        ):
            raise ConfigurationError(
                "run() requires at least one configured pipeline. Use score() "
                "and filter(), vary_filter(), vary_method(), or grid()."
            )
        name = _generated_name(
            self.base_pipeline,
            varied_parameters={},
            fallback="pipeline",
        )
        return MappingProxyType(
            {
                name: _SweepPipeline(
                    pipeline=self.base_pipeline,
                    varied_parameters={},
                )
            }
        )


def sweep(graph_or_network: nx.Graph | Network) -> Sweep:
    """Return a parameter sweep builder for a NetworkX graph or Network."""

    return Sweep(network=ensure_network(graph_or_network))


@dataclass(frozen=True)
class _SweepPipeline:
    pipeline: Pipeline
    varied_parameters: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "varied_parameters", MappingProxyType(dict(self.varied_parameters))
        )


@dataclass(frozen=True)
class _NamedGridConfiguration:
    name: str
    parameters: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))


def _cached_method_result(
    network: Network,
    pipeline_config: Pipeline,
    cache: dict[MethodCacheKey, MethodResult],
) -> tuple[MethodResult, bool]:
    if pipeline_config.method_name is None:
        raise ConfigurationError("Sweep pipeline has no scoring method configured.")

    cache_key = _method_cache_key(network, pipeline_config)
    if cache_key in cache:
        return cache[cache_key], True

    method_result = pipeline_config.compute(network)
    cache[cache_key] = method_result
    return method_result, False


def _filter_method_result(
    network: Network,
    method_result: MethodResult,
    pipeline_config: Pipeline,
) -> BackboneResult:
    if pipeline_config.filter_name is None:
        raise ConfigurationError("Sweep pipeline has no filter strategy configured.")

    if pipeline_config.filter_name == "custom":
        if pipeline_config.filter_callable is None:
            raise ConfigurationError("Custom sweep filter strategy has no callable.")
        strategy: str | FilterCallable = pipeline_config.filter_callable
    else:
        strategy = pipeline_config.filter_name

    return filter_scores(
        network,
        method_result,
        strategy=strategy,
        **dict(pipeline_config.filter_parameters),
    )


def _metric_rows(
    *,
    name: str,
    result: BackboneResult,
    row_base: Mapping[str, object],
    metric_names: Sequence[str],
    warning: str,
    score_cache_key: str,
    score_cache_hit: bool | None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    table = compare({name: result}).table(metrics=metric_names)
    for metric_row in table.to_dict(orient="records"):
        rows.append(
            {
                **row_base,
                "metric": metric_row["metric"],
                "value": metric_row["value"],
                "status": metric_row["status"],
                "explanation": metric_row["explanation"],
                "warning": warning,
                "failure_detail": "",
                "score_cache_key": score_cache_key,
                "score_cache_hit": score_cache_hit,
            }
        )
    return rows


def _row_base(
    run_id: int,
    name: str,
    spec: _SweepPipeline,
) -> dict[str, object]:
    varied_parameter = ""
    parameter_value: object = None
    if len(spec.varied_parameters) == 1:
        varied_parameter, parameter_value = next(iter(spec.varied_parameters.items()))

    return {
        "run_id": run_id,
        "pipeline_name": name,
        "method": spec.pipeline.method_name,
        "method_parameters": dict(spec.pipeline.method_parameters),
        "filter": spec.pipeline.filter_name,
        "filter_parameters": dict(spec.pipeline.filter_parameters),
        "varied_parameter": varied_parameter,
        "parameter_value": parameter_value,
        "varied_parameters": dict(spec.varied_parameters),
    }


def _parameter_product(
    parameter_grid: Mapping[str, object],
) -> tuple[dict[str, object], ...]:
    if not parameter_grid:
        return ({},)

    names = tuple(parameter_grid)
    values: list[tuple[object, ...]] = []
    for name in names:
        options = _grid_values(parameter_grid[name])
        if not options:
            raise ConfigurationError(
                f"Sweep parameter grid {name!r} must contain at least one value."
            )
        values.append(options)
    combinations: list[dict[str, object]] = []
    for combination in product(*values):
        combinations.append(dict(zip(names, combination, strict=True)))
    return tuple(combinations)


def _grid_values(value: object) -> tuple[object, ...]:
    if isinstance(value, (str, bytes, Mapping)):
        return (value,)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted(value, key=repr))
    if isinstance(value, Sequence):
        return tuple(value)
    return (value,)


def _method_configurations(
    methods: Mapping[str, Mapping[str, object]],
    *,
    caller: str,
) -> tuple[_NamedGridConfiguration, ...]:
    if not isinstance(methods, Mapping):
        raise ConfigurationError(f"{caller}() methods must be a mapping.")
    if not methods:
        raise ConfigurationError(f"{caller}() requires at least one method.")

    configurations: list[_NamedGridConfiguration] = []
    for method_name, method_grid in methods.items():
        if not isinstance(method_name, str) or not method_name:
            raise ConfigurationError("Method names must be non-empty strings.")
        if not isinstance(method_grid, Mapping):
            raise ConfigurationError(
                f"Method grid for {method_name!r} must be a mapping."
            )
        pipeline().score(method_name)
        configurations.extend(
            _NamedGridConfiguration(name=method_name, parameters=parameters)
            for parameters in _parameter_product(method_grid)
        )
    return tuple(configurations)


def _filter_configurations(
    filters: Mapping[str, Mapping[str, object]],
    *,
    caller: str,
) -> tuple[_NamedGridConfiguration, ...]:
    if not isinstance(filters, Mapping):
        raise ConfigurationError(f"{caller}() filters must be a mapping.")
    if not filters:
        raise ConfigurationError(f"{caller}() requires at least one filter.")

    configurations: list[_NamedGridConfiguration] = []
    for filter_name, filter_grid in filters.items():
        if not isinstance(filter_name, str) or not filter_name:
            raise ConfigurationError("Filter names must be non-empty strings.")
        if not isinstance(filter_grid, Mapping):
            raise ConfigurationError(
                f"Filter grid for {filter_name!r} must be a mapping."
            )
        pipeline().filter(filter_name)
        configurations.extend(
            _NamedGridConfiguration(name=filter_name, parameters=parameters)
            for parameters in _parameter_product(filter_grid)
        )
    return tuple(configurations)


def _qualified_parameters(
    *,
    method_parameters: Mapping[str, object],
    filter_parameters: Mapping[str, object],
) -> dict[str, object]:
    qualified = {f"method_{name}": value for name, value in method_parameters.items()}
    qualified.update(
        {f"filter_{name}": value for name, value in filter_parameters.items()}
    )
    return qualified


def _generated_name(
    pipeline_config: Pipeline,
    *,
    varied_parameters: Mapping[str, object],
    fallback: str,
) -> str:
    method_name = _name_part(pipeline_config.method_name or "unscored")
    filter_name = _name_part(pipeline_config.filter_name or "unfiltered")
    varied = (
        "_".join(
            f"{_name_part(name)}_{_name_part(value)}"
            for name, value in varied_parameters.items()
        )
        if varied_parameters
        else fallback
    )
    return f"{method_name}_{filter_name}_{varied}"


def _name_part(value: object) -> str:
    text = str(value).replace(".", "p").replace("-", "m")
    cleaned = re.sub(r"[^0-9A-Za-z]+", "_", text).strip("_").lower()
    return cleaned or "value"


def _unique_name(
    name: str,
    existing: Mapping[str, object],
    generated: Mapping[str, object],
) -> str:
    if name not in existing and name not in generated:
        return name
    index = 2
    while True:
        candidate = f"{name}_{index}"
        if candidate not in existing and candidate not in generated:
            return candidate
        index += 1


def _method_cache_key(
    network: Network,
    pipeline_config: Pipeline,
) -> MethodCacheKey:
    if pipeline_config.method_name is None:
        raise ConfigurationError("Sweep pipeline has no scoring method configured.")
    return (
        id(network.graph),
        pipeline_config.method_name,
        _freeze_mapping(pipeline_config.method_parameters),
    )


def _score_cache_key_text(
    network: Network,
    pipeline_config: Pipeline,
) -> str:
    if pipeline_config.method_name is None:
        return ""
    cache_key = _method_cache_key(network, pipeline_config)
    return repr(cache_key)


def _freeze_mapping(parameters: Mapping[str, object]) -> tuple[tuple[str, object], ...]:
    return tuple(
        (name, _freeze_value(value))
        for name, value in sorted(parameters.items(), key=lambda item: item[0])
    )


def _freeze_value(value: object) -> object:
    if isinstance(value, Mapping):
        return tuple(
            (name, _freeze_value(item))
            for name, item in sorted(value.items(), key=lambda entry: str(entry[0]))
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted((_freeze_value(item) for item in value), key=repr))
    try:
        hash(value)
    except TypeError:
        return repr(value)
    return value
