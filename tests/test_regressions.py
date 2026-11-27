"""Regression tests for issues found during exploratory testing."""

from __future__ import annotations

import json
import shutil
import threading
import urllib.error
import urllib.request
import warnings
from collections.abc import Iterator
from http.server import ThreadingHTTPServer
from pathlib import Path

import networkx as nx
import pytest

import netbone as nb
from netbone.webapp.bridge import preview_payload, run_pipeline_from_payload
from netbone.webapp.server import NetboneWebHandler


def _numbered_graph(edge_count: int) -> nx.Graph:
    graph = nx.gnm_random_graph(60, edge_count, seed=1)
    for index, (source, target) in enumerate(graph.edges()):
        graph[source][target]["weight"] = float(index + 1)
    return graph


@pytest.mark.parametrize(
    ("fraction", "expected"),
    [(0.07, 7), (0.14, 14), (0.28, 28), (0.29, 29), (0.57, 57), (0.1, 10)],
)
def test_fraction_count_ignores_floating_point_noise(
    fraction: float, expected: int
) -> None:
    result = (
        nb.pipeline()
        .score("edge_weight")
        .filter("fraction", fraction=fraction)
        .run(_numbered_graph(100))
    )

    assert result.selection.parameters["requested_count"] == expected
    assert result.graph.number_of_edges() == expected


def test_fraction_still_rounds_partial_counts_up() -> None:
    result = (
        nb.pipeline()
        .score("edge_weight")
        .filter("fraction", fraction=0.075)
        .run(_numbered_graph(100))
    )

    assert result.selection.parameters["requested_count"] == 8


def test_validation_messages_use_original_node_labels() -> None:
    graph = nx.Graph()
    graph.add_edge("x", "y", weight=1.0)
    graph.add_edge("y", "z", weight=-2.0)

    with pytest.raises(nb.ValidationError, match=r"edge \('y', 'z'\)"):
        nb.score(graph, "disparity")


def test_link_prediction_iforest_errors_name_the_method() -> None:
    pytest.importorskip("sklearn")
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=-1.0)
    graph.add_edge("b", "c", weight=1.0)

    with pytest.raises(nb.ValidationError, match="link_prediction_iforest scoring"):
        nb.score(graph, "link_prediction_iforest", similarities="shortest_path")


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_edgelist_keeps_na_like_labels_as_node_ids(tmp_path: Path) -> None:
    path = _write(
        tmp_path, "countries.csv", "source,target,weight\nNA,US,3\nUS,None,2\n"
    )

    graph = nb.from_edgelist(path).to_original_graph()

    assert set(graph.nodes) == {"NA", "US", "None"}


def test_edgelist_keeps_leading_zero_labels_distinct(tmp_path: Path) -> None:
    path = _write(tmp_path, "zeros.csv", "source,target,weight\n007,7,3\n7,8,2\n")

    graph = nb.from_edgelist(path).to_original_graph()

    assert set(graph.nodes) == {"007", "7", "8"}


def test_edgelist_converts_plain_integer_ids_to_python_ints(tmp_path: Path) -> None:
    path = _write(tmp_path, "ints.csv", "source,target,weight\n1,2,3\n2,10,2\n")

    graph = nb.from_edgelist(path).to_original_graph()

    assert set(graph.nodes) == {1, 2, 10}
    assert all(type(node) is int for node in graph.nodes)


def test_edgelist_accepts_spaces_after_delimiters(tmp_path: Path) -> None:
    path = _write(tmp_path, "spaced.csv", "source, target, weight\na, b, 3\nb, c, 2\n")

    graph = nb.from_edgelist(path).to_original_graph()

    assert sorted(graph.edges(data="weight")) == [("a", "b", 3.0), ("b", "c", 2.0)]


@pytest.mark.parametrize("value", ["inf", "-inf", "nan", ""])
def test_edgelist_rejects_non_finite_or_missing_weights(
    tmp_path: Path, value: str
) -> None:
    path = _write(tmp_path, "bad.csv", f"source,target,weight\na,b,{value}\nb,c,2\n")

    with pytest.raises(nb.ValidationError, match="row 2"):
        nb.from_edgelist(path)


def test_edgelist_self_loop_error_names_the_row(tmp_path: Path) -> None:
    path = _write(tmp_path, "loop.csv", "source,target,weight\na,b,1\nc,c,2\n")

    with pytest.raises(nb.CompatibilityError, match="row 3 is a self-loop"):
        nb.from_edgelist(path)


def test_temporal_edgelist_keeps_na_like_labels(tmp_path: Path) -> None:
    path = _write(tmp_path, "events.csv", "source,target,time\nNA,B,1\nB,C,2\n")

    events = nb.from_temporal_edgelist(path)

    assert "NA" in events.nodes


def test_temporal_datetime_rejects_numeric_evaluation_time(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "events.csv",
        "source,target,time\nA,B,2024-01-01\nB,C,2024-01-05\n",
    )
    events = nb.from_temporal_edgelist(path)

    with pytest.raises(nb.ValidationError, match="must be a datetime"):
        nb.aggregate_temporal(
            events, weighting="baseline", snapshot_size="1D", evaluation_time=5
        )


def test_marginal_likelihood_handles_huge_counts_without_overflow() -> None:
    graph = nx.karate_club_graph()
    for index, (source, target) in enumerate(graph.edges()):
        graph[source][target]["weight"] = 1e300 * (index + 1)

    try:
        nb.score(graph, "marginal_likelihood")
    except nb.ValidationError as exc:
        assert "too large" in str(exc)


@pytest.mark.parametrize("scale", [1e-6, 1e-3, 7.3, 1e3])
def test_multiple_linkage_selection_is_scale_invariant(scale: float) -> None:
    graph = nx.karate_club_graph()
    for index, (source, target) in enumerate(graph.edges()):
        graph[source][target]["weight"] = float((index * 7) % 11 + 1)
    scaled = graph.copy()
    for _, _, attributes in scaled.edges(data=True):
        attributes["weight"] *= scale

    base = nb.score(graph, "multiple_linkage").statistics
    rescaled = nb.score(scaled, "multiple_linkage").statistics

    assert (
        base["multiple_linkage_selected"].tolist()
        == rescaled["multiple_linkage_selected"].tolist()
    )


def _sweep() -> nb.SweepResult:
    return (
        nb.sweep(nx.karate_club_graph())
        .score("edge_weight")
        .filter("fraction")
        .vary_filter(fraction=[0.1, 0.5])
        .measure(["edge_retention"])
        .run()
    )


def test_sweep_bundles_are_byte_for_byte_reproducible(tmp_path: Path) -> None:
    first = nb.save_experiment(_sweep(), tmp_path / "first")
    second = nb.save_experiment(_sweep(), tmp_path / "second")

    for path in sorted(first.rglob("*")):
        if path.is_file():
            other = second / path.relative_to(first)
            assert path.read_bytes() == other.read_bytes(), path.name
    assert _sweep().runs["score_cache_key"].iloc[0].startswith("('edge_weight'")


def test_vary_method_rejects_a_list_of_methods() -> None:
    with pytest.raises(nb.ConfigurationError, match="takes one method name"):
        nb.sweep(nx.karate_club_graph()).filter("default").vary_method(
            ["disparity", "lans"]  # type: ignore[arg-type]
        )


def test_graphml_export_warns_when_labels_collide(tmp_path: Path) -> None:
    graph = nx.Graph()
    graph.add_edge(1, "1", weight=1.0)
    graph.add_edge("1", "a", weight=2.0)
    result = (
        nb.pipeline().score("edge_weight").filter("fraction", fraction=1.0).run(graph)
    )

    with pytest.warns(UserWarning, match="both written as '1'"):
        nb.save_experiment(result, tmp_path / "bundle")
    shutil.rmtree(tmp_path / "bundle")


def _csv_payload(csv_text: str) -> dict[str, object]:
    return {
        "csv_text": csv_text,
        "source": "source",
        "target": "target",
        "weight": "weight",
        "method": {"name": "edge_weight", "parameters": {"weight": "weight"}},
        "filter": {"name": "fraction", "parameters": {"fraction": 0.5}},
    }


def test_web_csv_accepts_spaces_after_commas_in_header() -> None:
    preview = preview_payload(
        _csv_payload("source, target, weight\na, b, 4\nb, c, 2\n")
    )

    assert preview["valid"] is True
    assert preview["edge_count"] == 2


@pytest.mark.parametrize("value", ["nan", "inf"])
def test_web_csv_rejects_non_finite_weights(value: str) -> None:
    preview = preview_payload(_csv_payload(f"source,target,weight\na,b,{value}\n"))

    assert preview["valid"] is False
    assert "finite" in str(preview["errors"])


def test_web_csv_self_loop_error_names_the_row() -> None:
    preview = preview_payload(_csv_payload("source,target,weight\na,b,1\nc,c,2\n"))

    assert preview["valid"] is False
    assert "row 3 is a self-loop" in str(preview["errors"])


def test_web_preview_reports_weight_sign() -> None:
    signs = {
        text: preview_payload(_csv_payload(text))["weight_sign"]
        for text in (
            "source,target,weight\na,b,1\nb,c,2\n",
            "source,target,weight\na,b,0\nb,c,2\n",
            "source,target,weight\na,b,-1\nb,c,2\n",
        )
    }

    assert list(signs.values()) == ["positive", "nonnegative", "mixed"]


def test_web_run_uses_labels_in_weight_errors() -> None:
    payload = _csv_payload("source,target,weight\nalpha,beta,-1\nbeta,gamma,2\n")
    payload["method"] = {"name": "disparity", "parameters": {"weight": "weight"}}

    with pytest.raises(nb.ValidationError, match=r"\('alpha', 'beta'\)"):
        run_pipeline_from_payload(payload)


@pytest.fixture
def server_url() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), NetboneWebHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _post(url: str, body: bytes, headers: dict[str, str]) -> tuple[int, str]:
    request = urllib.request.Request(url, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def test_server_rejects_non_utf8_body_as_bad_request(server_url: str) -> None:
    status, body = _post(f"{server_url}/api/run", b'{"csv_text":"\xff"}', {})

    assert status == 400
    assert "UTF-8" in json.loads(body)["message"]


def test_server_rejects_cross_origin_posts(server_url: str) -> None:
    body = json.dumps(_csv_payload("source,target,weight\na,b,1\n")).encode()

    status, _ = _post(f"{server_url}/api/run", body, {"Origin": "https://example.com"})
    same_origin_status, _ = _post(f"{server_url}/api/run", body, {"Origin": server_url})

    assert status == 403
    assert same_origin_status == 200


def test_server_rejects_rebound_host_names(server_url: str) -> None:
    request = urllib.request.Request(
        f"{server_url}/api/registry", headers={"Host": "attacker.example"}
    )

    with pytest.raises(urllib.error.HTTPError) as caught:
        urllib.request.urlopen(request, timeout=5)

    assert caught.value.code == 403


def test_server_answers_favicon_without_an_error(server_url: str) -> None:
    with urllib.request.urlopen(f"{server_url}/favicon.ico", timeout=5) as response:
        assert response.status == 204


def test_no_unexpected_warnings_from_auto_weight_on_plain_methods() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        nb.score(nx.karate_club_graph(), "disparity")


def test_edgelist_rejects_rows_with_extra_values(tmp_path: Path) -> None:
    path = tmp_path / "extra.csv"
    path.write_text("source,target,weight\na,b,1,9\nb,c,2,3\n")

    with pytest.raises(nb.ValidationError, match="Row 2 of extra.csv has 4 values"):
        nb.from_edgelist(path)


def test_edgelist_accepts_a_trailing_delimiter_on_every_row(tmp_path: Path) -> None:
    path = tmp_path / "trailing.csv"
    path.write_text("source,target,weight\na,b,1,\nb,c,2,\n")

    network = nb.from_edgelist(path)

    edges = {
        (network.node_id_to_original[u], network.node_id_to_original[v]): data["weight"]
        for u, v, data in network.graph.edges(data=True)
    }
    assert edges == {("a", "b"): 1.0, ("b", "c"): 2.0}


def test_edgelist_quoted_delimiters_are_not_extra_values(tmp_path: Path) -> None:
    path = tmp_path / "quoted.csv"
    path.write_text('source,target,weight\na, "b,c", 1\n')

    network = nb.from_edgelist(path)

    assert set(network.node_id_to_original.values()) == {"a", "b,c"}


def test_temporal_edgelist_accepts_trailing_delimiters(tmp_path: Path) -> None:
    path = tmp_path / "events.csv"
    path.write_text("source,target,time\na,b,1,\nb,c,2,\n")

    temporal = nb.from_temporal_edgelist(path)

    assert temporal.events["time"].tolist() == [1, 2]


def test_temporal_edgelist_rejects_rows_with_extra_values(tmp_path: Path) -> None:
    path = tmp_path / "events.csv"
    path.write_text("source,target,time\na,b,1,x\n")

    with pytest.raises(nb.ValidationError, match="has 4 values but the header"):
        nb.from_temporal_edgelist(path)


def test_web_csv_rejects_extra_values_and_accepts_trailing_delimiters() -> None:
    extra = preview_payload(_csv_payload("source,target,weight\na,b,1,9\n"))
    trailing = preview_payload(_csv_payload("source,target,weight\na,b,1,\nb,c,2,\n"))

    assert extra["valid"] is False
    assert "CSV row 2 has 4 values" in str(extra["errors"])
    assert trailing["valid"] is True
    assert trailing["edge_count"] == 2


def _raw_post(url: str, path: str, length: str, body: bytes) -> tuple[int, dict]:
    import socket
    from urllib.parse import urlparse

    parsed = urlparse(url)
    request = (
        f"POST {path} HTTP/1.1\r\nHost: {parsed.netloc}\r\n"
        f"Content-Type: application/json\r\nContent-Length: {length}\r\n"
        "Connection: close\r\n\r\n"
    ).encode() + body
    with socket.create_connection((parsed.hostname, parsed.port), timeout=5) as sock:
        sock.sendall(request)
        sock.shutdown(socket.SHUT_WR)
        chunks = []
        while chunk := sock.recv(65536):
            chunks.append(chunk)
    head, _, payload = b"".join(chunks).partition(b"\r\n\r\n")
    return int(head.split()[1]), json.loads(payload)


def test_server_rejects_bodies_over_the_upload_limit(server_url: str) -> None:
    status, payload = _raw_post(server_url, "/api/preview", "99999999999", b"{}")

    assert status == 413
    assert "larger than the 100 MB limit" in payload["message"]
    assert "--max-upload-mb" in payload["message"]


@pytest.mark.parametrize("length", ["-1", "abc"])
def test_server_rejects_bad_content_length_as_json(
    server_url: str, length: str
) -> None:
    status, payload = _raw_post(server_url, "/api/preview", length, b"{}")

    assert status == 400
    assert payload["status"] == "error"


def test_server_upload_limit_is_configurable() -> None:
    from netbone.webapp import server as web_server

    with pytest.raises(SystemExit):
        web_server.main(["--max-upload-mb", "0"])
    with pytest.raises(ValueError, match="positive"):
        web_server.run(max_upload_mb=0)


def test_edgelist_rejects_boolean_weights(tmp_path: Path) -> None:
    path = tmp_path / "flags.csv"
    path.write_text("source,target,weight\na,b,true\nb,c,false\n")

    with pytest.raises(nb.ValidationError, match="boolean weight 'true'"):
        nb.from_edgelist(path)


def test_to_undirected_auto_merges_full_weights_and_keeps_ints() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b", weight=3)
    graph.add_edge("b", "a", weight=1)
    graph.add_edge("b", "c", weight=2)

    projected = nb.to_undirected(graph)

    edges = projected.to_original_graph().edges
    assert edges["a", "b"]["weight"] == 4
    assert isinstance(edges["a", "b"]["weight"], int)
    assert projected.metadata["direction_conversion"]["reciprocal_merge"] == "sum"


def test_to_undirected_none_drops_weights_everywhere() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b", weight=3)
    graph.add_edge("b", "a", weight=1)
    graph.add_edge("b", "c", weight=2)

    projected = nb.to_undirected(graph, weight=None)

    assert all(
        "weight" not in data
        for *_, data in projected.to_original_graph().edges(data=True)
    )
    assert projected.metadata["direction_conversion"]["removed_weight_arc_count"] == 3
    assert nb.score(projected, method="edge_betweenness").parameters["weight"] is None


def test_to_undirected_auto_rejects_partial_weights() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b", weight=3)
    graph.add_edge("b", "c")

    with pytest.raises(nb.ValidationError, match="Only 1 of 2 arcs"):
        nb.to_undirected(graph)


def test_to_undirected_unweighted_auto_needs_no_merge_rule() -> None:
    projected = nb.to_undirected(nx.DiGraph([("a", "b"), ("b", "a")]))

    assert projected.metadata["direction_conversion"]["weight_attribute"] is None


@pytest.mark.parametrize("c", [50, 1000, 1e6])
def test_glanb_large_c_returns_the_exact_limit(c: float) -> None:
    graph = nx.karate_club_graph()

    statistics = nb.score(graph, method="glanb", c=c).statistics

    values = statistics["glanb_significance"]
    assert values.notna().all()
    assert values.between(0.0, 1.0).all()


def test_edgelist_rejects_a_header_only_file(tmp_path: Path) -> None:
    path = _write(tmp_path, "empty.csv", "source,target,weight\n")

    with pytest.raises(nb.ValidationError, match="has a header but no edges"):
        nb.from_edgelist(path)


def test_loaders_name_files_that_are_not_utf8(tmp_path: Path) -> None:
    path = tmp_path / "latin.csv"
    path.write_bytes("source,target,time\ncafé,b,1\n".encode("latin-1"))

    with pytest.raises(nb.ValidationError, match="latin.csv is not UTF-8 text"):
        nb.from_edgelist(path, weight=None)
    with pytest.raises(nb.ValidationError, match="latin.csv is not UTF-8 text"):
        nb.from_temporal_edgelist(path)


def test_loaders_reject_a_folder_path(tmp_path: Path) -> None:
    with pytest.raises(nb.ValidationError, match="is a folder, not a file"):
        nb.from_edgelist(tmp_path)
    with pytest.raises(nb.ValidationError, match="is a folder, not a file"):
        nb.from_temporal_edgelist(tmp_path)


def test_temporal_edgelist_names_mixed_numbers_and_dates(tmp_path: Path) -> None:
    path = _write(tmp_path, "events.csv", "source,target,time\nA,B,1\nB,C,2024-01-05\n")

    with pytest.raises(
        nb.ValidationError, match=r"mixes numbers \(row 2\) and dates \(row 3\)"
    ):
        nb.from_temporal_edgelist(path)


def test_temporal_edgelist_still_names_an_unreadable_time(tmp_path: Path) -> None:
    path = _write(tmp_path, "events.csv", "source,target,time\nA,B,1\nB,C,banana\n")

    with pytest.raises(nb.ValidationError, match="row 3 has an invalid"):
        nb.from_temporal_edgelist(path)


@pytest.mark.parametrize(
    ("text", "directed", "message"),
    [
        (
            "source,target\na,b\nb,a\n",
            False,
            r"row 3 \('b', 'a'\) repeats the edge between 'a' and 'b' from row 2\. "
            r"In an undirected file both orders are the same edge; pass directed=True",
        ),
        (
            "source,target\na,b\na,b\n",
            False,
            "row 3 repeats the edge between 'a' and 'b' from row 2. Merge repeated",
        ),
        (
            "source,target\na,b\na,b\n",
            True,
            "row 3 repeats the arc 'a' -> 'b' from row 2. Merge repeated",
        ),
    ],
)
def test_edgelist_duplicate_messages_explain_the_fix(
    tmp_path: Path, text: str, directed: bool, message: str
) -> None:
    path = _write(tmp_path, "edges.csv", text)

    with pytest.raises(nb.ValidationError, match=message):
        nb.from_edgelist(path, weight=None, directed=directed)


def test_edgelist_reversed_arcs_are_fine_when_directed(tmp_path: Path) -> None:
    path = _write(tmp_path, "edges.csv", "source,target\na,b\nb,a\n")

    assert nb.from_edgelist(path, weight=None, directed=True).edge_count == 2


def test_web_csv_duplicate_messages_point_at_the_directed_switch() -> None:
    reversed_preview = preview_payload(
        _csv_payload("source,target,weight\na,b,1\nb,a,2\n")
    )
    directed_payload = _csv_payload("source,target,weight\na,b,1\na,b,2\n")
    directed_payload["directed"] = True
    repeated_preview = preview_payload(directed_payload)
    loop_preview = preview_payload(_csv_payload("source,target,weight\nc,c,2\n"))

    assert "turn on Directed network to keep both directions" in str(
        reversed_preview["errors"]
    )
    assert "repeats the arc 'a' -> 'b' from row 2" in str(repeated_preview["errors"])
    assert "Self-loops are not supported; remove the row." in str(
        loop_preview["errors"]
    )


def test_server_answers_cross_origin_posts_with_json(server_url: str) -> None:
    body = json.dumps(_csv_payload("source,target,weight\na,b,1\n")).encode()

    status, text = _post(f"{server_url}/api/run", body, {"Origin": "https://x.test"})

    assert status == 403
    assert json.loads(text) == {
        "status": "error",
        "error": "Forbidden",
        "message": "Cross-origin requests to the Netbone web app are not allowed.",
    }


@pytest.mark.parametrize("path", ["/api/preview", "/api/export"])
def test_server_names_the_place_where_json_breaks(server_url: str, path: str) -> None:
    status, text = _post(f"{server_url}{path}", b'{"csv_text": "a,b"', {})

    payload = json.loads(text)
    assert status == 400
    assert payload["error"] == "ValidationError"
    assert payload["message"].startswith("Request body is not valid JSON (")
    assert "line 1, column" in payload["message"]


def test_method_display_names_match_the_documentation_titles() -> None:
    docs = Path(__file__).resolve().parents[1] / "docs" / "methods"
    for name in nb.list_methods():
        title = (docs / f"{name}.md").read_text(encoding="utf-8").splitlines()[0]
        assert nb.describe_method(name)["display_name"] == title.removeprefix("# ")
