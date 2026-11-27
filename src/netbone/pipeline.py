"""Pipeline configuration and execution helpers."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

import networkx as nx

from netbone._version import __version__
from netbone.exceptions import CompatibilityError, ConfigurationError, ValidationError
from netbone.filters.registry import get_filter
from netbone.methods.registry import get_method, run_method
from netbone.network import Network, ensure_network
from netbone.results import BackboneResult, MethodResult, Selection

FilterCallable = Callable[..., Selection]
PIPELINE_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class Pipeline:
    """Immutable scoring and filtering configuration."""

    method_name: str | None = None
    method_parameters: Mapping[str, object] = field(default_factory=dict)
    filter_name: str | None = None
    filter_parameters: Mapping[str, object] = field(default_factory=dict)
    filter_callable: FilterCallable | None = None

    def __post_init__(self) -> None:
        """Freeze pipeline parameter mappings."""

        object.__setattr__(
            self, "method_parameters", MappingProxyType(dict(self.method_parameters))
        )
        object.__setattr__(
            self, "filter_parameters", MappingProxyType(dict(self.filter_parameters))
        )

    @classmethod
    def from_dict(cls, config: Mapping[str, object]) -> Pipeline:
        """Restore a pipeline configuration produced by `Pipeline.to_dict()`.

        Only registered method and filter names can be deserialized. Custom
        filter callables must be recreated in Python and attached with
        `Pipeline.filter(...)`.

        Args:
            config: Pipeline configuration mapping.

        Raises:
            ConfigurationError: If the configuration shape is invalid, a
                registered method or filter is unknown, or a custom callable
                filter is present.
        """

        if not isinstance(config, Mapping):
            raise ConfigurationError(
                "Pipeline.from_dict() requires a pipeline configuration mapping."
            )

        restored = cls()
        method_config = _read_named_config(config.get("method"), section="method")
        if method_config is not None:
            method_name, method_parameters = method_config
            restored = restored.score(method_name, **method_parameters)

        filter_value = config.get("filter")
        filter_config = _read_named_config(filter_value, section="filter")
        if filter_config is not None:
            if isinstance(filter_value, Mapping) and "callable" in filter_value:
                raise ConfigurationError(
                    "Pipeline.from_dict() cannot deserialize custom filter "
                    "callables. Recreate the callable in Python and configure "
                    "the pipeline with filter(callable, ...)."
                )
            filter_name, filter_parameters = filter_config
            if filter_name == "custom":
                raise ConfigurationError(
                    "Pipeline.from_dict() cannot deserialize custom filter "
                    "callables. Recreate the callable in Python and configure "
                    "the pipeline with filter(callable, ...)."
                )
            restored = restored.filter(filter_name, **filter_parameters)

        return restored

    @classmethod
    def from_json(cls, path: str | Path) -> Pipeline:
        """Restore a registered pipeline configuration from a JSON file.

        Args:
            path: JSON file created from `Pipeline.to_json(...)` or equivalent
                `Pipeline.to_dict()` output.

        Raises:
            ValidationError: If the file is missing, unreadable, or invalid
                JSON.
            ConfigurationError: If the decoded configuration is invalid.
        """

        config_path = Path(path)
        try:
            raw_config = config_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ValidationError(
                f"Pipeline config file does not exist: {config_path}."
            ) from exc
        except OSError as exc:
            raise ValidationError(
                f"Pipeline config file could not be read: {config_path}."
            ) from exc

        try:
            config = json.loads(raw_config)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                f"Pipeline config file is not valid JSON: {config_path}."
            ) from exc

        if not isinstance(config, Mapping):
            raise ConfigurationError(
                "Pipeline config JSON must contain a configuration object."
            )
        return cls.from_dict(config)

    def score(self, method: str, **parameters: object) -> Pipeline:
        """Return a new pipeline configured with a scoring method.

        Args:
            method: Registered method name.
            **parameters: Method-specific parameters.

        Raises:
            ConfigurationError: If the method is unknown.
        """

        get_method(method)
        return Pipeline(
            method_name=method,
            method_parameters=parameters,
            filter_name=self.filter_name,
            filter_parameters=self.filter_parameters,
            filter_callable=self.filter_callable,
        )

    def filter(
        self,
        strategy: str | FilterCallable,
        **parameters: object,
    ) -> Pipeline:
        """Return a new pipeline configured with a filtering strategy.

        Args:
            strategy: Registered filter name or custom filter callable.
            **parameters: Filter-specific parameters.

        Raises:
            ConfigurationError: If the filter strategy is unknown.
        """

        filter_callable: FilterCallable | None = None
        if isinstance(strategy, str):
            get_filter(strategy)
            filter_name = strategy
        elif callable(strategy):
            filter_name = "custom"
            filter_callable = strategy
        else:
            raise ConfigurationError(
                "Filter strategy must be a registered filter name or callable."
            )
        return Pipeline(
            method_name=self.method_name,
            method_parameters=self.method_parameters,
            filter_name=filter_name,
            filter_parameters=parameters,
            filter_callable=filter_callable,
        )

    def compute(self, graph_or_network: nx.Graph | Network) -> MethodResult:
        """Compute method statistics without applying a filter."""

        network = ensure_network(graph_or_network)
        return _compute_method(network, self.method_name, self.method_parameters)

    def run(self, graph_or_network: nx.Graph | Network) -> BackboneResult:
        """Compute statistics, apply the filter, and return a backbone result.

        Raises:
            ConfigurationError: If the pipeline has no scoring method or no
                filter strategy.
            CompatibilityError: If the selected result target cannot be
                extracted by this release.
        """

        network = ensure_network(graph_or_network)
        method_result = _compute_method(
            network, self.method_name, self.method_parameters
        )
        selection = _apply_filter(
            network,
            method_result,
            self.filter_name,
            self.filter_parameters,
            self.filter_callable,
        )
        return _build_result(network, method_result, selection, self.to_dict())

    def describe(self) -> dict[str, object]:
        """Return a compact description of the configured pipeline."""

        return self.to_dict()

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible pipeline configuration summary."""

        return {
            "schema_version": PIPELINE_SCHEMA_VERSION,
            "package": {
                "name": "netbone",
                "version": __version__,
            },
            "method": (
                None
                if self.method_name is None
                else {
                    "name": self.method_name,
                    "parameters": dict(self.method_parameters),
                }
            ),
            "filter": (
                None
                if self.filter_name is None
                else _filter_config(
                    self.filter_name,
                    self.filter_parameters,
                    self.filter_callable,
                )
            ),
        }

    def to_json(self, path: str | Path, *, indent: int | None = 2) -> None:
        """Write this registered pipeline configuration to a JSON file.

        Args:
            path: Destination JSON file path.
            indent: JSON indentation level. Pass `None` for compact JSON.

        Raises:
            ConfigurationError: If the pipeline contains a custom callable
                filter, which cannot be reliably restored from JSON.
            ValidationError: If the file cannot be written.
        """

        config = self.to_dict()
        filter_config = config.get("filter")
        if isinstance(filter_config, Mapping) and "callable" in filter_config:
            raise ConfigurationError(
                "Pipeline.to_json() cannot serialize custom filter callables for "
                "reproducible loading. Save only registered method and filter "
                "pipelines, or recreate the callable in Python."
            )

        config_path = Path(path)
        try:
            serialized = json.dumps(config, indent=indent, sort_keys=True) + "\n"
        except TypeError as exc:
            raise ConfigurationError(
                "Pipeline configuration contains a value that cannot be serialized "
                "to JSON. Use registered methods and filters with JSON-compatible "
                "parameter values."
            ) from exc

        try:
            config_path.write_text(
                serialized,
                encoding="utf-8",
            )
        except OSError as exc:
            raise ValidationError(
                f"Pipeline config file could not be written: {config_path}."
            ) from exc


def pipeline() -> Pipeline:
    """Return an empty immutable pipeline."""

    return Pipeline()


def score(
    graph_or_network: nx.Graph | Network,
    method: str = "edge_weight",
    **parameters: object,
) -> MethodResult:
    """Compute method statistics using the functional API."""

    return pipeline().score(method, **parameters).compute(graph_or_network)


def filter_scores(
    graph_or_network: nx.Graph | Network,
    method_result: MethodResult,
    strategy: str | FilterCallable = "threshold",
    **parameters: object,
) -> BackboneResult:
    """Filter existing method statistics using the functional API."""

    network = ensure_network(graph_or_network)
    if isinstance(strategy, str):
        filter_name = strategy
        filter_callable = None
    elif callable(strategy):
        filter_name = "custom"
        filter_callable = strategy
    else:
        raise ConfigurationError(
            "Filter strategy must be a registered filter name or callable."
        )
    selection = _apply_filter(
        network,
        method_result,
        filter_name,
        parameters,
        filter_callable,
    )
    config = Pipeline(
        method_name=method_result.method_name,
        method_parameters=method_result.parameters,
        filter_name=filter_name,
        filter_parameters=parameters,
        filter_callable=filter_callable,
    ).to_dict()
    return _build_result(network, method_result, selection, config)


def _compute_method(
    network: Network,
    method_name: str | None,
    parameters: Mapping[str, object],
) -> MethodResult:
    if method_name is None:
        raise ConfigurationError("Pipeline has no scoring method configured.")
    method = get_method(method_name)
    if network.directed and not bool(method.metadata.get("supports_directed", False)):
        raise CompatibilityError(
            f"Method {method_name!r} does not support directed graphs. "
            "Choose a method whose metadata declares directed support, or convert "
            "the graph to undirected with an explicit aggregation rule before "
            "scoring."
        )
    return run_method(method, network, parameters)


def _apply_filter(
    network: Network,
    method_result: MethodResult,
    filter_name: str | None,
    parameters: Mapping[str, object],
    filter_callable: FilterCallable | None = None,
) -> Selection:
    if filter_name is None:
        raise ConfigurationError("Pipeline has no filter strategy configured.")
    if filter_name == "custom":
        if filter_callable is None:
            raise ConfigurationError("Custom filter strategy has no callable.")
        selection = filter_callable(
            method_result,
            network.to_original_graph(),
            **dict(parameters),
        )
        if not isinstance(selection, Selection):
            raise ConfigurationError("Custom filter callable must return Selection.")
        return selection
    return get_filter(filter_name).apply(method_result, parameters)


def _filter_config(
    filter_name: str,
    parameters: Mapping[str, object],
    filter_callable: FilterCallable | None,
) -> dict[str, object]:
    config: dict[str, object] = {
        "name": filter_name,
        "parameters": dict(parameters),
    }
    if filter_callable is not None:
        config["callable"] = getattr(
            filter_callable,
            "__name__",
            filter_callable.__class__.__name__,
        )
    return config


def _read_named_config(
    config: object,
    *,
    section: str,
) -> tuple[str, dict[str, object]] | None:
    if config is None:
        return None
    if not isinstance(config, Mapping):
        raise ConfigurationError(
            f"Pipeline.from_dict() {section} config must be a mapping or None."
        )

    name = config.get("name")
    if not isinstance(name, str) or not name:
        raise ConfigurationError(
            f"Pipeline.from_dict() {section} config requires a non-empty string 'name'."
        )

    parameters = config.get("parameters", {})
    if not isinstance(parameters, Mapping):
        raise ConfigurationError(
            f"Pipeline.from_dict() {section} parameters must be a mapping."
        )

    parameter_dict: dict[str, object] = {}
    for parameter_name, value in parameters.items():
        if not isinstance(parameter_name, str):
            raise ConfigurationError(
                f"Pipeline.from_dict() {section} parameter names must be strings."
            )
        parameter_dict[parameter_name] = value

    return name, parameter_dict


def _build_result(
    network: Network,
    method_result: MethodResult,
    selection: Selection,
    pipeline_config: Mapping[str, object],
) -> BackboneResult:
    if selection.target != method_result.target:
        raise CompatibilityError(
            "Selection target does not match method result target. Recompute "
            "the selection from the method result before extracting."
        )
    result_graph = (
        _edge_selection_graph(network, method_result, selection)
        if selection.target == "edge"
        else _node_selection_graph(network, method_result, selection)
    )
    return BackboneResult(
        graph=result_graph,
        original_graph=network.to_original_graph(),
        method_result=method_result,
        selection=selection,
        pipeline_config=pipeline_config,
        context=network.context,
        network_metadata=network.metadata,
        warnings=(
            _network_warnings(network) + method_result.warnings + selection.warnings
        ),
    )


def _network_warnings(network: Network) -> tuple[str, ...]:
    values = network.metadata.get("netbone_warnings", ())
    if not isinstance(values, list | tuple):
        return ()
    return tuple(str(value) for value in values)


def _edge_selection_graph(
    network: Network,
    method_result: MethodResult,
    selection: Selection,
) -> nx.Graph:
    _validate_edge_selection_compatible(network, method_result, selection)
    drop_isolates = bool(selection.parameters.get("drop_isolates", False))
    return network.to_original_graph(
        edge_ids=selection.selected_ids,
        drop_isolates=drop_isolates,
    )


def _node_selection_graph(
    network: Network,
    method_result: MethodResult,
    selection: Selection,
) -> nx.Graph:
    _validate_node_selection_compatible(network, method_result, selection)
    return network.to_original_graph(node_ids=selection.selected_ids)


def _validate_edge_selection_compatible(
    network: Network,
    method_result: MethodResult,
    selection: Selection,
) -> None:
    edge_rows = method_result.statistics.set_index("edge_id", drop=False)
    known_stat_ids = set(int(edge_id) for edge_id in edge_rows.index.tolist())
    network_ids = set(network.edge_id_to_endpoints)
    extra_stat_ids = known_stat_ids.difference(network_ids)
    if extra_stat_ids:
        extra_text = ", ".join(str(edge_id) for edge_id in sorted(extra_stat_ids))
        raise CompatibilityError(
            "Method statistics reference edge id(s) absent from the target "
            f"network: {extra_text}."
        )
    missing_stat_ids = network_ids.difference(known_stat_ids)
    if missing_stat_ids:
        missing_text = ", ".join(str(edge_id) for edge_id in sorted(missing_stat_ids))
        raise CompatibilityError(
            "Method statistics do not cover target network edge id(s): "
            f"{missing_text}. Recompute scores for this network before filtering."
        )

    referenced_ids = set(selection.selected_ids).union(selection.rejected_ids)
    unknown_stat_ids = referenced_ids.difference(known_stat_ids)
    if unknown_stat_ids:
        unknown_text = ", ".join(str(edge_id) for edge_id in sorted(unknown_stat_ids))
        raise CompatibilityError(
            "Selection references edge id(s) absent from method statistics: "
            f"{unknown_text}."
        )
    unclassified_ids = known_stat_ids.difference(referenced_ids)
    if unclassified_ids:
        unclassified_text = ", ".join(
            str(edge_id) for edge_id in sorted(unclassified_ids)
        )
        raise CompatibilityError(
            "Selection does not classify method statistic edge id(s): "
            f"{unclassified_text}."
        )

    for edge_id in sorted(known_stat_ids):
        row = edge_rows.loc[edge_id]
        source_id = int(row["source_id"])
        target_id = int(row["target_id"])
        expected_source_id, expected_target_id = network.edge_id_to_endpoints[edge_id]
        expected_source = network.node_id_to_original[expected_source_id]
        expected_target = network.node_id_to_original[expected_target_id]

        if (
            source_id != expected_source_id
            or target_id != expected_target_id
            or row["source"] != expected_source
            or row["target"] != expected_target
        ):
            raise CompatibilityError(
                f"Method statistics for edge id {edge_id} do not match the "
                "target network. Recompute scores for this network before "
                "filtering."
            )


def _validate_node_selection_compatible(
    network: Network,
    method_result: MethodResult,
    selection: Selection,
) -> None:
    node_rows = method_result.statistics.set_index("node_id", drop=False)
    known_stat_ids = set(int(node_id) for node_id in node_rows.index.tolist())
    network_ids = set(network.node_id_to_original)
    extra_stat_ids = known_stat_ids.difference(network_ids)
    if extra_stat_ids:
        extra_text = ", ".join(str(node_id) for node_id in sorted(extra_stat_ids))
        raise CompatibilityError(
            "Method statistics reference node id(s) absent from the target "
            f"network: {extra_text}."
        )
    missing_stat_ids = network_ids.difference(known_stat_ids)
    if missing_stat_ids:
        missing_text = ", ".join(str(node_id) for node_id in sorted(missing_stat_ids))
        raise CompatibilityError(
            "Method statistics do not cover target network node id(s): "
            f"{missing_text}. Recompute scores for this network before filtering."
        )

    referenced_ids = set(selection.selected_ids).union(selection.rejected_ids)
    unknown_stat_ids = referenced_ids.difference(known_stat_ids)
    if unknown_stat_ids:
        unknown_text = ", ".join(str(node_id) for node_id in sorted(unknown_stat_ids))
        raise CompatibilityError(
            "Selection references node id(s) absent from method statistics: "
            f"{unknown_text}."
        )
    unclassified_ids = known_stat_ids.difference(referenced_ids)
    if unclassified_ids:
        unclassified_text = ", ".join(
            str(node_id) for node_id in sorted(unclassified_ids)
        )
        raise CompatibilityError(
            "Selection does not classify method statistic node id(s): "
            f"{unclassified_text}."
        )

    for node_id in sorted(known_stat_ids):
        row = node_rows.loc[node_id]
        expected_node = network.node_id_to_original[node_id]
        if int(row["node_id"]) != node_id or row["node"] != expected_node:
            raise CompatibilityError(
                f"Method statistics for node id {node_id} do not match the "
                "target network. Recompute scores for this network before "
                "filtering."
            )
