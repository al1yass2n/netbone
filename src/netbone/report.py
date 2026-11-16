"""Deterministic report generation for Netbone results."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import TypeAlias

import pandas as pd

from netbone._json import JsonValue, json_mapping, json_records, json_value
from netbone.compare.comparison import Comparison
from netbone.exceptions import ConfigurationError, ValidationError
from netbone.filters.registry import describe_filter
from netbone.results import BackboneResult
from netbone.sweep import SweepResult

ReportSubject: TypeAlias = BackboneResult | Comparison | SweepResult


@dataclass(frozen=True)
class Report:
    """A deterministic, JSON-compatible report payload.

    Reports are generated entirely from computed values, metadata, warnings,
    and user-provided context already present in Netbone objects. They do not
    require or call an LLM provider.
    """

    subject_type: str
    title: str
    summary: Mapping[str, object]
    sections: Mapping[str, object]
    warnings: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    reproducibility: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Freeze shallow mapping and tuple fields."""

        object.__setattr__(self, "summary", MappingProxyType(dict(self.summary)))
        object.__setattr__(self, "sections", MappingProxyType(dict(self.sections)))
        object.__setattr__(
            self, "reproducibility", MappingProxyType(dict(self.reproducibility))
        )
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(self, "limitations", tuple(self.limitations))

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-compatible report representation."""

        return {
            "subject_type": self.subject_type,
            "title": self.title,
            "summary": json_mapping(self.summary),
            "sections": json_mapping(self.sections),
            "warnings": [_json_string(warning) for warning in self.warnings],
            "limitations": [
                _json_string(limitation) for limitation in self.limitations
            ],
            "reproducibility": json_mapping(self.reproducibility),
        }

    def to_markdown(self) -> str:
        """Return a deterministic Markdown rendering of this report."""

        payload = self.to_dict()
        lines = [f"# {self.title}", "", f"- Subject type: {self.subject_type}", ""]
        _append_mapping_section(lines, "Summary", payload["summary"])

        sections = payload["sections"]
        if isinstance(sections, dict):
            for section_name, section_value in sections.items():
                _append_value_section(lines, _title(section_name), section_value)

        _append_list_section(lines, "Warnings", payload["warnings"])
        _append_list_section(lines, "Limitations", payload["limitations"])
        _append_mapping_section(
            lines,
            "Reproducibility",
            payload["reproducibility"],
        )
        return "\n".join(lines).rstrip() + "\n"

    def write_markdown(self, path: str | Path, *, overwrite: bool = True) -> Path:
        """Write this report as a UTF-8 Markdown file and return its path.

        Args:
            path: Destination Markdown file path.
            overwrite: Whether an existing destination file may be replaced.

        Raises:
            ValidationError: If the destination is a directory, already exists
                while `overwrite=False`, or cannot be written.
        """

        destination = Path(path)
        if destination.exists() and destination.is_dir():
            raise ValidationError(
                f"Report Markdown path points to a directory: {destination}."
            )
        if destination.exists() and not overwrite:
            raise ValidationError(
                f"Report Markdown file already exists: {destination}."
            )
        if destination.parent.exists() and not destination.parent.is_dir():
            raise ValidationError(
                f"Report Markdown parent path is not a directory: {destination.parent}."
            )

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open(
                "w" if overwrite else "x",
                encoding="utf-8",
                newline="\n",
            ) as file:
                file.write(self.to_markdown())
        except FileExistsError as exc:
            raise ValidationError(
                f"Report Markdown file already exists: {destination}."
            ) from exc
        except OSError as exc:
            raise ValidationError(
                f"Report Markdown file could not be written: {destination}."
            ) from exc
        return destination.resolve()


def report(subject: ReportSubject, *, title: str | None = None) -> Report:
    """Create a deterministic report for a result, comparison, or sweep.

    Args:
        subject: `BackboneResult`, `Comparison`, or `SweepResult` to report.
        title: Optional report title.

    Raises:
        ConfigurationError: If the subject type is unsupported.
    """

    if isinstance(subject, BackboneResult):
        return _result_report(subject, title=title)
    if isinstance(subject, Comparison):
        return _comparison_report(subject, title=title)
    if isinstance(subject, SweepResult):
        return _sweep_report(subject, title=title)
    raise ConfigurationError(
        "report() requires a BackboneResult, Comparison, or SweepResult."
    )


def _result_report(result: BackboneResult, *, title: str | None) -> Report:
    method_result = result.method_result
    filter_name = result.selection.parameters.get("strategy")
    summary = result.summary()
    method_section = {
        "name": method_result.method_name,
        "display_name": method_result.metadata.get("display_name"),
        "target": method_result.target,
        "output_type": method_result.output_type,
        "primary_statistic": method_result.primary_statistic,
        "preferred_direction": method_result.preferred_direction,
        "parameters": dict(method_result.parameters),
        "reference": method_result.metadata.get("reference"),
        "doi": method_result.metadata.get("doi"),
    }
    filter_section = {
        "name": filter_name,
        "display_name": _filter_display_name(filter_name),
        "statistic": result.selection.statistic,
        "parameters": dict(result.selection.parameters),
    }
    sections = {
        "method": method_section,
        "filter": filter_section,
        "selection": result.selection.summary(),
        "statistics": method_result.to_dict()["statistics"],
        "pipeline": dict(result.pipeline_config),
    }
    reproducibility = {
        "pipeline": dict(result.pipeline_config),
        "method_parameters": dict(method_result.parameters),
        "filter_parameters": dict(result.selection.parameters),
        "has_context": result.context is not None,
    }
    return Report(
        subject_type="backbone_result",
        title=title or "Netbone Backbone Report",
        summary=summary,
        sections=sections,
        warnings=result.warnings,
        limitations=(
            "Report text is deterministic and limited to computed values, "
            "registered metadata, warnings, and user-provided context.",
        ),
        reproducibility=reproducibility,
    )


def _comparison_report(comparison: Comparison, *, title: str | None) -> Report:
    single_metrics = comparison.table()
    pairwise_metrics = comparison.pairwise()
    metric_statuses = _status_counts(single_metrics, pairwise_metrics)
    summary = {
        "result_count": len(comparison.results),
        "results": list(comparison.results),
        "single_metric_rows": len(single_metrics),
        "pairwise_metric_rows": len(pairwise_metrics),
        "ok_rows": metric_statuses.get("ok", 0),
        "invalid_rows": metric_statuses.get("invalid", 0),
        "undefined_rows": metric_statuses.get("undefined", 0),
    }
    sections = {
        "results": [
            _comparison_result_row(name, result)
            for name, result in comparison.results.items()
        ],
        "single_metrics": _records(single_metrics),
        "pairwise_metrics": _records(pairwise_metrics),
    }
    reproducibility = {
        "result_names": list(comparison.results),
        "pipelines": {
            name: dict(result.pipeline_config)
            for name, result in comparison.results.items()
        },
    }
    return Report(
        subject_type="comparison",
        title=title or "Netbone Comparison Report",
        summary=summary,
        sections=sections,
        warnings=_unique(
            warning
            for result in comparison.results.values()
            for warning in result.warnings
        ),
        limitations=(
            "Invalid and undefined comparison rows are retained with explicit "
            "status and explanation values.",
        ),
        reproducibility=reproducibility,
    )


def _sweep_report(sweep_result: SweepResult, *, title: str | None) -> Report:
    runs = sweep_result.runs
    metrics = sweep_result.table()
    failures = sweep_result.failures
    summary = {
        "result_count": len(sweep_result.results),
        "run_count": len(runs),
        "failed_run_count": len(failures),
        "metric_rows": len(metrics),
        "score_cache_hits": sweep_result.score_cache_hits,
        "score_cache_misses": sweep_result.score_cache_misses,
    }
    sections = {
        "runs": _records(runs),
        "metrics": _records(metrics),
        "failures": _records(failures),
    }
    limitations = [
        "Failed sweep configurations are retained as failed rows instead of "
        "being omitted."
    ]
    if len(failures) == 0:
        limitations = [
            "This sweep report contains no failed configurations.",
        ]
    return Report(
        subject_type="sweep_result",
        title=title or "Netbone Sweep Report",
        summary=summary,
        sections=sections,
        warnings=_table_messages(runs, "warning"),
        limitations=tuple(limitations),
        reproducibility={
            "score_cache_hits": sweep_result.score_cache_hits,
            "score_cache_misses": sweep_result.score_cache_misses,
            "successful_pipelines": {
                name: dict(result.pipeline_config)
                for name, result in sweep_result.results.items()
            },
        },
    )


def _comparison_result_row(name: str, result: BackboneResult) -> dict[str, object]:
    summary = result.summary()
    return {
        "name": name,
        "method": summary["method"],
        "filter": summary["filter"],
        "original_edges": summary["original_edge_count"],
        "backbone_edges": summary["backbone_edge_count"],
        "edge_fraction": summary["edge_fraction"],
    }


def _filter_display_name(filter_name: object) -> object:
    if not isinstance(filter_name, str) or filter_name == "custom":
        return None
    try:
        return describe_filter(filter_name).get("display_name")
    except ConfigurationError:
        return None


def _status_counts(*tables: pd.DataFrame) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in tables:
        if "status" not in table:
            continue
        for status, count in table["status"].value_counts().items():
            counts[str(status)] = counts.get(str(status), 0) + int(count)
    return counts


def _table_messages(table: pd.DataFrame, column: str) -> tuple[str, ...]:
    if column not in table:
        return ()
    return _unique(str(value) for value in table[column].tolist() if str(value))


def _unique(values: Iterable[object]) -> tuple[str, ...]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in seen:
            seen.add(text)
            unique_values.append(text)
    return tuple(unique_values)


def _records(table: pd.DataFrame) -> list[JsonValue]:
    return json_records(table)


def _json_string(value: object) -> str:
    return str(value)


def _append_mapping_section(
    lines: list[str],
    title: str,
    mapping: JsonValue,
) -> None:
    lines.append(f"## {title}")
    lines.append("")
    if not isinstance(mapping, dict) or not mapping:
        lines.append("_None._")
        lines.append("")
        return
    for key, value in mapping.items():
        lines.append(f"- **{_title(key)}:** {_markdown_value(value)}")
    lines.append("")


def _append_value_section(
    lines: list[str],
    title: str,
    value: JsonValue,
) -> None:
    if isinstance(value, dict):
        _append_mapping_section(lines, title, value)
        return
    if isinstance(value, list):
        if value and all(isinstance(item, dict) for item in value):
            lines.append(f"## {title}")
            lines.append("")
            lines.extend(_markdown_table(value))
            lines.append("")
            return
        _append_list_section(lines, title, value)
        return
    lines.append(f"## {title}")
    lines.append("")
    lines.append(_markdown_value(value))
    lines.append("")


def _append_list_section(
    lines: list[str],
    title: str,
    values: JsonValue,
) -> None:
    lines.append(f"## {title}")
    lines.append("")
    if not isinstance(values, list) or not values:
        lines.append("_None._")
        lines.append("")
        return
    for value in values:
        lines.append(f"- {_markdown_value(value)}")
    lines.append("")


def _markdown_table(records: list[JsonValue]) -> list[str]:
    dict_records = [record for record in records if isinstance(record, dict)]
    if not dict_records:
        return ["_None._"]
    columns = list(dict_records[0])
    for record in dict_records[1:]:
        for key in record:
            if key not in columns:
                columns.append(key)
    lines = [
        "| " + " | ".join(_title(column) for column in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for record in dict_records:
        lines.append(
            "| "
            + " | ".join(
                _escape_table(_markdown_value(record.get(column))) for column in columns
            )
            + " |"
        )
    return lines


def _markdown_value(value: JsonValue) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float | str):
        return str(value)
    return json.dumps(json_value(value), sort_keys=True, separators=(",", ":"))


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _title(value: str) -> str:
    return value.replace("_", " ").title()
