"""Reproducible experiment bundle export."""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import sys
import warnings
from collections.abc import Mapping
from pathlib import Path
from typing import TypeAlias, TypeVar

import networkx as nx
import pandas as pd

from netbone._json import json_value
from netbone._version import __version__
from netbone.compare import Comparison
from netbone.exceptions import ConfigurationError, ValidationError
from netbone.pipeline import Pipeline
from netbone.report import Report, report
from netbone.results import BackboneResult
from netbone.sweep import SweepResult

EXPERIMENT_BUNDLE_SCHEMA_VERSION = "1.0"
ExperimentSubject: TypeAlias = BackboneResult | Comparison | SweepResult
_Target = TypeVar("_Target")
BACKBONE_COLOR = "#0072B2"
REJECTED_COLOR = "#D9D9D9"
_STATISTIC_IDENTITY_COLUMNS = frozenset(
    {
        "edge_id",
        "source_id",
        "target_id",
        "source",
        "target",
        "node_id",
        "node",
    }
)
_MISSING_GRAPH_ATTRIBUTE = object()


def save_experiment(
    subject: ExperimentSubject,
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Save a deterministic experiment bundle and return the bundle directory.

    The bundle contains a manifest, deterministic report files, JSON payloads,
    and CSV tables suitable for inspection, sharing, and rerunning registered
    pipelines.

    Args:
        subject: `BackboneResult`, `Comparison`, or `SweepResult` to export.
        path: Destination directory for the bundle.
        overwrite: Whether an existing destination directory may be replaced.
            Only empty directories and earlier Netbone bundles are replaced;
            any other existing directory is left untouched.

    Raises:
        ConfigurationError: If the subject type is unsupported.
        ValidationError: If the destination cannot be prepared or written.
    """

    if not isinstance(subject, BackboneResult | Comparison | SweepResult):
        raise ConfigurationError(
            "save_experiment() requires a BackboneResult, Comparison, or SweepResult."
        )

    destination = _prepare_directory(path, overwrite=overwrite)
    subject_type = _subject_type(subject)
    files: dict[str, str] = {}

    experiment_report = report(subject)
    files.update(_write_report_files(destination, experiment_report))

    if isinstance(subject, BackboneResult):
        files.update(_write_backbone_result(destination, subject))
    elif isinstance(subject, Comparison):
        files.update(_write_comparison(destination, subject))
    else:
        files.update(_write_sweep_result(destination, subject))

    manifest = {
        "bundle_schema_version": EXPERIMENT_BUNDLE_SCHEMA_VERSION,
        "package": {
            "name": "netbone",
            "version": __version__,
        },
        "python": {
            "version": sys.version.split()[0],
        },
        "subject_type": subject_type,
        "files": files,
    }
    _write_json(destination / "manifest.json", manifest)
    return destination.resolve()


def _prepare_directory(path: str | Path, *, overwrite: bool) -> Path:
    destination = Path(path)
    if destination.exists() and destination.is_file():
        raise ValidationError(
            f"Experiment bundle path points to a file: {destination}."
        )
    if destination.exists():
        if not overwrite:
            raise ValidationError(
                f"Experiment bundle directory already exists: {destination}."
            )
        if not _is_replaceable_bundle(destination):
            raise ValidationError(
                f"Refusing to overwrite {destination}: it is not empty and is not "
                "a Netbone experiment bundle (no manifest.json with "
                "bundle_schema_version). Choose a new or empty directory."
            )
        try:
            shutil.rmtree(destination)
        except OSError as exc:
            raise ValidationError(
                f"Experiment bundle directory could not be replaced: {destination}."
            ) from exc
    try:
        destination.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        raise ValidationError(
            f"Experiment bundle directory could not be created: {destination}."
        ) from exc
    return destination


def _is_replaceable_bundle(directory: Path) -> bool:
    """Return whether overwrite may delete this existing directory."""

    try:
        if not any(directory.iterdir()):
            return True
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(manifest, Mapping) and "bundle_schema_version" in manifest


def _write_report_files(destination: Path, experiment_report: Report) -> dict[str, str]:
    markdown_path = Path("report.md")
    json_path = Path("report.json")
    experiment_report.write_markdown(destination / markdown_path)
    _write_json(destination / json_path, experiment_report.to_dict())
    return {
        "report_markdown": markdown_path.as_posix(),
        "report_json": json_path.as_posix(),
    }


def _write_backbone_result(
    destination: Path,
    result: BackboneResult,
) -> dict[str, str]:
    tables_dir = destination / "tables"
    graphs_dir = destination / "graphs"
    tables_dir.mkdir()
    graphs_dir.mkdir()

    files = {
        "subject_json": "result.json",
        "pipeline_json": "pipeline.json",
        "network_metadata_json": "network_metadata.json",
        "method_statistics_csv": "tables/method_statistics.csv",
        "selection_csv": "tables/selection.csv",
        "original_nodes_csv": "graphs/original_nodes.csv",
        "original_edges_csv": "graphs/original_edges.csv",
        "backbone_nodes_csv": "graphs/backbone_nodes.csv",
        "backbone_edges_csv": "graphs/backbone_edges.csv",
        "backbone_graphml": "graphs/backbone.graphml",
        "original_annotated_graphml": "graphs/original_annotated.graphml",
        "backbone_gexf": "graphs/backbone.gexf",
        "original_annotated_gexf": "graphs/original_annotated.gexf",
    }
    _write_json(destination / files["subject_json"], result.to_dict())
    _write_json(destination / files["pipeline_json"], result.pipeline_config)
    _write_json(destination / files["network_metadata_json"], result.network_metadata)
    temporal_config = _temporal_aggregation_config(result)
    if temporal_config is not None:
        temporal_path = "temporal_aggregation.json"
        _write_json(destination / temporal_path, temporal_config)
        files["temporal_aggregation_json"] = temporal_path
    _write_csv(tables_dir / "method_statistics.csv", result.statistics)
    _write_csv(tables_dir / "selection.csv", _selection_table(result))
    _write_csv(graphs_dir / "original_nodes.csv", _node_table(result.original_graph))
    _write_csv(graphs_dir / "original_edges.csv", _edge_table(result.original_graph))
    _write_csv(graphs_dir / "backbone_nodes.csv", _node_table(result.graph))
    _write_csv(graphs_dir / "backbone_edges.csv", _edge_table(result.graph))
    _write_graph_exports(graphs_dir, result)
    return files


def _temporal_aggregation_config(
    result: BackboneResult,
) -> Mapping[str, object] | None:
    aggregation = result.network_metadata.get("temporal_aggregation")
    if not isinstance(aggregation, Mapping):
        return None
    config = aggregation.get("config")
    return config if isinstance(config, Mapping) else None


def _write_comparison(
    destination: Path,
    comparison: Comparison,
) -> dict[str, str]:
    tables_dir = destination / "tables"
    pipelines_dir = destination / "pipelines"
    results_dir = destination / "results"
    tables_dir.mkdir()
    pipelines_dir.mkdir()
    results_dir.mkdir()

    files = {
        "subject_json": "comparison.json",
        "single_metrics_csv": "tables/single_metrics.csv",
        "pairwise_metrics_csv": "tables/pairwise_metrics.csv",
        "spearman_csv": "tables/spearman.csv",
    }
    _write_json(destination / files["subject_json"], _comparison_payload(comparison))
    _write_csv(tables_dir / "single_metrics.csv", comparison.table())
    _write_csv(tables_dir / "pairwise_metrics.csv", comparison.pairwise())
    _write_csv(tables_dir / "spearman.csv", comparison.spearman())

    name_map = _safe_name_map(comparison.results)
    for result_name, result in comparison.results.items():
        safe_name = name_map[result_name]
        pipeline_path = pipelines_dir / f"{safe_name}.json"
        result_path = results_dir / f"{safe_name}.json"
        _write_json(pipeline_path, result.pipeline_config)
        _write_json(result_path, result.to_dict())
        files[f"pipeline_{safe_name}_json"] = _relative(destination, pipeline_path)
        files[f"result_{safe_name}_json"] = _relative(destination, result_path)
    return files


def _write_sweep_result(
    destination: Path,
    sweep_result: SweepResult,
) -> dict[str, str]:
    tables_dir = destination / "tables"
    pipelines_dir = destination / "pipelines"
    results_dir = destination / "results"
    tables_dir.mkdir()
    pipelines_dir.mkdir()
    results_dir.mkdir()

    files = {
        "subject_json": "sweep.json",
        "runs_csv": "tables/runs.csv",
        "metrics_csv": "tables/metrics.csv",
        "failures_csv": "tables/failures.csv",
        "pipeline_index_json": "pipelines/index.json",
    }
    _write_json(destination / files["subject_json"], sweep_result.to_dict())
    _write_csv(tables_dir / "runs.csv", sweep_result.runs)
    _write_csv(tables_dir / "metrics.csv", sweep_result.table())
    _write_csv(tables_dir / "failures.csv", sweep_result.failures)

    pipeline_index = _sweep_pipeline_index(sweep_result.runs)
    _write_json(destination / files["pipeline_index_json"], pipeline_index)
    for entry in pipeline_index:
        if not isinstance(entry, Mapping):
            continue
        safe_name = str(entry["file_stem"])
        pipeline_path = pipelines_dir / f"{safe_name}.json"
        _write_json(pipeline_path, entry["pipeline"])
        files[f"pipeline_{safe_name}_json"] = _relative(destination, pipeline_path)

    name_map = _safe_name_map(sweep_result.results)
    for result_name, result in sweep_result.results.items():
        safe_name = name_map[result_name]
        result_path = results_dir / f"{safe_name}.json"
        _write_json(result_path, result.to_dict())
        files[f"result_{safe_name}_json"] = _relative(destination, result_path)
    return files


def _comparison_payload(comparison: Comparison) -> dict[str, object]:
    return {
        "result_names": list(comparison.results),
        "results": {
            name: result.to_dict() for name, result in comparison.results.items()
        },
        "pipelines": {
            name: dict(result.pipeline_config)
            for name, result in comparison.results.items()
        },
    }


def _sweep_pipeline_index(runs: pd.DataFrame) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    if runs.empty:
        return entries
    names = _safe_names([str(value) for value in runs["pipeline_name"].tolist()])
    for index, row in runs.reset_index(drop=True).iterrows():
        pipeline_config = Pipeline(
            method_name=str(row["method"]),
            method_parameters=_mapping_cell(row["method_parameters"]),
            filter_name=str(row["filter"]),
            filter_parameters=_mapping_cell(row["filter_parameters"]),
        ).to_dict()
        entries.append(
            {
                "run_id": int(row["run_id"]),
                "pipeline_name": str(row["pipeline_name"]),
                "file_stem": names[index],
                "status": str(row["status"]),
                "pipeline": pipeline_config,
            }
        )
    return entries


def _mapping_cell(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _selection_table(result: BackboneResult) -> pd.DataFrame:
    id_column = "edge_id" if result.selection.target == "edge" else "node_id"
    selected_ids = set(result.selection.selected_ids)
    rejected_ids = set(result.selection.rejected_ids)
    rows = [
        {
            id_column: identifier,
            "selected": identifier in selected_ids,
            "status": "selected" if identifier in selected_ids else "rejected",
        }
        for identifier in sorted(selected_ids.union(rejected_ids))
    ]
    return pd.DataFrame(rows, columns=[id_column, "selected", "status"])


def _node_table(graph: nx.Graph) -> pd.DataFrame:
    attribute_names = sorted(
        {str(key) for _, attributes in graph.nodes(data=True) for key in attributes}
    )
    rows = []
    for node, attributes in sorted(
        graph.nodes(data=True),
        key=lambda item: repr(item[0]),
    ):
        row = {"node": _csv_cell(node)}
        row.update({name: _csv_cell(attributes.get(name)) for name in attribute_names})
        rows.append(row)
    return pd.DataFrame(rows, columns=["node", *attribute_names])


def _edge_table(graph: nx.Graph) -> pd.DataFrame:
    attribute_names = sorted(
        {str(key) for _, _, attributes in graph.edges(data=True) for key in attributes}
    )
    rows = []
    for source, target, attributes in sorted(
        graph.edges(data=True),
        key=lambda item: (repr(item[0]), repr(item[1])),
    ):
        row = {
            "source": _csv_cell(source),
            "target": _csv_cell(target),
        }
        row.update({name: _csv_cell(attributes.get(name)) for name in attribute_names})
        rows.append(row)
    return pd.DataFrame(rows, columns=["source", "target", *attribute_names])


def _write_graph_exports(graphs_dir: Path, result: BackboneResult) -> None:
    original = _annotated_original_graph(result)
    backbone = _annotated_backbone_graph(result)
    _write_graphml(graphs_dir / "original_annotated.graphml", original)
    _write_graphml(graphs_dir / "backbone.graphml", backbone)
    _write_gexf(graphs_dir / "original_annotated.gexf", original)
    _write_gexf(graphs_dir / "backbone.gexf", backbone)


def _annotated_original_graph(result: BackboneResult) -> nx.Graph:
    graph = _graph_copy_for_export(result.original_graph)
    _annotate_graph(graph, result)
    return graph


def _annotated_backbone_graph(result: BackboneResult) -> nx.Graph:
    graph = _graph_copy_for_export(result.graph)
    _annotate_graph(graph, result, backbone_only=True)
    return graph


def _annotate_graph(
    graph: nx.Graph,
    result: BackboneResult,
    *,
    backbone_only: bool = False,
) -> None:
    prefix = _method_prefix(result)
    target_column = f"{prefix}_target"
    if result.selection.target == "edge":
        selected_edges = _selected_edge_keys(result)
        statistics_by_edge = _edge_statistic_attributes(result, prefix)
        for source, target in graph.edges:
            edge_key = _edge_key(
                source,
                target,
                directed=graph.is_directed(),
            )
            selected = edge_key in selected_edges or backbone_only
            role = "backbone" if selected else "rejected"
            color = BACKBONE_COLOR if selected else REJECTED_COLOR
            graph.edges[source, target].update(
                _required_target_statistics(
                    statistics_by_edge,
                    edge_key,
                    target_description=f"edge ({source!r}, {target!r})",
                )
            )
            graph.edges[source, target][f"{prefix}_selected"] = int(selected)
            graph.edges[source, target][f"{prefix}_role"] = role
            graph.edges[source, target][f"{prefix}_color"] = color
            graph.edges[source, target][target_column] = "edge"
            graph.edges[source, target]["viz"] = _edge_viz(color, selected=selected)
        return

    selected_nodes = _selected_nodes(result)
    statistics_by_node = _node_statistic_attributes(result, prefix)
    for node in graph.nodes:
        selected = node in selected_nodes or backbone_only
        role = "backbone" if selected else "rejected"
        color = BACKBONE_COLOR if selected else REJECTED_COLOR
        graph.nodes[node].update(
            _required_target_statistics(
                statistics_by_node,
                node,
                target_description=f"node {node!r}",
            )
        )
        graph.nodes[node][f"{prefix}_selected"] = int(selected)
        graph.nodes[node][f"{prefix}_role"] = role
        graph.nodes[node][f"{prefix}_color"] = color
        graph.nodes[node][target_column] = "node"
        graph.nodes[node]["viz"] = _node_viz(color, selected=selected)


def _edge_statistic_attributes(
    result: BackboneResult,
    prefix: str,
) -> dict[tuple[object, object], dict[str, object]]:
    columns = _statistic_attribute_columns(result, prefix)
    attributes: dict[tuple[object, object], dict[str, object]] = {}
    for row in result.statistics.to_dict(orient="records"):
        edge_key = _edge_key(
            row["source"],
            row["target"],
            directed=result.original_graph.is_directed(),
        )
        attributes[edge_key] = _row_statistic_attributes(row, columns)
    return attributes


def _node_statistic_attributes(
    result: BackboneResult,
    prefix: str,
) -> dict[object, dict[str, object]]:
    columns = _statistic_attribute_columns(result, prefix)
    return {
        row["node"]: _row_statistic_attributes(row, columns)
        for row in result.statistics.to_dict(orient="records")
    }


def _statistic_attribute_columns(
    result: BackboneResult,
    prefix: str,
) -> list[tuple[object, str]]:
    columns = [
        column
        for column in result.statistics.columns
        if str(column) not in _STATISTIC_IDENTITY_COLUMNS
    ]
    safe_names = _safe_names([str(column) for column in columns])
    return [
        (column, f"{prefix}_{safe_name}")
        for column, safe_name in zip(columns, safe_names, strict=True)
    ]


def _row_statistic_attributes(
    row: Mapping[object, object],
    columns: list[tuple[object, str]],
) -> dict[str, object]:
    attributes: dict[str, object] = {}
    for column, attribute_name in columns:
        value = _graph_statistic_attribute_value(row[column])
        if value is not _MISSING_GRAPH_ATTRIBUTE:
            attributes[attribute_name] = value
    return attributes


def _graph_statistic_attribute_value(value: object) -> object:
    if value is None:
        return _MISSING_GRAPH_ATTRIBUTE
    try:
        if bool(pd.isna(value)):
            return _MISSING_GRAPH_ATTRIBUTE
    except (TypeError, ValueError):
        pass
    return _graph_attribute_value(value)


def _required_target_statistics(
    statistics: Mapping[_Target, dict[str, object]],
    target: _Target,
    *,
    target_description: str,
) -> dict[str, object]:
    try:
        return statistics[target]
    except KeyError as exc:
        raise ValidationError(
            f"Method statistics do not contain {target_description}; "
            "the graph export cannot attach computed scores."
        ) from exc


def _selected_edge_keys(result: BackboneResult) -> set[tuple[object, object]]:
    selected_ids = set(result.selection.selected_ids)
    selected_rows = result.statistics[result.statistics["edge_id"].isin(selected_ids)]
    return {
        _edge_key(
            row["source"],
            row["target"],
            directed=result.original_graph.is_directed(),
        )
        for row in selected_rows.to_dict(orient="records")
    }


def _selected_nodes(result: BackboneResult) -> set[object]:
    selected_ids = set(result.selection.selected_ids)
    selected_rows = result.statistics[result.statistics["node_id"].isin(selected_ids)]
    return {row["node"] for row in selected_rows.to_dict(orient="records")}


def _method_prefix(result: BackboneResult) -> str:
    method_name = _safe_file_stem(result.method_result.method_name)
    return f"netbone_{method_name}_{_pipeline_config_hash(result)}"


def _pipeline_config_hash(result: BackboneResult) -> str:
    payload = {
        "method": result.pipeline_config.get("method"),
        "filter": result.pipeline_config.get("filter"),
    }
    encoded = json.dumps(
        json_value(payload),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.blake2s(encoded, digest_size=4).hexdigest()


def _edge_key(
    source: object,
    target: object,
    *,
    directed: bool,
) -> tuple[object, object]:
    if directed:
        return (source, target)
    endpoints = sorted((source, target), key=repr)
    return (endpoints[0], endpoints[1])


def _graph_copy_for_export(graph: nx.Graph) -> nx.Graph:
    exported = graph.__class__()
    exported.graph.update(
        {
            str(key): _graph_attribute_value(value)
            for key, value in graph.graph.items()
            if _graph_attribute_value(value) != ""
        }
    )
    for node, attributes in graph.nodes(data=True):
        exported.add_node(
            node,
            **{
                str(key): _graph_attribute_value(value)
                for key, value in attributes.items()
                if str(key) != "viz"
            },
        )
    for source, target, attributes in graph.edges(data=True):
        exported.add_edge(
            source,
            target,
            **{
                str(key): _graph_attribute_value(value)
                for key, value in attributes.items()
                if str(key) != "viz"
            },
        )
    return exported


def _write_graphml(path: Path, graph: nx.Graph) -> None:
    _warn_on_text_label_collisions(path, graph)
    graphml_graph = _strip_viz_attributes(graph)
    _restore_graph_defaults(graphml_graph)
    try:
        nx.write_graphml(graphml_graph, path)
    except OSError as exc:
        raise ValidationError(
            f"Experiment GraphML file could not be written: {path}."
        ) from exc


def _warn_on_text_label_collisions(path: Path, graph: nx.Graph) -> None:
    """Warn when distinct node ids share one text label in GraphML or GEXF."""

    seen: dict[str, object] = {}
    for node in graph.nodes:
        text = str(node)
        if text in seen and seen[text] != node:
            warnings.warn(
                f"Nodes {seen[text]!r} and {node!r} are both written as {text!r} "
                f"in {path.name}; the exported graph merges them and cannot be "
                "reloaded faithfully. Relabel the nodes to distinct strings, or "
                "use the CSV tables in the bundle.",
                UserWarning,
                stacklevel=3,
            )
            return
        seen[text] = node


def _restore_graph_defaults(graph: nx.Graph) -> None:
    for name in ("node_default", "edge_default"):
        value = graph.graph.get(name)
        if not isinstance(value, str):
            continue
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, Mapping):
            graph.graph[name] = dict(decoded)


def _write_gexf(path: Path, graph: nx.Graph) -> None:
    _restore_graph_defaults(graph)
    try:
        nx.write_gexf(graph, path)
    except OSError as exc:
        raise ValidationError(
            f"Experiment GEXF file could not be written: {path}."
        ) from exc


def _strip_viz_attributes(graph: nx.Graph) -> nx.Graph:
    stripped = graph.copy()
    for _, attributes in stripped.nodes(data=True):
        attributes.pop("viz", None)
    for _, _, attributes in stripped.edges(data=True):
        attributes.pop("viz", None)
    return stripped


def _graph_attribute_value(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    if isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, Mapping | list | tuple):
        return json.dumps(json_value(value), sort_keys=True, separators=(",", ":"))
    return str(value)


def _node_viz(color: str, *, selected: bool) -> dict[str, object]:
    return {
        "color": _hex_color(color),
        "size": 18.0 if selected else 9.0,
    }


def _edge_viz(color: str, *, selected: bool) -> dict[str, object]:
    return {
        "color": _hex_color(color),
        "thickness": 2.5 if selected else 0.7,
    }


def _hex_color(color: str) -> dict[str, int]:
    normalized = color.lstrip("#")
    return {
        "r": int(normalized[0:2], 16),
        "g": int(normalized[2:4], 16),
        "b": int(normalized[4:6], 16),
    }


def _write_json(path: Path, payload: object) -> None:
    try:
        path.write_text(
            json.dumps(json_value(payload), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    except OSError as exc:
        raise ValidationError(
            f"Experiment JSON file could not be written: {path}."
        ) from exc


def _write_csv(path: Path, table: pd.DataFrame) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        table.apply(lambda column: column.map(_csv_cell)).to_csv(
            path,
            index=False,
            lineterminator="\n",
        )
    except OSError as exc:
        raise ValidationError(
            f"Experiment CSV file could not be written: {path}."
        ) from exc


def _csv_cell(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    if isinstance(value, Mapping | list | tuple):
        return json.dumps(json_value(value), sort_keys=True, separators=(",", ":"))
    try:
        if bool(pd.isna(value)):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, bool | int | float | str):
        return value
    return str(value)


def _subject_type(subject: ExperimentSubject) -> str:
    if isinstance(subject, BackboneResult):
        return "backbone_result"
    if isinstance(subject, Comparison):
        return "comparison"
    return "sweep_result"


def _safe_name_map(values: Mapping[str, object]) -> dict[str, str]:
    names = list(values)
    safe_names = _safe_names(names)
    return dict(zip(names, safe_names, strict=True))


def _safe_names(values: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    names: list[str] = []
    for value in values:
        base = _safe_file_stem(value)
        count = counts.get(base, 0) + 1
        counts[base] = count
        names.append(base if count == 1 else f"{base}_{count}")
    return names


def _safe_file_stem(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z]+", "_", value).strip("_").lower()
    return cleaned or "item"


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()
