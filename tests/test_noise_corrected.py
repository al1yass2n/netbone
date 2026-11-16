from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb
from netbone.exceptions import ValidationError

# Outputs from the unmodified Python 3 archive on the authors' project page.
# For the undirected case, the reference receives both orientations per edge.
DIRECTED_REFERENCE = [
    ("a", "b", 20, 0.2925170068027211, 0.016902287285074095),
    ("b", "a", 3, 0.5475113122171945, 0.0234035229395957),
    ("a", "c", 6, 0.1362126245847176, 0.04594363628088745),
    ("b", "c", 2, 0.39024390243902435, 0.1058063873766504),
    ("c", "a", 7, 0.33222036727879795, 0.00937143624644642),
    ("c", "d", 13, 0.4805194805194805, 0.030693301365328496),
    ("d", "b", 4, 0.22580645161290322, 0.046517725926210014),
    ("d", "c", 2, 0.31034482758620685, 0.13412351629598313),
]
UNDIRECTED_REFERENCE = [
    ("a", "b", 20, 0.4539579967689823, 0.019378021890890437),
    ("a", "c", 6, -0.005524861878453019, 0.10478455886634849),
    ("b", "c", 2, -0.5041322314049588, 0.3169093582165067),
    ("c", "d", 13, 0.5324165029469548, 0.01695598489675529),
    ("b", "d", 4, -0.10224438902743142, 0.16351749293168222),
]


@pytest.mark.parametrize("directed", [False, True])
def test_noise_corrected_matches_author_scores_and_threshold(directed: bool) -> None:
    reference = DIRECTED_REFERENCE if directed else UNDIRECTED_REFERENCE
    graph = nx.DiGraph() if directed else nx.Graph()
    graph.add_weighted_edges_from(
        [(source, target, weight) for source, target, weight, _, _ in reference],
        weight="count",
    )
    original = graph.copy()
    pipeline = nb.pipeline().score("noise_corrected", weight="count").filter("default")
    result = nb.Pipeline.from_dict(pipeline.to_dict()).run(graph)

    def edge_key(source: str, target: str) -> tuple[str, ...]:
        return (source, target) if directed else tuple(sorted((source, target)))

    expected = {
        edge_key(source, target): (lift, deviation)
        for source, target, _, lift, deviation in reference
    }
    assert result.method_result.primary_statistic == "noise_corrected_z"
    for row in result.statistics.to_dict(orient="records"):
        lift, deviation = expected[edge_key(row["source"], row["target"])]
        assert row["noise_corrected_score"] == pytest.approx(lift, abs=1e-13)
        assert row["noise_corrected_stddev"] == pytest.approx(deviation, abs=1e-13)
        assert row["noise_corrected_z"] == pytest.approx(lift / deviation, rel=1e-12)

    default_kept = set(expected) if directed else {("a", "b"), ("c", "d")}
    assert {edge_key(*edge) for edge in result.graph.edges} == default_kept
    strict = pipeline.filter("threshold", value=2.32, operator="greater").run(graph)
    stricter_kept = default_kept - ({("d", "c")} if directed else set())
    assert {edge_key(*edge) for edge in strict.graph.edges} == stricter_kept
    assert nx.utils.graphs_equal(graph, original)


@pytest.mark.parametrize("weight", [0, -1, 2.5])
def test_noise_corrected_requires_positive_integer_counts(weight: float) -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=weight)
    with pytest.raises(ValidationError, match="positive|integer count"):
        nb.score(graph, method="noise_corrected")


def test_noise_corrected_reports_degenerate_margins_and_keeps_no_arcs() -> None:
    graph = nx.DiGraph()
    graph.add_weighted_edges_from([("a", "b", 3), ("a", "c", 8)])
    result = nb.pipeline().score("noise_corrected").filter("default").run(graph)
    assert result.statistics["noise_corrected_stddev"].isna().all()
    assert result.statistics["noise_corrected_z"].tolist() == [0.0, 0.0]
    assert not result.selection.selected_ids
    assert any(
        "could not estimate uncertainty for 2 edge(s)" in warning
        for warning in result.warnings
    )
