"""Score-alignment helpers for comparison metrics."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import networkx as nx
import pandas as pd

from netbone.exceptions import CompatibilityError

if TYPE_CHECKING:
    from netbone.results import BackboneResult, MethodResult


def same_original_topology(left: BackboneResult, right: BackboneResult) -> bool:
    """Return whether two results were extracted from the same graph topology."""

    return (
        left.original_graph.is_directed() == right.original_graph.is_directed()
        and set(left.original_graph.nodes()) == set(right.original_graph.nodes())
        and _canonical_edges(left.original_graph)
        == _canonical_edges(right.original_graph)
    )


def same_original_graph(left: BackboneResult, right: BackboneResult) -> bool:
    """Return whether two results were extracted from the same attributed graph."""

    return (
        same_original_topology(left, right)
        and left.original_graph.graph == right.original_graph.graph
        and _node_attributes(left.original_graph)
        == _node_attributes(right.original_graph)
        and _edge_attributes(left.original_graph)
        == _edge_attributes(right.original_graph)
    )


def _node_attributes(graph: nx.Graph) -> dict[object, dict[str, object]]:
    return {node: dict(attributes) for node, attributes in graph.nodes(data=True)}


def _edge_attributes(graph: nx.Graph) -> dict[object, dict[str, object]]:
    return {
        _edge_identity(graph, source, target): dict(attributes)
        for source, target, attributes in graph.edges(data=True)
    }


def _edge_identity(graph: nx.Graph, source: object, target: object) -> object:
    if graph.is_directed():
        return (source, target)
    return frozenset((source, target))


def score_incompatibility(left: BackboneResult, right: BackboneResult) -> str:
    """Return an explanation when two method result tables cannot be aligned."""

    if not same_original_graph(left, right):
        return "Score comparison requires the same attributed original graph."
    if left.method_result.target != right.method_result.target:
        return "Score comparison requires the same result target."
    return ""


def aligned_score_table(
    left_name: str,
    right_name: str,
    left: MethodResult,
    right: MethodResult,
    *,
    directed: bool = False,
) -> pd.DataFrame:
    """Return primary statistics aligned by graph identity with importance ranks."""

    aligned = (
        _aligned_edge_table(left, right, directed=directed)
        if left.target == "edge"
        else _aligned_node_table(left, right)
    )
    aligned.insert(0, "result_a", left_name)
    aligned.insert(1, "result_b", right_name)
    aligned.insert(2, "target", left.target)
    aligned.insert(3, "output_type_a", left.output_type)
    aligned.insert(4, "output_type_b", right.output_type)
    aligned.insert(5, "preferred_direction_a", left.preferred_direction)
    aligned.insert(6, "preferred_direction_b", right.preferred_direction)
    aligned["importance_rank_a"] = importance_rank(
        aligned["value_a"],
        preferred_direction=left.preferred_direction,
    )
    aligned["importance_rank_b"] = importance_rank(
        aligned["value_b"],
        preferred_direction=right.preferred_direction,
    )
    return aligned


def importance_rank(
    values: pd.Series,
    *,
    preferred_direction: str,
) -> pd.Series:
    """Return ranks where larger rank numbers mean more important."""

    if preferred_direction == "higher":
        return values.rank(method="average", ascending=True)
    if preferred_direction == "lower":
        return values.rank(method="average", ascending=False)
    raise CompatibilityError(
        "Score comparison requires preferred_direction to be 'higher' or 'lower'."
    )


def spearman(left_ranks: pd.Series, right_ranks: pd.Series) -> float | None:
    """Return correlation of aligned rank series, or None when undefined."""

    if len(left_ranks) < 2 or len(right_ranks) < 2:
        return None
    if left_ranks.nunique() < 2 or right_ranks.nunique() < 2:
        return None
    value = float(left_ranks.corr(right_ranks))
    if math.isnan(value):
        return None
    return value


def _canonical_edges(graph: nx.Graph) -> set[object]:
    return {_edge_identity(graph, source, target) for source, target in graph.edges()}


def _aligned_edge_table(
    left: MethodResult,
    right: MethodResult,
    *,
    directed: bool,
) -> pd.DataFrame:
    _validate_columns(left, ("edge_id", "source", "target"))
    _validate_columns(right, ("edge_id", "source", "target"))
    left_table = _edge_identity_table(left, suffix="a", directed=directed)
    right_table = _edge_identity_table(right, suffix="b", directed=directed)
    _validate_matching_identities(
        left_table["_edge_identity"],
        right_table["_edge_identity"],
        identity_name="edge identities",
    )
    aligned = left_table.merge(right_table, on="_edge_identity", how="inner")
    aligned.insert(0, "edge_key", aligned["_edge_identity"])
    return aligned.drop(columns=["_edge_identity"])


def _edge_identity_table(
    method_result: MethodResult,
    *,
    suffix: str,
    directed: bool,
) -> pd.DataFrame:
    edge_identities = [
        (source, target) if directed else frozenset((source, target))
        for source, target in zip(
            method_result.statistics["source"],
            method_result.statistics["target"],
            strict=True,
        )
    ]
    return pd.DataFrame(
        {
            "_edge_identity": edge_identities,
            f"edge_id_{suffix}": method_result.statistics["edge_id"],
            f"source_{suffix}": method_result.statistics["source"],
            f"target_{suffix}": method_result.statistics["target"],
            f"value_{suffix}": _numeric_primary_values(method_result),
        }
    )


def _aligned_node_table(left: MethodResult, right: MethodResult) -> pd.DataFrame:
    id_column = "node" if "node" in left.statistics.columns else "node_id"
    if id_column not in right.statistics.columns:
        id_column = "node_id"
    _validate_id_column(left, id_column)
    _validate_id_column(right, id_column)
    left_table = pd.DataFrame(
        {
            id_column: left.statistics[id_column],
            "value_a": _numeric_primary_values(left),
        }
    )
    right_table = pd.DataFrame(
        {
            id_column: right.statistics[id_column],
            "value_b": _numeric_primary_values(right),
        }
    )
    _validate_matching_identities(
        left_table[id_column],
        right_table[id_column],
        identity_name="node identities",
    )
    return left_table.merge(right_table, on=id_column, how="inner")


def _validate_columns(method_result: MethodResult, columns: tuple[str, ...]) -> None:
    missing = [
        column for column in columns if column not in method_result.statistics.columns
    ]
    if missing:
        missing_text = ", ".join(repr(column) for column in missing)
        raise CompatibilityError(
            f"Score comparison requires {missing_text} in method "
            f"{method_result.method_name!r} statistics."
        )


def _validate_id_column(method_result: MethodResult, id_column: str) -> None:
    if id_column not in method_result.statistics.columns:
        raise CompatibilityError(
            f"Score comparison requires {id_column!r} in method "
            f"{method_result.method_name!r} statistics."
        )


def _validate_matching_identities(
    left: pd.Series,
    right: pd.Series,
    *,
    identity_name: str,
) -> None:
    left_set = set(left.tolist())
    right_set = set(right.tolist())
    if len(left_set) != len(left) or len(right_set) != len(right):
        raise CompatibilityError(f"Score comparison requires unique {identity_name}.")
    if left_set != right_set:
        raise CompatibilityError(f"Score comparison requires matching {identity_name}.")


def _numeric_primary_values(method_result: MethodResult) -> pd.Series:
    raw_values = method_result.statistics[method_result.primary_statistic]
    if raw_values.map(lambda value: isinstance(value, bool)).any():
        raise CompatibilityError(
            "Score comparison requires finite numeric primary statistics."
        )
    values = pd.to_numeric(raw_values, errors="coerce")
    if values.isna().any() or not values.map(math.isfinite).all():
        raise CompatibilityError(
            "Score comparison requires finite numeric primary statistics."
        )
    return pd.Series(values, index=method_result.statistics.index, dtype=float)
