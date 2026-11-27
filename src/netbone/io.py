"""File input helpers."""

from __future__ import annotations

import csv
import math
import warnings
from collections.abc import Hashable
from pathlib import Path
from typing import TypeAlias
from xml.etree.ElementTree import ParseError

import networkx as nx
import pandas as pd

from netbone.exceptions import CompatibilityError, ValidationError
from netbone.network import Network, normalize_edgelist_graph, normalize_loaded_graph
from netbone.temporal.model import EVENT_COLUMNS, TemporalNetwork

TemporalTime: TypeAlias = int | float | pd.Timestamp

# Markers pandas would read as missing. Node id columns ignore them so labels
# such as "NA" (Namibia) or "None" stay ordinary node ids.
_MISSING_VALUE_MARKERS = (
    "",
    "#N/A",
    "#N/A N/A",
    "#NA",
    "-1.#IND",
    "-1.#QNAN",
    "-NaN",
    "-nan",
    "1.#IND",
    "1.#QNAN",
    "<NA>",
    "N/A",
    "NA",
    "NULL",
    "NaN",
    "None",
    "n/a",
    "nan",
    "null",
)


def _read_table(
    path: Path,
    *,
    delimiter: str,
    id_columns: tuple[str, ...],
    value_columns: tuple[str, ...],
) -> pd.DataFrame:
    """Read a delimited table keeping node ids exactly as written."""

    _check_row_widths(path, delimiter=delimiter)
    with warnings.catch_warnings():
        # Extra trailing empty fields are already known to be empty here.
        warnings.simplefilter("ignore", pd.errors.ParserWarning)
        return pd.read_csv(
            path,
            delimiter=delimiter,
            dtype={column: str for column in id_columns},
            keep_default_na=False,
            na_values={
                column: list(_MISSING_VALUE_MARKERS) for column in value_columns
            },
            skipinitialspace=True,
            # Never promote the first column to an index when rows run long.
            index_col=False,
        )


def _check_row_widths(path: Path, *, delimiter: str) -> None:
    """Reject rows with more values than the header, allowing trailing empties.

    Spreadsheet exports often end every row with a delimiter, which is harmless.
    A non-empty extra value means the columns do not line up with the header.
    """

    if len(delimiter) != 1:
        return
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        reader = csv.reader(handle, delimiter=delimiter, skipinitialspace=True)
        header = next(reader, None)
        if header is None:
            return
        width = len(header)
        row_number = 1
        for row in reader:
            if not row:
                continue
            row_number += 1
            extra = [value for value in row[width:] if value.strip()]
            if extra:
                raise ValidationError(
                    f"Row {row_number} of {path.name} has {len(row)} values but the "
                    f"header has {width} columns. Check the delimiter, or add a "
                    "header for the extra column."
                )


def _node_id_columns(
    table: pd.DataFrame, source: str, target: str
) -> tuple[list[Hashable], list[Hashable]]:
    """Convert source and target ids together so both use the same id type."""

    combined = _node_id_values(pd.concat([table[source], table[target]]))
    return combined[: len(table)], combined[len(table) :]


def _node_id_values(values: pd.Series) -> list[Hashable]:
    """Return node ids, converting to numbers only when no label would change.

    A column of plain integers such as ``1, 2, 10`` becomes Python ints. Labels
    with leading zeros, signs, decimals or text stay strings, so ``007`` and
    ``7`` remain different nodes.
    """

    texts = ["" if pd.isna(value) else str(value).strip() for value in values]
    present = [text for text in texts if text]
    if present and all(_is_canonical_integer(text) for text in present):
        return [int(text) if text else "" for text in texts]
    return list(texts)


def _is_canonical_integer(text: str) -> bool:
    try:
        return str(int(text)) == text
    except ValueError:
        return False


def from_edgelist(
    path: str | Path,
    *,
    source: str = "source",
    target: str = "target",
    weight: str | None = "weight",
    delimiter: str = ",",
    context: str | None = None,
    directed: bool = False,
) -> Network:
    """Load a CSV or delimiter-separated edge list into a `Network`.

    Args:
        path: File path to read.
        source: Column containing source node ids.
        target: Column containing target node ids.
        weight: Optional column containing numeric edge weights. When provided,
            values are stored on edges as the canonical `weight` attribute.
        delimiter: Field delimiter, defaulting to comma.
        context: Optional user-supplied context retained in result metadata.
        directed: Whether source-to-target order defines directed arcs. When
            false, reversed rows are duplicate undirected edges.

    Raises:
        ValidationError: If required columns are missing, ids are missing, edge
            weights are invalid, or duplicate simple-graph edges are present.
    """

    edge_path = Path(path)
    try:
        table = _read_table(
            edge_path,
            delimiter=delimiter,
            id_columns=(source, target),
            value_columns=() if weight is None else (weight,),
        )
    except FileNotFoundError as exc:
        raise ValidationError(f"Edge-list file does not exist: {edge_path}.") from exc
    except pd.errors.EmptyDataError as exc:
        raise ValidationError(f"Edge-list file is empty: {edge_path}.") from exc

    required_columns = [source, target]
    if weight is not None:
        required_columns.append(weight)

    missing_columns = [column for column in required_columns if column not in table]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValidationError(
            f"Edge-list file {edge_path} is missing required column(s): {missing}."
        )

    if not isinstance(directed, bool):
        raise ValidationError("from_edgelist parameter 'directed' must be a boolean.")

    graph = nx.DiGraph() if directed else nx.Graph()
    seen_edges: set[tuple[Hashable, Hashable]] = set()
    source_ids, target_ids = _node_id_columns(table, source, target)

    for position, (_, row) in enumerate(table.iterrows()):
        row_number = position + 2
        source_value = source_ids[position]
        target_value = target_ids[position]
        if source_value == "" or target_value == "":
            raise ValidationError(
                f"Edge-list row {row_number} has a missing source or target id."
            )
        if source_value == target_value:
            raise CompatibilityError(
                f"Edge-list row {row_number} is a self-loop on node "
                f"{source_value!r}. Self-loops are not supported; remove the row "
                "or load the data as a temporal event list, which drops them."
            )

        edge_attributes: dict[str, object] = {}
        if weight is not None:
            weight_value = row[weight]
            if pd.isna(weight_value):
                raise ValidationError(
                    f"Edge-list row {row_number} has a missing weight value."
                )
            if isinstance(weight_value, bool) or pd.api.types.is_bool(weight_value):
                raise ValidationError(
                    f"Edge-list row {row_number} has a boolean weight "
                    f"{str(weight_value).lower()!r} in column {weight!r}. Use "
                    "numbers, or pass weight=None for an unweighted network."
                )
            try:
                numeric_weight = float(weight_value)
            except (TypeError, ValueError) as exc:
                raise ValidationError(
                    f"Edge-list row {row_number} has a non-numeric weight "
                    f"value in column {weight!r}."
                ) from exc
            if not math.isfinite(numeric_weight):
                raise ValidationError(
                    f"Edge-list row {row_number} has a non-finite weight value "
                    f"in column {weight!r}."
                )
            edge_attributes["weight"] = numeric_weight

        first, second = (
            (source_value, target_value)
            if directed
            else sorted((source_value, target_value), key=repr)
        )
        edge_key: tuple[Hashable, Hashable] = (first, second)
        if edge_key in seen_edges:
            raise ValidationError(
                f"Duplicate simple-graph edge found in edge-list row {row_number}."
            )
        seen_edges.add(edge_key)
        graph.add_edge(source_value, target_value, **edge_attributes)

    metadata = (
        {
            "edge_weight_original_column": weight,
            "canonical_weight_attribute": "weight",
        }
        if weight is not None
        else {}
    )
    return normalize_edgelist_graph(
        graph,
        context=context,
        source_path=edge_path,
        metadata=metadata,
    )


def from_graphml(
    path: str | Path,
    *,
    context: str | None = None,
) -> Network:
    """Load a GraphML file into a validated `Network`.

    Args:
        path: GraphML file path to read.
        context: Optional user-supplied context retained in result metadata.

    Raises:
        ValidationError: If the file does not exist or cannot be parsed.
        CompatibilityError: If the loaded graph type is unsupported by this
            release.
    """

    graphml_path = Path(path)
    try:
        graph = nx.read_graphml(graphml_path)
    except FileNotFoundError as exc:
        raise ValidationError(f"GraphML file does not exist: {graphml_path}.") from exc
    except (OSError, ParseError, nx.NetworkXException) as exc:
        raise ValidationError(
            f"GraphML file could not be read: {graphml_path}."
        ) from exc

    return normalize_loaded_graph(
        graph,
        context=context,
        source_path=graphml_path,
        metadata={"format": "graphml"},
    )


def from_temporal_edgelist(
    path: str | Path,
    *,
    source: str = "source",
    target: str = "target",
    time: str = "time",
    event_weight: str | None = None,
    delimiter: str = ",",
    context: str | None = None,
    directed: bool = False,
) -> TemporalNetwork:
    """Load repeated temporal interactions from a delimiter-separated file.

    Each row represents one interaction occurrence and is retained for later
    aggregation. By default, reversed rows belong to the same undirected pair.
    With ``directed=True``, source-to-target order defines an arc and reciprocal
    events are aggregated separately. Self-interactions are removed while their
    node labels remain part of the temporal network.

    Args:
        path: Temporal event-list file path.
        source: Column containing source node ids.
        target: Column containing target node ids.
        time: Column containing numeric times or datetime values.
        event_weight: Optional numeric non-negative event magnitude column.
            Omit it to give every event magnitude `1.0`.
        delimiter: Field delimiter, defaulting to comma.
        context: Optional user context retained on aggregated networks.
        directed: Whether source-to-target order defines directed temporal arcs.

    Raises:
        ValidationError: If required columns or event values are invalid.
    """

    event_path = Path(path)
    try:
        table = _read_table(
            event_path,
            delimiter=delimiter,
            id_columns=(source, target),
            value_columns=(time,) if event_weight is None else (time, event_weight),
        )
    except FileNotFoundError as exc:
        raise ValidationError(
            f"Temporal event-list file does not exist: {event_path}."
        ) from exc
    except pd.errors.EmptyDataError as exc:
        raise ValidationError(
            f"Temporal event-list file is empty: {event_path}."
        ) from exc

    required_columns = [source, target, time]
    if event_weight is not None:
        required_columns.append(event_weight)
    missing_columns = [column for column in required_columns if column not in table]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValidationError(
            f"Temporal event-list file {event_path} is missing required "
            f"column(s): {missing}."
        )
    if table.empty:
        raise ValidationError(
            f"Temporal event-list file contains no event rows: {event_path}."
        )
    if not isinstance(directed, bool):
        raise ValidationError(
            "from_temporal_edgelist parameter 'directed' must be a boolean."
        )

    times, time_kind = _temporal_times(table[time], path=event_path, column=time)
    event_weights = _temporal_event_weights(
        table[event_weight] if event_weight is not None else None,
        path=event_path,
        column=event_weight,
        row_count=len(table),
    )
    nodes: list[Hashable] = []
    seen_nodes: set[Hashable] = set()
    records: list[dict[str, object]] = []
    self_interaction_count = 0
    source_ids, target_ids = _node_id_columns(table, source, target)
    for position in range(len(table)):
        row_number = position + 2
        source_value = source_ids[position]
        target_value = target_ids[position]
        if source_value == "" or target_value == "":
            raise ValidationError(
                f"Temporal event-list row {row_number} has a missing source or "
                "target id."
            )
        for value, label in ((source_value, "source"), (target_value, "target")):
            try:
                hash(value)
            except TypeError as exc:
                raise ValidationError(
                    f"Temporal event-list row {row_number} has an unhashable "
                    f"{label} id."
                ) from exc
            if value not in seen_nodes:
                seen_nodes.add(value)
                nodes.append(value)
        if source_value == target_value:
            self_interaction_count += 1
            continue
        records.append(
            {
                "source": source_value,
                "target": target_value,
                "time": times[position],
                "event_weight": event_weights[position],
            }
        )

    if not records:
        raise ValidationError(
            "Temporal event-list contains no non-self interaction events after "
            "self-interactions are removed."
        )
    if self_interaction_count:
        warnings.warn(
            f"Removed {self_interaction_count} temporal self-interaction(s).",
            UserWarning,
            stacklevel=2,
        )
    events = pd.DataFrame.from_records(records, columns=EVENT_COLUMNS)
    metadata = {
        "format": "temporal_edgelist",
        "temporal_source_column": source,
        "temporal_target_column": target,
        "temporal_time_column": time,
        "temporal_event_weight_column": event_weight,
        "temporal_delimiter": delimiter,
        "temporal_source_path": str(event_path),
        "temporal_directed": directed,
        "time_kind": time_kind,
        "input_event_count": len(table),
        "retained_event_count": len(events),
        "self_interaction_count": self_interaction_count,
    }
    retained_times = [record["time"] for record in records]
    observed_start, observed_end = _temporal_bounds(retained_times)
    return TemporalNetwork(
        events=events,
        nodes=tuple(nodes),
        directed=directed,
        time_kind=time_kind,
        observed_start=observed_start,
        observed_end=observed_end,
        context=context,
        source=str(event_path),
        metadata=metadata,
    )


def _temporal_times(
    values: pd.Series,
    *,
    path: Path,
    column: str,
) -> tuple[list[TemporalTime], str]:
    missing = values.isna()
    if missing.any():
        position = int(missing.to_numpy().nonzero()[0][0])
        raise ValidationError(
            f"Temporal event-list row {position + 2} has a missing time value "
            f"in column {column!r}."
        )

    if pd.api.types.is_bool_dtype(values.dtype):
        raise ValidationError(
            f"Temporal event-list row 2 has a boolean time value in column "
            f"{column!r}; use numeric snapshot ids or datetimes."
        )

    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.notna().all():
        parsed_numeric: list[TemporalTime] = []
        for position, value in enumerate(numeric):
            result = float(value)
            if not math.isfinite(result):
                raise ValidationError(
                    f"Temporal event-list row {position + 2} has a non-finite "
                    f"time value in column {column!r}."
                )
            parsed_numeric.append(int(result) if result.is_integer() else result)
        return parsed_numeric, "numeric"

    parsed_datetimes: list[TemporalTime] = []
    for position, value in enumerate(values):
        if pd.api.types.is_bool(value):
            raise ValidationError(
                f"Temporal event-list row {position + 2} has a boolean time "
                f"value in column {column!r}; use numeric snapshot ids or "
                "datetimes."
            )
        try:
            parsed = pd.to_datetime(value, errors="raise", utc=True)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValidationError(
                f"Temporal event-list row {position + 2} has an invalid numeric "
                f"or datetime value in column {column!r} from {path}."
            ) from exc
        if not isinstance(parsed, pd.Timestamp):
            raise ValidationError(
                f"Temporal event-list row {position + 2} has an invalid datetime "
                f"value in column {column!r}."
            )
        parsed_datetimes.append(parsed)
    return parsed_datetimes, "datetime"


def _temporal_bounds(values: list[TemporalTime]) -> tuple[TemporalTime, TemporalTime]:
    first = values[0]
    if isinstance(first, pd.Timestamp):
        timestamps = [value for value in values if isinstance(value, pd.Timestamp)]
        if len(timestamps) != len(values):
            raise ValidationError("Temporal event times must use one consistent type.")
        return min(timestamps), max(timestamps)
    numeric_values = [
        float(value)
        for value in values
        if isinstance(value, int | float) and not isinstance(value, bool)
    ]
    if len(numeric_values) != len(values):
        raise ValidationError("Temporal event times must use one consistent type.")
    minimum = min(numeric_values)
    maximum = max(numeric_values)
    return (
        int(minimum) if minimum.is_integer() else minimum,
        int(maximum) if maximum.is_integer() else maximum,
    )


def _temporal_event_weights(
    values: pd.Series | None,
    *,
    path: Path,
    column: str | None,
    row_count: int,
) -> list[float]:
    if values is None:
        return [1.0] * row_count
    weights: list[float] = []
    for position, value in enumerate(values):
        if pd.isna(value):
            raise ValidationError(
                f"Temporal event-list row {position + 2} has a missing event "
                f"weight in column {column!r}."
            )
        if pd.api.types.is_bool(value):
            raise ValidationError(
                f"Temporal event-list row {position + 2} has a boolean event "
                f"weight in column {column!r}; weights must be numeric."
            )
        try:
            weight = float(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                f"Temporal event-list row {position + 2} has a non-numeric "
                f"event weight in column {column!r} from {path}."
            ) from exc
        if not math.isfinite(weight) or weight < 0.0:
            raise ValidationError(
                f"Temporal event-list row {position + 2} event weight in column "
                f"{column!r} must be finite and non-negative."
            )
        weights.append(weight)
    return weights
