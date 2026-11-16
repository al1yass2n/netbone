from __future__ import annotations

import networkx as nx
import pandas as pd
import pytest

import netbone as nb
from netbone.network import EDGE_ID_ATTR, NODE_ORIGINAL_ATTR


def test_from_graph_assigns_internal_ids_and_preserves_original_ids() -> None:
    graph = nx.Graph()
    graph.add_node("a", color="red")
    graph.add_edge("a", "b", weight=3)

    network = nb.from_graph(graph, context="example")

    assert network.node_id_to_original == {0: "a", 1: "b"}
    assert network.original_to_node_id == {"a": 0, "b": 1}
    assert network.edge_id_to_endpoints == {0: (0, 1)}
    assert network.graph.nodes[0][NODE_ORIGINAL_ATTR] == "a"
    assert network.context == "example"
    assert network.metadata == {}

    original = network.to_original_graph()
    assert sorted(original.nodes(data=True)) == [("a", {"color": "red"}), ("b", {})]
    assert original.edges["a", "b"]["weight"] == 3


def test_from_graph_does_not_mutate_input_graph() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1)

    nb.from_graph(graph)

    assert EDGE_ID_ATTR not in graph.edges["a", "b"]
    assert NODE_ORIGINAL_ATTR not in graph.nodes["a"]


def test_from_graph_preserves_directed_arcs_and_reciprocal_edges() -> None:
    directed = nx.DiGraph()
    directed.add_edge("a", "b", weight=1)
    directed.add_edge("b", "a", weight=2)

    network = nb.from_graph(directed)

    assert network.directed is True
    assert network.edge_id_to_endpoints == {0: (0, 1), 1: (1, 0)}
    restored = network.to_original_graph()
    assert isinstance(restored, nx.DiGraph)
    assert restored.edges["a", "b"]["weight"] == 1
    assert restored.edges["b", "a"]["weight"] == 2


@pytest.mark.parametrize(
    ("merge", "expected"),
    [
        ("sum", 6.0),
        ("mean", 3.0),
        ("max", 4.0),
        ("min", 2.0),
    ],
)
def test_to_undirected_merges_reciprocal_weight_values(
    merge: str,
    expected: float,
) -> None:
    graph = nx.DiGraph(project="example")
    graph.add_node("a", group="one")
    graph.add_edge("a", "b", weight=4.0, kind="collaboration")
    graph.add_edge("b", "a", weight=2.0, kind="collaboration")
    graph.add_edge("b", "c", weight=3.0, kind="citation")
    network = nb.from_graph(graph, context="directed example")

    projected = nb.to_undirected(
        network,
        weight="weight",
        reciprocal_merge=merge,
    )

    restored = projected.to_original_graph()
    assert projected.directed is False
    assert projected.context == "directed example"
    assert restored.graph["project"] == "example"
    assert restored.nodes["a"]["group"] == "one"
    assert restored.edges["a", "b"] == {
        "weight": expected,
        "kind": "collaboration",
    }
    assert restored.edges["b", "c"] == {"weight": 3.0, "kind": "citation"}
    assert projected.metadata["direction_conversion"] == {
        "mode": "undirected",
        "weight_attribute": "weight",
        "reciprocal_merge": merge,
        "original_arc_count": 3,
        "undirected_edge_count": 2,
        "reciprocal_pair_count": 1,
        "one_way_edge_count": 1,
    }
    assert (
        "Arc direction is not represented" in projected.metadata["netbone_warnings"][0]
    )
    assert network.directed is True
    assert network.edge_count == 3


def test_to_undirected_preserves_conflicting_directional_attribute_provenance() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b", weight=1.0, year=2020, relationship="outbound")
    graph.add_edge("b", "a", weight=2.0, year=2021, relationship="inbound")

    projected = nb.to_undirected(
        graph,
        weight="weight",
        reciprocal_merge="sum",
    )

    attributes = projected.to_original_graph().edges["a", "b"]
    assert attributes["weight"] == 3.0
    assert "relationship" not in attributes
    assert "year" not in attributes
    provenance = attributes["netbone_directional_conflicts"]
    assert "outbound" in provenance
    assert "inbound" in provenance
    assert "relationship" in provenance
    assert "year" in provenance


def test_to_undirected_rejects_undirected_input_and_unknown_merge() -> None:
    with pytest.raises(nb.ValidationError, match="requires a directed"):
        nb.to_undirected(
            nx.Graph([("a", "b")]),
            weight=None,
            reciprocal_merge=None,
        )

    with pytest.raises(nb.ValidationError, match="reciprocal_merge"):
        nb.to_undirected(
            nx.DiGraph([("a", "b")]),
            weight="weight",
            reciprocal_merge="median",  # type: ignore[arg-type]
        )


def test_to_undirected_unweighted_projection_needs_no_merge_rule() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "a")

    projected = nb.to_undirected(
        graph,
        weight=None,
        reciprocal_merge=None,
    )

    assert projected.edge_count == 1
    assert projected.metadata["direction_conversion"]["weight_attribute"] is None
    assert projected.metadata["direction_conversion"]["reciprocal_merge"] is None


def test_from_graph_rejects_unsupported_multigraph_types() -> None:
    multigraph = nx.MultiGraph()
    multigraph.add_edge("a", "b")

    with pytest.raises(nb.CompatibilityError, match="Multigraphs"):
        nb.from_graph(multigraph)


def test_from_graph_rejects_reserved_internal_attributes() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", **{EDGE_ID_ATTR: 10})

    with pytest.raises(nb.ValidationError, match="reserved Netbone"):
        nb.from_graph(graph)


def test_from_edgelist_loads_csv_and_preserves_ids(tmp_path) -> None:
    path = tmp_path / "network.csv"
    pd.DataFrame(
        [
            {"source": "a", "target": "b", "weight": 2},
            {"source": "b", "target": "c", "weight": 3},
        ]
    ).to_csv(path, index=False)

    network = nb.from_edgelist(path, weight="weight")

    assert network.source == str(path)
    assert network.metadata == {
        "edge_weight_original_column": "weight",
        "canonical_weight_attribute": "weight",
    }
    assert network.node_id_to_original == {0: "a", 1: "b", 2: "c"}
    assert network.to_original_graph().edges["a", "b"]["weight"] == 2.0


def test_from_edgelist_canonicalizes_custom_weight_column(tmp_path) -> None:
    path = tmp_path / "network.csv"
    pd.DataFrame(
        [
            {"source": "a", "target": "b", "strength": 2},
            {"source": "b", "target": "c", "strength": 3},
        ]
    ).to_csv(path, index=False)

    network = nb.from_edgelist(path, weight="strength")

    assert network.weighted is True
    assert network.metadata == {
        "edge_weight_original_column": "strength",
        "canonical_weight_attribute": "weight",
    }
    assert network.to_original_graph().edges["a", "b"] == {"weight": 2.0}


def test_from_edgelist_can_load_explicitly_unweighted_csv(tmp_path) -> None:
    path = tmp_path / "network.csv"
    pd.DataFrame([{"source": "a", "target": "b"}]).to_csv(path, index=False)

    network = nb.from_edgelist(path, weight=None)

    assert network.weighted is False
    assert network.metadata == {}
    assert sorted(network.to_original_graph().edges()) == [("a", "b")]


def test_from_edgelist_reports_missing_columns(tmp_path) -> None:
    path = tmp_path / "network.csv"
    pd.DataFrame([{"source": "a", "target": "b"}]).to_csv(path, index=False)

    with pytest.raises(nb.ValidationError, match="missing required column"):
        nb.from_edgelist(path, weight="weight")


def test_from_edgelist_rejects_duplicate_undirected_edges(tmp_path) -> None:
    path = tmp_path / "network.csv"
    pd.DataFrame(
        [
            {"source": "a", "target": "b", "weight": 1},
            {"source": "b", "target": "a", "weight": 1},
        ]
    ).to_csv(path, index=False)

    with pytest.raises(nb.ValidationError, match="Duplicate simple-graph edge"):
        nb.from_edgelist(path)


def test_from_edgelist_can_load_reciprocal_directed_arcs(tmp_path) -> None:
    path = tmp_path / "directed.csv"
    pd.DataFrame(
        [
            {"source": "a", "target": "b", "weight": 1},
            {"source": "b", "target": "a", "weight": 2},
        ]
    ).to_csv(path, index=False)

    network = nb.from_edgelist(path, directed=True)

    assert network.directed is True
    assert network.to_original_graph().edges["a", "b"]["weight"] == 1.0
    assert network.to_original_graph().edges["b", "a"]["weight"] == 2.0


def test_from_graphml_loads_graph_and_uses_shared_validation(tmp_path) -> None:
    path = tmp_path / "network.graphml"
    graph = nx.Graph()
    graph.add_node("alice", color="red")
    graph.add_edge("alice", "bob", weight=2.0)
    nx.write_graphml(graph, path)

    network = nb.from_graphml(path, context="graphml example")

    assert network.source == str(path)
    assert network.context == "graphml example"
    assert network.metadata == {"format": "graphml"}
    assert network.node_id_to_original == {0: "alice", 1: "bob"}
    assert network.to_original_graph().nodes["alice"]["color"] == "red"
    assert network.to_original_graph().edges["alice", "bob"]["weight"] == 2.0


def test_from_graphml_reports_missing_file(tmp_path) -> None:
    path = tmp_path / "missing.graphml"

    with pytest.raises(nb.ValidationError, match="GraphML file does not exist"):
        nb.from_graphml(path)


def test_from_graphml_preserves_directed_graph_shape(tmp_path) -> None:
    path = tmp_path / "directed.graphml"
    graph = nx.DiGraph()
    graph.add_edge("a", "b", weight=1.0)
    graph.add_edge("b", "a", weight=2.0)
    nx.write_graphml(graph, path)

    network = nb.from_graphml(path)

    assert network.directed is True
    assert isinstance(network.to_original_graph(), nx.DiGraph)
    assert network.to_original_graph().number_of_edges() == 2
