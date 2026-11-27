from __future__ import annotations

import networkx as nx
import pytest

import netbone as nb


def test_public_exports_are_intentional() -> None:
    expected = {
        "BackboneResult",
        "CompatibilityError",
        "Comparison",
        "ConfigurationError",
        "MethodResult",
        "NetboneError",
        "Network",
        "Pipeline",
        "Report",
        "Selection",
        "Sweep",
        "SweepResult",
        "TemporalAggregationConfig",
        "TemporalNetwork",
        "UndefinedMetricError",
        "ValidationError",
        "__version__",
        "aggregate_temporal",
        "compare",
        "describe_filter",
        "describe_method",
        "describe_metric",
        "describe_temporal_weighting",
        "filter_scores",
        "from_edgelist",
        "from_graph",
        "from_graphml",
        "from_temporal_edgelist",
        "list_filters",
        "list_methods",
        "list_metrics",
        "list_temporal_weightings",
        "pipeline",
        "report",
        "score",
        "save_experiment",
        "sweep",
        "to_undirected",
    }

    assert set(nb.__all__) == expected


def test_functional_public_api_scores_and_filters_graph() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=2.0)
    graph.add_edge("b", "c", weight=1.0)

    method_result = nb.score(graph, method="edge_weight", weight="weight")
    result = nb.filter_scores(
        graph,
        method_result,
        strategy="threshold",
        value=2.0,
        operator="greater_equal",
    )

    assert sorted(result.graph.edges()) == [("a", "b")]
    assert result.statistics["score"].tolist() == [2.0, 1.0]


def test_public_discovery_api_lists_methods_and_filters() -> None:
    assert nb.list_methods() == (
        "disparity",
        "doubly_stochastic",
        "edge_betweenness",
        "edge_weight",
        "glanb",
        "gspar",
        "h_backbone",
        "lans",
        "link_prediction",
        "link_prediction_iforest",
        "link_salience",
        "marginal_likelihood",
        "maximum_spanning_forest",
        "multiple_linkage",
        "node_betweenness",
        "node_degree",
        "node_strength",
        "noise_corrected",
        "planar_maximally_filtered_graph",
        "primary_linkage",
    )
    assert nb.describe_method("doubly_stochastic")["default_filter"] == "threshold"
    assert nb.describe_method("doubly_stochastic")["default_epsilon_mode"] == (
        "relative"
    )
    assert nb.describe_method("doubly_stochastic")["epsilon_mode_options"] == (
        "absolute",
        "relative",
    )
    assert nb.describe_method("doubly_stochastic")["connected_tie_policy"] == (
        "stable_edge_id"
    )
    assert nb.describe_method("disparity")["default_filter"] == "significance"
    assert nb.describe_method("edge_betweenness")["default_filter"] == "fraction"
    assert nb.describe_method("glanb")["default_filter"] == "significance"
    assert nb.describe_method("glanb")["default_weight"] == "auto"
    assert nb.describe_method("gspar")["default_filter"] == "fraction"
    assert nb.describe_method("gspar")["neighborhood"] == "open"
    assert nb.describe_method("h_backbone")["default_filter"] == "threshold"
    assert nb.describe_method("lans")["default_filter"] == "significance"
    assert nb.describe_method("lans")["default_leaf_policy"] == "zero"
    assert nb.describe_method("link_prediction")["default_filter"] == "fraction"
    assert nb.describe_method("link_prediction")["default_weight"] == "auto"
    assert nb.describe_method("link_prediction")["default_weight_alpha"] == 1.0
    assert nb.describe_method("link_prediction")["default_distance_transform"] == (
        "inverse"
    )
    assert nb.describe_method("link_prediction")["distance_transform_options"] == (
        "identity",
        "inverse",
    )
    assert nb.describe_method("link_prediction")["requires_positive_weights"] is True
    assert nb.describe_method("link_prediction")["requires_fraction_direction"] is True
    assert nb.describe_method("link_prediction")["supports_directed"] is True
    assert nb.describe_method("link_prediction_iforest")["default_filter"] == (
        "fraction"
    )
    assert nb.describe_method("link_prediction_iforest")["preferred_direction"] == (
        "higher"
    )
    assert nb.describe_method("link_prediction_iforest")["optional_dependency"] == (
        "scikit-learn"
    )
    assert nb.describe_method("link_prediction_iforest")["doi"] == (
        "10.1007/978-3-031-92898-7_13"
    )
    assert (
        nb.describe_method("link_prediction_iforest")["selection_uses_contamination"]
        is False
    )
    assert nb.describe_method("link_prediction_iforest")["supports_directed"] is True
    assert nb.describe_method("link_salience")["default_filter"] == "threshold"
    assert nb.describe_method("marginal_likelihood")["default_filter"] == (
        "significance"
    )
    assert nb.describe_method("maximum_spanning_forest")["default_filter"] == (
        "threshold"
    )
    assert nb.describe_method("multiple_linkage")["default_filter"] == "threshold"
    assert nb.describe_method("node_degree")["target"] == "node"
    assert nb.describe_method("node_strength")["target"] == "node"
    assert nb.describe_method("node_betweenness")["target"] == "node"
    assert (
        nb.describe_method("planar_maximally_filtered_graph")["default_filter"]
        == "threshold"
    )
    assert nb.describe_method("primary_linkage")["default_filter"] == "threshold"
    assert nb.list_filters() == ("default", "fraction", "significance", "threshold")
    assert nb.describe_filter("fraction")["direction_options"] == ("higher", "lower")
    assert nb.describe_filter("fraction")["default_tie_policy"] == "include_all_ties"
    assert "edge_jaccard" in nb.list_metrics(scope="pairwise")
    assert nb.describe_metric("edge_retention")["scope"] == "single"
    assert nb.describe_metric("weakly_connected_component_count")["scope"] == ("single")
    assert nb.describe_metric("strongly_connected_component_count")["scope"] == (
        "single"
    )
    assert nb.list_temporal_weightings() == (
        "asf",
        "baseline",
        "persistent_exponential",
        "persistent_log_logistic",
        "persistent_weibull",
    )


@pytest.mark.parametrize("method_name", nb.list_methods())
def test_registered_methods_reject_unknown_parameters(method_name: str) -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1)

    with pytest.raises(nb.ConfigurationError, match="does not accept parameter"):
        nb.score(graph, method=method_name, unknown_parameter=True)


def test_registered_filters_reject_unknown_parameters() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1)
    method_result = nb.score(graph, method="edge_weight", weight="weight")

    for strategy, parameters in {
        "threshold": {
            "value": 1,
            "operator": "greater_equal",
            "unknown_parameter": True,
        },
        "fraction": {"fraction": 1.0, "unknown_parameter": True},
        "significance": {"alpha": 0.5, "unknown_parameter": True},
    }.items():
        with pytest.raises(nb.ConfigurationError, match="does not accept parameter"):
            nb.filter_scores(
                method_result=method_result,
                graph_or_network=graph,
                strategy=strategy,
                **parameters,
            )
