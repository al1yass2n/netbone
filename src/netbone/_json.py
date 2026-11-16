"""Helpers for JSON-compatible result payloads."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import TypeAlias

import pandas as pd

JsonValue: TypeAlias = (
    None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
)


def json_mapping(mapping: Mapping[str, object]) -> dict[str, JsonValue]:
    """Return a JSON-compatible copy of a mapping."""

    return {str(key): json_value(value) for key, value in mapping.items()}


def json_records(table: pd.DataFrame) -> list[JsonValue]:
    """Return JSON-compatible records from a DataFrame."""

    return [json_mapping(row) for row in table.to_dict(orient="records")]


def json_value(value: object) -> JsonValue:
    """Return a JSON-compatible representation of one value."""

    if value is None or isinstance(value, bool | str):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Mapping):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [json_value(item) for item in value]
    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        return json_value(value.item())
    return str(value)
