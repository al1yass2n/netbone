from __future__ import annotations

import json
import threading
import urllib.request
from collections.abc import Iterable, Mapping
from http.server import ThreadingHTTPServer
from importlib import resources
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import networkx as nx
import pytest

import netbone as nb
from netbone.exceptions import ValidationError
from netbone.webapp.bridge import (
    comparison_payload,
    error_payload,
    experiment_export_payload,
    filter_payload,
    filter_preview_payload,
    graph_export_payload,
    preview_payload,
    registry_payload,
    result_export_payload,
    run_pipeline_from_payload,
    score_payload,
    sweep_payload,
    ui_schema_payload,
)
from netbone.webapp.server import NetboneWebHandler

WEIGHTED_CSV = """source,target,weight
alice,bob,4
bob,carol,2
alice,carol,1
"""

TEMPORAL_CSV = """source,target,time,magnitude
alice,bob,0,2
bob,alice,1,3
alice,carol,2,1
carol,dana,3,2
alice,bob,4,1
"""


def test_webapp_registry_payload_exposes_raw_methods_and_filters() -> None:
    payload = registry_payload()

    assert "edge_weight" in payload["methods"]
    assert "disparity" in payload["methods"]
    assert "threshold" in payload["filters"]
    assert "fraction" in payload["filters"]
    assert set(payload["temporal_weightings"]) == set(nb.list_temporal_weightings())


def test_webapp_ui_schema_exposes_registered_temporal_weightings() -> None:
    temporal = ui_schema_payload()["temporal"]
    weighting_names = {item["name"] for item in temporal["weightings"]}

    assert weighting_names == set(nb.list_temporal_weightings())
    assert temporal["default_weighting"] == "baseline"
    assert {"p", "q", "a"} == _control_names(temporal["controls"]["asf"])
    assert temporal["controls"]["baseline"] == []
    persistent = {
        item["name"]: item
        for item in temporal["weightings"]
        if item["name"].startswith("persistent_")
    }
    assert set(persistent) == {
        "persistent_exponential",
        "persistent_log_logistic",
        "persistent_weibull",
    }
    assert all(item["age_basis"] == "elapsed" for item in persistent.values())
    exponential_controls = temporal["controls"]["persistent_exponential"]
    assert _control_names(exponential_controls) == {
        "persistent_level",
        "decay_rate",
    }
    assert all(control["required"] is True for control in exponential_controls)
    assert all(control["default"] is None for control in exponential_controls)
    exponential_by_name = _controls_by_name(exponential_controls)
    assert exponential_by_name["persistent_level"]["step"] == 0.01
    assert exponential_by_name["persistent_level"]["min"] == 0.0
    assert exponential_by_name["persistent_level"]["max"] == 1.0
    assert exponential_by_name["decay_rate"]["step"] == 0.01
    weibull_by_name = _controls_by_name(temporal["controls"]["persistent_weibull"])
    assert weibull_by_name["scale"]["step"] == 0.1
    assert weibull_by_name["shape"]["step"] == 0.1
    assert _controls_by_name(temporal["controls"]["asf"])["q"]["step"] == 0.01


def test_webapp_numeric_controls_have_deterministic_spinner_steps() -> None:
    schema = ui_schema_payload()
    numeric_controls = [
        control
        for control in _all_controls(schema)
        if control.get("control") == "number"
    ]

    assert numeric_controls
    assert all(
        isinstance(control.get("step"), int | float)
        and not isinstance(control.get("step"), bool)
        and float(control["step"]) > 0.0
        for control in numeric_controls
    )
    method_controls = schema["controls"]["methods"]
    assert _controls_by_name(method_controls["glanb"])["c"]["step"] == 0.1
    assert (
        _controls_by_name(method_controls["link_prediction"])["epsilon"]["step"] == 0.01
    )
    assert (
        _controls_by_name(method_controls["doubly_stochastic"])["epsilon"]["step"]
        == 1e-5
    )


def test_webapp_ui_schema_represents_every_registered_method() -> None:
    schema = ui_schema_payload()
    method_names = [card["name"] for card in _method_cards(schema)]

    assert sorted(method_names) == sorted(nb.list_methods())
    assert schema["capabilities"]["graph_export"] is True
    assert schema["capabilities"]["graphml_import"] is True
    assert schema["capabilities"]["directed_to_undirected"] is True
    assert schema["capabilities"]["directed_temporal"] is True
    assert schema["capabilities"]["comparison"] is True
    assert {metric["name"] for metric in schema["comparison"]["single_metrics"]} == set(
        nb.list_metrics(scope="single")
    )
    assert {
        metric["name"] for metric in schema["comparison"]["pairwise_metrics"]
    } == set(nb.list_metrics(scope="pairwise"))
    data_controls = _controls_by_name(schema["controls"]["data"])
    assert _option_values(data_controls["direction_mode"]) == {
        "preserve",
        "undirected",
    }
    assert _option_values(data_controls["reciprocal_merge"]) == {
        "sum",
        "mean",
        "max",
        "min",
    }


def test_webapp_ui_schema_exposes_one_alphabetical_method_catalog() -> None:
    schema = ui_schema_payload()
    cards = _method_cards(schema)
    method_names = [card["name"] for card in cards]

    assert method_names == sorted(nb.list_methods())
    assert "groups" not in schema
    assert all("group" not in card for card in cards)
    assert all(card["meaning_template"] for card in cards)
    assert all(card["score_meaning_template"] for card in cards)


def test_webapp_ui_schema_exposes_overlapping_method_discovery_facets() -> None:
    schema = ui_schema_payload()
    cards = {card["name"]: card for card in _method_cards(schema)}
    approaches = {option["value"] for option in schema["method_filters"]["approaches"]}

    assert approaches == {
        "anomaly_detection",
        "direct_measure",
        "link_prediction",
        "shortest_paths",
        "statistical",
        "structural",
    }
    assert cards["disparity"]["approaches"] == ["statistical"]
    assert set(cards["glanb"]["approaches"]) == {"statistical", "shortest_paths"}
    assert set(cards["link_prediction_iforest"]["approaches"]) == {
        "link_prediction",
        "anomaly_detection",
    }
    assert all(card["approaches"] for card in cards.values())


def test_webapp_ui_schema_explains_method_output_values() -> None:
    cards = {card["name"]: card for card in _method_cards(ui_schema_payload())}

    assert cards["disparity"]["score_meaning_template"].startswith("Lower p-values")
    assert "connected {nodes}'" not in cards["disparity"]["score_meaning_template"]
    assert cards["edge_betweenness"]["score_meaning_template"].startswith(
        "Higher scores mean"
    )
    assert cards["h_backbone"]["score_interpretation"] == "binary_selection"
    assert "Values of 1" in cards["h_backbone"]["score_meaning_template"]
    assert "not a continuous ranking" in cards["h_backbone"]["score_meaning_template"]
    assert cards["multiple_linkage"]["score_interpretation"] == ("binary_selection")
    assert (
        "locally strongest set" in cards["multiple_linkage"]["score_meaning_template"]
    )
    assert cards["link_prediction_iforest"]["score_interpretation"] == "score"
    assert (
        "unusually high, low"
        in cards["link_prediction_iforest"]["score_meaning_template"]
    )


def test_webapp_ui_schema_exposes_iforest_similarity_choices() -> None:
    schema = ui_schema_payload()
    cards = {card["name"]: card for card in _method_cards(schema)}
    control_names = _control_names(
        schema["controls"]["methods"]["link_prediction_iforest"]
    )

    assert cards["link_prediction_iforest"]["label"] == (
        "Link Prediction Isolation Forest"
    )
    assert {
        "iforest_similarity_preferential_attachment",
        "iforest_similarity_shortest_path",
        "iforest_similarity_local_path",
        "n_estimators",
        "random_state",
    }.issubset(control_names)


def test_webapp_ui_schema_guides_pvalue_methods_to_significance() -> None:
    schema = ui_schema_payload()
    pvalue_methods = {
        name
        for name in nb.list_methods()
        if nb.describe_method(name)["output_type"] == "pvalue"
    }
    cards = {card["name"]: card for card in _method_cards(schema)}

    assert pvalue_methods
    for method_name in pvalue_methods:
        assert cards[method_name]["recommended_filter"] == "significance"
    assert "alpha" in _control_names(schema["controls"]["filters"]["significance"])


def test_webapp_ui_schema_uses_range_controls_for_observed_cutoffs() -> None:
    controls = ui_schema_payload()["controls"]["filters"]
    threshold = _controls_by_name(controls["threshold"])["threshold_value"]
    significance = _controls_by_name(controls["significance"])["alpha"]

    assert threshold["control"] == "range"
    assert significance["control"] == "range"


def test_webapp_ui_schema_does_not_require_json_parameter_editors() -> None:
    schema = ui_schema_payload()

    for control in _all_controls(schema):
        assert control.get("control") != "json"
        assert "json" not in str(control.get("label", "")).lower()


def test_webapp_ui_schema_exposes_factual_method_compatibility() -> None:
    schema = ui_schema_payload()
    cards = {card["name"]: card for card in _method_cards(schema)}

    assert cards["disparity"]["target"] == "edge"
    assert cards["disparity"]["requires_weights"] is True
    assert cards["disparity"]["output_type"] == "pvalue"
    assert cards["node_degree"]["target"] == "node"
    assert cards["node_degree"]["requires_weights"] is False
    assert cards["marginal_likelihood"]["requires_integer_weights"] is True
    assert cards["lans"]["supports_directed"] is True
    assert cards["link_salience"]["supports_directed"] is True
    assert cards["link_prediction"]["supports_directed"] is True
    assert cards["link_prediction_iforest"]["supports_directed"] is True
    assert cards["disparity"]["supports_directed"] is True
    assert cards["disparity"]["directed_semantics"] == (
        "source_outgoing_and_target_incoming_distributions"
    )
    assert "recommended_methods" not in schema


def test_webapp_ui_schema_exposes_default_filter_parameters_for_ui_defaults() -> None:
    schema = ui_schema_payload()
    cards = {card["name"]: card for card in _method_cards(schema)}

    assert cards["maximum_spanning_forest"]["default_filter_parameters"] == {
        "operator": "equal",
        "value": 1.0,
    }
    assert cards["noise_corrected"]["recommended_filter"] == "threshold"
    assert cards["noise_corrected"]["default_filter_parameters"] == {
        "operator": "greater",
        "value": 1.64,
    }
    assert cards["doubly_stochastic"]["default_filter_parameters"] == {
        "operator": "equal",
        "statistic": "doubly_stochastic_connected_selected",
        "value": 1.0,
    }


def test_webapp_noise_corrected_guided_run_uses_reference_cutoff() -> None:
    payload = _guided_payload(
        method="noise_corrected", filter_name="threshold", controls={}, directed=True
    )
    result = run_pipeline_from_payload(payload)
    parameters = result["pipeline"]["filter"]["parameters"]
    assert parameters["value"] == 1.64
    assert parameters["operator"] == "greater"
    assert result["network"]["directed"] is True


def test_webapp_ui_schema_keeps_filter_details_advanced() -> None:
    schema = ui_schema_payload()
    filter_controls = schema["controls"]["filters"]

    significance_controls = _controls_by_name(filter_controls["significance"])
    fraction_controls = _controls_by_name(filter_controls["fraction"])

    assert significance_controls["alpha"].get("advanced") is not True
    assert significance_controls["correction"]["advanced"] is True
    assert fraction_controls["fraction"].get("advanced") is not True
    assert fraction_controls["tie_policy"]["advanced"] is True


def test_webapp_offers_holm_and_seeded_random_ties() -> None:
    filter_controls = ui_schema_payload()["controls"]["filters"]
    significance = _controls_by_name(filter_controls["significance"])
    fraction = _controls_by_name(filter_controls["fraction"])

    assert "holm" in {item["value"] for item in significance["correction"]["options"]}
    assert "random_seeded" in {
        item["value"] for item in fraction["tie_policy"]["options"]
    }
    assert fraction["random_seed"]["shown_when"] == {"tie_policy": "random_seeded"}

    holm = run_pipeline_from_payload(
        _guided_payload(
            method="disparity",
            filter_name="significance",
            controls={"alpha": 0.5, "correction": "holm"},
        )
    )
    assert holm["pipeline"]["filter"]["parameters"]["correction"] == "holm"

    def fraction_parameters(controls: Mapping[str, object]) -> dict[str, object]:
        result = run_pipeline_from_payload(
            _guided_payload(
                method="node_degree", filter_name="fraction", controls=controls
            )
        )
        return dict(result["pipeline"]["filter"]["parameters"])

    seeded = fraction_parameters(
        {"fraction": 0.5, "tie_policy": "random_seeded", "random_seed": 7}
    )
    assert seeded["tie_policy"] == "random_seeded"
    assert seeded["random_seed"] == 7
    # The seed box is hidden for the other tie rules, so a leftover value is not sent.
    stable = fraction_parameters(
        {"fraction": 0.5, "tie_policy": "exact_stable", "random_seed": 7}
    )
    assert "random_seed" not in stable
    with pytest.raises(ValidationError, match="random_seed"):
        fraction_parameters(
            {"fraction": 0.5, "tie_policy": "random_seeded", "random_seed": 1.5}
        )


def test_webapp_ui_schema_illustrates_every_method_parameter() -> None:
    method_controls = ui_schema_payload()["controls"]["methods"]

    for controls in method_controls.values():
        for control in controls:
            if control["control"] == "notice":
                continue
            assert control["description"]
            if control["control"] == "select":
                assert control["options"]
                for option in control["options"]:
                    assert option["description"]
                    assert option["illustration"]["kind"]
            else:
                assert control["illustration"]["kind"]


def test_webapp_ui_schema_method_choices_match_registered_implementations() -> None:
    controls = ui_schema_payload()["controls"]["methods"]
    disparity = _controls_by_name(controls["disparity"])
    lans = _controls_by_name(controls["lans"])
    link_prediction = _controls_by_name(controls["link_prediction"])
    doubly_stochastic = _controls_by_name(controls["doubly_stochastic"])

    assert _option_values(disparity["pvalue_aggregation"]) == {
        "average",
        "in",
        "max",
        "min",
        "out",
    }
    assert _option_values(lans["pvalue_aggregation"]) == _option_values(
        disparity["pvalue_aggregation"]
    )
    assert {
        option["value"]
        for option in disparity["pvalue_aggregation"]["options"]
        if option.get("directed_only")
    } == {"in", "out"}
    aggregation_options = {
        option["value"]: option for option in disparity["pvalue_aggregation"]["options"]
    }
    assert all(
        option["illustration"]["kind"] == "endpoint"
        for option in aggregation_options.values()
    )
    assert all(
        option["illustration"]["left_value"] != option["illustration"]["right_value"]
        for option in aggregation_options.values()
    )
    assert aggregation_options["min"]["illustration"]["result"] == "edge p = 0.02"
    assert aggregation_options["max"]["illustration"]["result"] == "edge p = 0.40"
    assert "ignored_when_directed" not in disparity["pvalue_aggregation"]
    assert "source-outgoing and target-incoming" in str(
        disparity["pvalue_aggregation"]["description"]
    )
    assert "source out-degree-one" in str(disparity["leaf_policy"]["description"])
    assert "ignored_when_directed" not in lans["pvalue_aggregation"]
    assert disparity["leaf_policy"]["default"] == "zero"
    assert lans["leaf_policy"]["default"] == "zero"
    assert aggregation_options["average"]["illustration"]["result"] == ("edge p = 0.21")
    assert _option_values(disparity["leaf_policy"]) == {"ignore", "zero"}
    leaf_options = {
        option["value"]: option for option in disparity["leaf_policy"]["options"]
    }
    assert all(
        option["illustration"]["kind"] == "endpoint" for option in leaf_options.values()
    )
    assert leaf_options["zero"]["illustration"]["result"] == "inputs: 0, 0.40"
    assert leaf_options["ignore"]["illustration"]["result"] == "edge p = 0.40"
    assert _option_values(link_prediction["similarity"]) == {
        "local_path",
        "preferential_attachment",
        "shortest_path",
    }
    assert all(
        option["illustration"]["kind"] == "endpoint"
        for option in link_prediction["similarity"]["options"]
    )
    distance_options = {
        option["value"]: option
        for option in link_prediction["distance_transform"]["options"]
    }
    assert distance_options["inverse"]["illustration"]["result"] == ("distance = 0.20")
    assert distance_options["identity"]["illustration"]["result"] == "distance = 5"
    assert doubly_stochastic["epsilon"]["default"] == 1e-4
    assert link_prediction["epsilon"]["default"] == 1.0
    assert "distance_transform" not in _controls_by_name(controls["glanb"])


def test_webapp_react_entrypoint_is_built_into_package_assets() -> None:
    html = _static_text("index.html")

    assert '<div id="root"></div>' in html
    assert 'src="/app.js"' in html
    assert 'href="/styles.css"' in html
    assert len(_static_text("app.js")) > 100_000
    assert len(_static_text("styles.css")) > 10_000


def test_webapp_source_keeps_extraction_in_one_workspace() -> None:
    source = _frontend_text("App.tsx")

    for workspace in ("start", "analysis", "compare", "sweep"):
        assert f'workspace === "{workspace}"' in source
    for former_stage in ("dataset", "extract", "result"):
        assert f'setWorkspace("{former_stage}")' not in source
    assert "<AnalysisWorkspace" in source
    assert "Back to analysis" in source


def test_webapp_source_exposes_package_backed_sweep_workspace() -> None:
    app = _frontend_text("App.tsx")
    sweep = _frontend_text("components", "ConfigurationSweepWorkspace.tsx")
    setup = _frontend_text("sweepSetup.ts")
    api = _frontend_text("api.ts")

    assert "SweepWorkspace" in app
    assert 'aria-label="Sweep: test a range of values"' in app
    assert "initialConfiguration=" in app
    assert "filterPreview?.resolved_config" in app
    assert "onBack={backToAnalysis}" in app
    assert "<BackLink onClick={onBack} />" in sweep
    assert "Test a range of settings" in sweep
    assert "What to vary?" in sweep
    assert "Add another setup" in sweep
    assert "Duplicate setup" in sweep
    assert "Method, filter and fixed settings" in sweep
    assert "Add another setting" in sweep
    # Numbers start as a From/To/Step range, and the sweep runs without a review step.
    assert 'RANGE_PARTS = [["from", "From"], ["to", "To"], ["step", "Step"]]' in sweep
    assert "Range</button>" in sweep
    assert "List</button>" in sweep
    assert '"Run sweep"' in sweep
    assert "preview_only" not in sweep
    assert "Review runs" not in sweep
    assert "SWEEP_RUN_LIMIT = 100" in setup
    assert "parameter-choices" in sweep
    assert "Choose two or more." in sweep
    assert 'aria-label="Backbone measurements"' in sweep
    assert "SweepResults" in sweep
    assert "Run settings" in sweep
    assert "Edit sweep" in sweep
    assert "<DownloadMenu items={downloads} />" in sweep
    assert "configuration-drawer" in sweep
    assert "mergeDescriptions" in sweep
    assert "overflow-y: auto" in _frontend_text("styles.css")
    assert "separated by commas" in sweep
    assert "One row for each run." in sweep
    assert 'requestJson<SweepResponse>("/api/sweep"' in api


def test_webapp_analysis_keeps_controls_and_preview_together() -> None:
    app = _frontend_text("App.tsx")
    styles = _frontend_text("styles.css")

    assert 'className="analysis-controls"' in app
    assert 'className="analysis-preview"' in app
    assert ".analysis-canvas" in styles
    assert "<NetworkPreview graph={graph}" in app


def test_webapp_source_exposes_saved_result_comparison_workspace() -> None:
    app = _frontend_text("App.tsx")
    comparison = _frontend_text("components", "ComparisonWorkspace.tsx")
    api = _frontend_text("api.ts")

    assert "Save this backbone" in app
    assert "savedCount >= 2" in app
    assert "aria-label={`Compare ${savedCount} saved backbones`}" in app
    assert "<BackLink onClick={onBack} />" in comparison
    assert "Compare backbones" in comparison
    assert 'aria-label="Saved backbones"' in comparison
    assert 'role="group" aria-label="Comparison scope"' in comparison
    assert "Properties" in comparison
    assert "Overlap &amp; agreement" in comparison
    assert "Score alignment" in comparison
    assert "Backbone pair" in comparison
    assert "Select two or more backbones" in comparison
    # Each saved backbone has one menu for its actions.
    assert "aria-label={`Options for ${item.label}`}" in comparison
    assert ">Details</button>" in comparison
    assert 'role="dialog" aria-modal="true"' in comparison
    # Status and explanation columns appear only when a value is missing.
    assert '"value", ...(problems ? ["status", "explanation"] : [])' in comparison
    assert 'requestJson<ComparisonResponse>("/api/compare"' in api


def test_webapp_source_exports_accessible_comparison_figures() -> None:
    comparison = _frontend_text("components", "ComparisonWorkspace.tsx")
    figure = _frontend_text("components", "ComparisonFigure.tsx")
    alignment = _frontend_text("components", "ScoreAlignmentFigure.tsx")
    export = _frontend_text("figureExport.ts")

    assert "ComparisonFigure" in comparison
    assert "downloadSvgFigure" in comparison
    assert "downloadPngFigure" in comparison
    assert 'role="img"' in figure
    assert "aria-labelledby" in figure
    assert "<title id={titleId}>" in figure
    assert "<desc id={descriptionId}>" in figure
    assert "record.status" in figure
    assert "Unavailable" in figure
    assert "ScoreAlignmentFigure" in comparison
    assert 'role="img"' in alignment
    assert "importance_rank_a" in alignment
    assert "importance_rank_b" in alignment
    assert "Higher rank means greater importance" in alignment
    assert 'title="Zoom in"' in alignment
    assert 'title="Zoom out"' in alignment
    assert 'title="Reset view"' in alignment
    assert "onPointerMove" in alignment
    assert 'metricLabel("score_spearman")' in alignment
    assert "alignmentOverlap" in comparison
    assert "XMLSerializer" in export
    assert 'type: "image/svg+xml;charset=utf-8"' in export
    assert '"image/png"' in export
    assert "deviceScaleFactor" not in export


def test_webapp_source_uses_accessible_single_select_filters() -> None:
    source = _frontend_text("App.tsx")

    # The filter is a switch on the page, preset to the method's recommendation.
    assert (
        '<div className="filter-switch" role="radiogroup" '
        'aria-labelledby="retention-title">'
    ) in source
    assert '<input type="radio" name="analysis-filter"' in source
    assert "checked={name === filterName}" in source
    assert "filterName === method.recommended_filter" in source
    assert "if (!score?.score_id || !method) {" in source
    assert "filterOptions(method)" in source
    assert "filterChosen" not in source


def test_webapp_source_keeps_primary_result_actions_reachable() -> None:
    app = _frontend_text("App.tsx")
    details = _frontend_text("components", "BackboneDetails.tsx")

    for label in ("Save this backbone", "Inspect &amp; export"):
        assert label in app
    for label in (
        "Method statistics",
        "Run settings",
        "Statistics (CSV)",
        "Backbone (GraphML)",
        "Full network with scores (GEXF)",
        "Settings (JSON)",
        "Full experiment (ZIP)",
    ):
        assert label in details
    assert "downloadStatistics" in _frontend_text("components", "StatisticsTable.tsx")
    assert 'downloadGraph(result.result_id, "graphml", "backbone")' in details
    assert "resultDialog.current?.showModal()" in app
    assert "<BackboneDetails" in app
    assert "Comparison label" not in app
    assert "Rename backbone" in _frontend_text("components", "ComparisonWorkspace.tsx")


def test_webapp_source_emphasizes_the_next_extraction_action() -> None:
    app = _frontend_text("App.tsx")
    styles = _frontend_text("styles.css")

    assert 'aria-label="Analysis actions"' in app
    assert "|| !networkReady || Boolean(selectedBlocked)" in app
    assert "onClick={onScore}" in app
    assert "onMaterialize(true)" in app
    assert "onMaterialize(false)" in app
    assert "min-height: var(--button-height)" in styles
    assert ".button--primary, .button--save, .button--success" in styles
    assert "--action-tone: var(--button-green)" in styles


def test_webapp_source_includes_guided_score_and_filter_controls() -> None:
    app = _frontend_text("App.tsx")
    score_distribution = _frontend_text("components", "ScoreDistribution.tsx")
    api = _frontend_text("api.ts")

    assert 'placeholder="Search methods"' in app
    assert "contextualMeaning(method, context)" in app
    assert "adjustedFilterControls" in app
    assert "filterDefaults" in app
    assert "RetentionPreview" in app
    assert "backbone_edge_count" in app
    assert "backbone_component_count" in app
    assert "node_coverage_count" in app
    assert "backbone_node_count" in app
    assert 'requestJson<FilterPreview>("/api/filter-preview"' in api
    assert "aria-label={`${method.label} score distribution`}" in score_distribution
    assert "distribution__boundary" in score_distribution


def test_webapp_source_opens_dataset_settings_from_the_network_summary() -> None:
    app = _frontend_text("App.tsx")

    assert "Network settings</button>" in app
    assert "settingsDialog.current?.showModal()" in app
    assert "setMappingReviewPending(true)" in app
    assert "mappingReviewPending && dialog && !dialog.open" in app
    assert "Use this mapping" in app
    assert "weightMeaningMissing || (mappingReviewPending && !networkReady)" in app
    assert "View raw file" not in app
    assert "Detected mapping" in app
    assert "Show mapped columns" in app
    assert "Show all ${allColumns.length} columns" in app
    assert "Change mapping" in app
    assert "Describe this network" in app
    assert "onText" not in app
    assert "<textarea value={data.text}" not in app


def test_webapp_source_filters_methods_by_discovery_facets() -> None:
    app = _frontend_text("App.tsx")

    assert 'aria-label="Method filters"' in app
    assert "All targets" in app
    assert "All approaches" in app
    assert "Directed compatible" in app
    assert "Undirected only" in app
    assert "Compatible only" in app
    assert "Reset filters" in app
    assert "activeMethodFilterCount" in app
    assert "candidate.approaches.includes(approachFilter)" in app
    assert "conciseScoreMeaning(candidate, context)" in app
    assert "candidate.output_type" not in app


def test_webapp_source_keeps_method_details_in_selected_pane() -> None:
    app = _frontend_text("App.tsx")

    assert '<span aria-hidden="true">1</span> Method</h2>' in app
    assert '<span aria-hidden="true">2</span> Filter</h2>' in app
    assert "<strong>{method.label}</strong>" in app
    assert "<span>{filterLabel(name)}</span>" in app
    assert "Start with a goal" not in app
    assert "Clear search and filters" in app
    assert 'aria-label="Change method"' in app
    assert "methodDialog.current?.showModal()" in app
    assert "Advanced method settings" in app
    assert "compactChoices" in app
    assert "Browse methods to choose one for this network." in app
    assert "Recommended" in app
    assert 'aria-label="Change filter"' not in app
    assert "</button> : methodChoiceButton}" in app
    assert '{score && method && <section className="analysis-step">' in app
    assert "Advanced filter options" in app


def test_webapp_source_uses_live_graph_and_resolves_full_results_on_demand() -> None:
    source = _frontend_text("App.tsx")

    assert "filterPreview?.graph" in source
    assert "api.filterPreview" in source
    assert "api.filter(" in source
    assert "<BackboneDetails" in source
    assert "result.resolved_config" in _frontend_text(
        "components", "BackboneDetails.tsx"
    )


def test_webapp_source_includes_examples_and_export_bridges() -> None:
    app = _frontend_text("App.tsx")
    examples = _frontend_text("examples.ts")
    api = _frontend_text("api.ts")

    for example_name in ("weighted", "unweighted", "temporal"):
        assert f'name: "{example_name}"' in examples
    assert 'time: "time"' in examples
    assert 'eventWeight: "magnitude"' in examples
    assert 'format: "gexf" | "graphml"' in api
    assert 'downloadAttachment("/api/export",' in api
    assert 'downloadAttachment("/api/export-result",' in api
    details = _frontend_text("components", "BackboneDetails.tsx")
    assert "<BackboneDetails" in app
    assert "downloadGraph" in details
    assert "StatisticsTable" in details
    assert "downloadCsv" in _frontend_text("components", "StatisticsTable.tsx")
    assert "downloadJson" in details


def test_webapp_source_includes_graphml_import_controls() -> None:
    app = _frontend_text("App.tsx")
    utilities = _frontend_text("utils.ts")

    assert 'accept=".csv,.tsv,.txt,.edges,.graphml,.xml"' in app
    assert 'mode === "graphml"' in app
    assert "numeric_edge_attributes" in app
    assert "nextPreview.source_directed === true" in app
    assert "detectDelimiter(file.name, text)" in app
    assert "const sourceDirected = data.directed" in utilities
    assert "payload.graphml_text = data.text" in utilities
    assert 'directionMode: "preserve"' in _frontend_text("examples.ts")


def test_webapp_source_includes_guided_temporal_controls() -> None:
    app = _frontend_text("App.tsx")
    utilities = _frontend_text("utils.ts")
    control = _frontend_text("components", "ControlField.tsx")

    assert 'data.mode === "temporal"' in app
    assert "Event magnitude" in app
    assert "temporalWeighting" in app
    assert "schema.temporal.controls" in app
    assert "payload.temporal" in utilities
    assert "snapshot_size" in utilities
    assert "snapshot_origin" in utilities
    assert 'step={control.step ?? "any"}' in control


def test_webapp_source_collects_structured_network_context() -> None:
    app = _frontend_text("App.tsx")
    utilities = _frontend_text("utils.ts")

    for label in (
        "Nodes represent",
        '"Edges"} represent',
        "Weight represents",
        "What do higher weights mean?",
        "Strength",
        "Distance or cost",
    ):
        assert label in app
    assert "contextSummary" in utilities
    assert "contextualMeaning" in utilities
    assert "weightSemantics" in utilities


def test_webapp_source_includes_accessibility_hooks() -> None:
    app = _frontend_text("App.tsx")
    comparison = _frontend_text("components", "ComparisonWorkspace.tsx")
    graph = _frontend_text("components", "NetworkPreview.tsx")

    assert 'aria-labelledby="analysis-title"' in app
    assert 'aria-labelledby="network-settings-title"' in app
    assert 'aria-labelledby="live-preview-title"' in app
    assert 'aria-labelledby="result-title"' in app
    assert 'aria-labelledby="compare-title"' in comparison
    assert 'role="img" aria-label="Backbone graph preview"' in graph
    assert "const large = graph.truncated || graph.nodes.length > 80;" in graph
    assert "Preview unavailable for large networks" in graph
    assert 'className="is-danger"' in comparison


def test_webapp_static_assets_do_not_contain_mojibake() -> None:
    for filename in ("index.html", "app.js", "styles.css"):
        assert "Â" not in _static_text(filename)


def test_webapp_guided_run_edge_weight_threshold() -> None:
    result = run_pipeline_from_payload(
        _guided_payload(
            method="edge_weight",
            filter_name="threshold",
            controls={
                "threshold_value": 2,
                "operator": "greater_equal",
                "drop_isolates": False,
            },
        )
    )

    assert result["status"] == "ok"
    assert result["summary"]["original_edge_count"] == 3
    assert result["summary"]["backbone_edge_count"] == 2
    assert result["pipeline"]["method"]["parameters"]["weight"] == "weight"
    assert result["pipeline"]["filter"]["parameters"]["value"] == 2.0
    assert result["pipeline"]["filter"]["parameters"]["operator"] == "greater_equal"
    assert _retained_count(result["statistics"]) == 2
    assert _retained_count(result["graph"]["edges"]) == 2


def test_webapp_guided_score_returns_score_id_and_ranges() -> None:
    result = score_payload(
        _guided_payload(
            method="edge_weight",
            filter_name="threshold",
            controls={},
        )
    )

    assert result["status"] == "ok"
    assert str(result["score_id"]).startswith("score-")
    assert result["score_summary"]["score_row_count"] == 3
    assert result["method_result"]["primary_statistic"] == "score"
    assert result["pipeline"]["filter"] is None
    assert "retained" not in result["statistics"][0]
    assert result["score_ranges"]["score"] == {
        "min": 1.0,
        "max": 4.0,
        "count": 3,
    }


def test_webapp_guided_filter_reuses_cached_scores() -> None:
    score_result = score_payload(
        _guided_payload(
            method="edge_weight",
            filter_name="threshold",
            controls={},
        )
    )
    payload = _guided_payload(
        method="edge_weight",
        filter_name="threshold",
        controls={
            "threshold_value": 2,
            "operator": "greater_equal",
            "drop_isolates": False,
        },
    )
    payload["score_id"] = score_result["score_id"]

    result = filter_payload(payload)

    assert result["status"] == "ok"
    assert result["score_id"] == score_result["score_id"]
    assert result["summary"]["backbone_edge_count"] == 2
    assert result["summary"]["target"] == "edge"
    assert result["summary"]["node_coverage_count"] == 3
    assert result["summary"]["node_coverage_fraction"] == 1.0
    assert result["pipeline"]["method"]["parameters"]["weight"] == "weight"
    assert result["pipeline"]["filter"]["parameters"]["value"] == 2.0
    assert _retained_count(result["statistics"]) == 2


def test_webapp_filter_result_distinguishes_node_coverage_from_output_nodes() -> None:
    score_result = score_payload(
        _guided_payload(method="edge_weight", filter_name="threshold", controls={})
    )
    payload = _guided_payload(
        method="edge_weight",
        filter_name="threshold",
        controls={
            "threshold_value": 3,
            "operator": "greater_equal",
            "drop_isolates": False,
        },
    )
    payload["score_id"] = score_result["score_id"]

    result = filter_payload(payload)

    assert result["summary"]["node_coverage_count"] == 2
    assert result["summary"]["node_coverage_fraction"] == pytest.approx(2 / 3)
    assert result["summary"]["backbone_node_count"] == 3
    assert result["summary"]["node_fraction"] == 1.0


@pytest.mark.parametrize(
    ("drop_isolates", "expected_backbone_nodes"),
    [(False, 3), (True, 2)],
)
def test_webapp_filter_preview_reports_exact_edge_node_coverage(
    drop_isolates: bool,
    expected_backbone_nodes: int,
) -> None:
    score_result = score_payload(
        _guided_payload(method="edge_weight", filter_name="threshold", controls={})
    )
    payload = _guided_payload(
        method="edge_weight",
        filter_name="threshold",
        controls={
            "threshold_value": 3,
            "operator": "greater_equal",
            "drop_isolates": drop_isolates,
        },
    )
    payload["score_id"] = score_result["score_id"]

    result = filter_preview_payload(payload)

    assert result["status"] == "ok"
    assert result["target"] == "edge"
    assert result["selected_item_count"] == 1
    assert result["total_item_count"] == 3
    assert result["node_coverage_count"] == 2
    assert result["node_coverage_fraction"] == pytest.approx(2 / 3)
    assert result["backbone_node_count"] == expected_backbone_nodes
    assert result["original_edge_count"] == 3
    assert result["backbone_edge_count"] == 1
    assert result["backbone_component_count"] == expected_backbone_nodes - 1
    assert sum(node["isolated"] for node in result["graph"]["nodes"]) == (
        expected_backbone_nodes - 2
    )
    assert result["backbone_isolated_node_count"] == expected_backbone_nodes - 2
    assert result["backbone_node_fraction"] == pytest.approx(
        expected_backbone_nodes / 3
    )
    assert result["drop_isolates"] is drop_isolates


def test_webapp_filter_preview_reports_node_target_retention() -> None:
    score_result = score_payload(
        _guided_payload(method="node_degree", filter_name="fraction", controls={})
    )
    payload = _guided_payload(
        method="node_degree",
        filter_name="fraction",
        controls={"fraction": 0.1, "tie_policy": "exact_stable"},
    )
    payload["score_id"] = score_result["score_id"]

    result = filter_preview_payload(payload)

    assert result["target"] == "node"
    assert result["selected_item_count"] == 1
    assert result["node_coverage_count"] == 1
    assert result["backbone_node_count"] == 1
    assert result["backbone_edge_count"] == 0
    assert result["backbone_component_count"] == 1
    assert result["backbone_isolated_node_count"] == 1
    assert result["backbone_node_fraction"] == pytest.approx(1 / 3)


def test_webapp_graphml_export_colors_retained_and_rejected_edges() -> None:
    score_result = score_payload(
        _guided_payload(method="edge_weight", filter_name="threshold", controls={})
    )
    payload = _guided_payload(
        method="edge_weight",
        filter_name="threshold",
        controls={
            "threshold_value": 2,
            "operator": "greater_equal",
            "drop_isolates": False,
        },
    )
    payload["score_id"] = score_result["score_id"]
    payload["export"] = {"format": "graphml", "scope": "annotated"}

    exported = graph_export_payload(payload)
    graph = nx.read_graphml(BytesIO(exported.content))
    colors = [
        value
        for _, _, attributes in graph.edges(data=True)
        for name, value in attributes.items()
        if name.endswith("_color")
    ]

    assert exported.content_type == "application/graphml+xml"
    assert exported.filename == "netbone-edge-weight-annotated.graphml"
    assert sorted(colors) == ["#0072B2", "#0072B2", "#D9D9D9"]


def test_webapp_gexf_export_includes_gephi_visual_metadata() -> None:
    score_result = score_payload(
        _guided_payload(method="edge_weight", filter_name="threshold", controls={})
    )
    payload = _guided_payload(
        method="edge_weight",
        filter_name="threshold",
        controls={"threshold_value": 2, "operator": "greater_equal"},
    )
    payload["score_id"] = score_result["score_id"]
    payload["export"] = {"format": "gexf", "scope": "backbone"}

    exported = graph_export_payload(payload)

    assert exported.content_type == "application/gexf+xml"
    assert exported.filename == "netbone-edge-weight-backbone.gexf"
    assert b"<viz:color" in exported.content


def test_webapp_gexf_export_includes_link_salience_scores() -> None:
    score_result = score_payload(
        _guided_payload(
            method="link_salience",
            filter_name="threshold",
            controls={},
            weight=None,
        )
    )
    payload = _guided_payload(
        method="link_salience",
        filter_name="threshold",
        controls={"threshold_value": 0.0, "operator": "greater_equal"},
        weight=None,
    )
    payload["score_id"] = score_result["score_id"]
    payload["export"] = {"format": "gexf", "scope": "annotated"}

    exported = graph_export_payload(payload)
    graph = nx.read_gexf(BytesIO(exported.content))
    score_columns = [
        name
        for name in graph["alice"]["bob"]
        if name.startswith("netbone_link_salience_") and name.endswith("_link_salience")
    ]

    assert len(score_columns) == 1
    assert graph["alice"]["bob"][score_columns[0]] == pytest.approx(2 / 3)


def test_webapp_graphml_input_exports_preserved_attributes_to_gexf() -> None:
    score_result = score_payload(_graphml_guided_payload())
    payload = _graphml_guided_payload(
        controls={"threshold_value": 2, "operator": "greater_equal"}
    )
    payload["score_id"] = score_result["score_id"]
    payload["export"] = {"format": "gexf", "scope": "annotated"}

    exported = graph_export_payload(payload)
    graph = nx.read_gexf(BytesIO(exported.content))

    assert exported.filename == "netbone-edge-weight-annotated.gexf"
    assert graph.number_of_nodes() == 3
    assert graph.number_of_edges() == 3
    assert graph.nodes["a"]["group"] == "one"
    assert graph["a"]["b"]["strength"] == 4.0
    assert graph["a"]["b"]["relationship"] == "strong"
    assert b"<viz:color" in exported.content


def test_webapp_directed_graphml_export_preserves_arc_direction() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b", strength=3.0)
    graph.add_edge("b", "a", strength=1.0)
    score_request = _graphml_guided_payload(
        graph=graph,
        method="lans",
        filter_name="significance",
    )
    score_result = score_payload(score_request)
    payload = _graphml_guided_payload(
        graph=graph,
        method="lans",
        filter_name="significance",
        controls={"alpha": 1.0},
    )
    payload["score_id"] = score_result["score_id"]
    payload["export"] = {"format": "graphml", "scope": "annotated"}

    exported = graph_export_payload(payload)
    restored = nx.read_graphml(BytesIO(exported.content))

    assert isinstance(restored, nx.DiGraph)
    assert set(restored.edges()) == {("a", "b"), ("b", "a")}


def test_webapp_graph_export_rejects_unknown_options() -> None:
    payload = _guided_payload(
        method="edge_weight", filter_name="threshold", controls={}
    )
    payload["score_id"] = "unused"
    payload["export"] = {"format": "pdf", "scope": "annotated"}

    with pytest.raises(ValidationError, match="export.format"):
        graph_export_payload(payload)


def test_webapp_guided_filter_requires_available_score_id() -> None:
    payload = _guided_payload(
        method="edge_weight",
        filter_name="threshold",
        controls={},
    )
    payload["score_id"] = "missing-score"

    with pytest.raises(ValidationError, match="Compute scores again"):
        filter_payload(payload)


def test_webapp_comparison_returns_public_api_metric_records() -> None:
    score_request = _guided_payload(
        method="edge_weight",
        filter_name="threshold",
        controls={},
    )
    score_result = score_payload(score_request)
    results = []
    for label, threshold in (("Strict", 4.0), ("Broader", 2.0)):
        request = _guided_payload(
            method="edge_weight",
            filter_name="threshold",
            controls={
                "threshold_value": threshold,
                "operator": "greater_equal",
                "drop_isolates": False,
            },
        )
        request["score_id"] = score_result["score_id"]
        filtered = filter_payload(request)
        results.append({"result_id": filtered["result_id"], "label": label})

    comparison = comparison_payload({"results": results})

    assert comparison["status"] == "ok"
    assert [item["label"] for item in comparison["results"]] == [
        "Strict",
        "Broader",
    ]
    assert _metric_record(
        comparison["single_metrics"], metric="edge_retention", result="Strict"
    )["value"] == pytest.approx(1 / 3)
    assert _metric_record(
        comparison["single_metrics"], metric="edge_retention", result="Broader"
    )["value"] == pytest.approx(2 / 3)
    assert _metric_record(comparison["pairwise_metrics"], metric="edge_jaccard")[
        "value"
    ] == pytest.approx(0.5)
    spearman = _metric_record(comparison["pairwise_metrics"], metric="score_spearman")
    assert spearman["status"] == "ok"
    assert spearman["value"] == pytest.approx(1.0)
    alignment = comparison["alignments"][0]
    assert alignment["status"] == "ok"
    assert alignment["target"] == "edge"
    assert alignment["output_type_a"] == "score"
    assert alignment["preferred_direction_a"] == "higher"
    assert len(alignment["points"]) == 3
    assert set(alignment["points"][0]) == {
        "source",
        "target",
        "value_a",
        "value_b",
        "importance_rank_a",
        "importance_rank_b",
    }
    experiment_id = comparison["experiment_id"]
    server = ThreadingHTTPServer(("127.0.0.1", 0), NetboneWebHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_address[1]}/api/export-experiment",
            data=json.dumps({"experiment_id": experiment_id}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            assert response.headers.get_content_type() == "application/zip"
            assert (
                "netbone-comparison-experiment.zip"
                in response.headers["Content-Disposition"]
            )
            archive = response.read()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
    with ZipFile(BytesIO(archive)) as bundle:
        manifest = json.loads(bundle.read("manifest.json"))
        assert manifest["subject_type"] == "comparison"
        assert set(manifest["files"].values()) <= set(bundle.namelist())
        assert json.loads(bundle.read("comparison.json"))["result_names"] == [
            "Strict",
            "Broader",
        ]
        settings = json.loads(bundle.read("web_settings.json"))["results"]
        assert [item["label"] for item in settings] == ["Strict", "Broader"]
        assert [item["context"] for item in settings] == ["test web run"] * 2
        assert json.loads(bundle.read("web_comparison_records.json")) == {
            key: comparison[key]
            for key in ("single_metrics", "pairwise_metrics", "alignments")
        }


def test_webapp_doubly_stochastic_sweep_reuses_inputs_not_diagnostics() -> None:
    request = _guided_payload(
        method="doubly_stochastic",
        filter_name="fraction",
        controls={"fraction": 0.7, "epsilon": 0.002},
    )
    scored = score_payload(request)
    request["score_id"] = scored["score_id"]
    preview = filter_preview_payload(request)
    finalized = filter_payload(request)
    method = preview["resolved_config"]["method"]
    assert method == scored["pipeline"]["method"]
    assert method == finalized["resolved_config"]["method"]
    assert method["parameters"]["epsilon"] == 0.002
    assert "iterations_by_component" in finalized["extraction"]["method_parameters"]

    request["metrics"] = ["edge_retention"]
    sweep = sweep_payload(
        {
            **request,
            "variation": {"scope": "configurations"},
            "configurations": [
                {
                    "name": "Current extraction",
                    "method": method,
                    "filter": {
                        "name": "fraction",
                        "parameters": {"fraction": [0.5, 0.7]},
                    },
                }
            ],
        }
    )
    legacy = sweep_payload(
        {
            **request,
            "variation": {
                "scope": "filter",
                "parameter": "fraction",
                "values": [0.5, 0.7],
            },
        }
    )
    for response in (sweep, legacy):
        assert [run["status"] for run in response["runs"]] == ["ok", "ok"]
        assert [run["filter_parameters"]["fraction"] for run in response["runs"]] == [
            0.5,
            0.7,
        ]


def test_webapp_filter_sweep_returns_tidy_records_and_reuses_scores() -> None:
    request = _guided_payload(
        method="edge_weight",
        filter_name="threshold",
        controls={"threshold_value": 1.0, "operator": "greater_equal"},
    )
    scored = score_payload(request)
    request.update(
        {
            "score_id": scored["score_id"],
            "variation": {
                "scope": "filter",
                "parameter": "value",
                "values": [1.0, 2.0, 4.0],
            },
            "metrics": ["edge_count", "edge_retention"],
        }
    )

    swept = sweep_payload(request)

    assert swept["status"] == "ok"
    assert swept["score_cache_misses"] == 1
    assert swept["score_cache_hits"] == 2
    assert len(swept["runs"]) == 3
    assert len(swept["metrics"]) == 6
    assert {row["status"] for row in swept["runs"]} == {"ok"}
    assert {row["metric"] for row in swept["metrics"]} == {
        "edge_count",
        "edge_retention",
    }
    assert len(swept["configuration"]["configurations"]) == 3

    request["preview_only"] = True
    preview = sweep_payload(request)
    assert preview["status"] == "preview"
    assert preview["runs"] == []
    assert preview["metrics"] == []
    assert "experiment_id" not in preview
    assert len(preview["configuration"]["configurations"]) == 3


def test_webapp_sweep_rejects_missing_or_oversized_value_lists() -> None:
    request = _guided_payload(
        method="edge_weight",
        filter_name="fraction",
        controls={"fraction": 0.5},
    )
    scored = score_payload(request)
    request["score_id"] = scored["score_id"]
    request["metrics"] = ["edge_count"]

    request["variation"] = {
        "scope": "filter",
        "parameter": "fraction",
        "values": [0.5],
    }
    with pytest.raises(ValidationError, match="at least two"):
        sweep_payload(request)

    request["variation"] = {
        "scope": "filter",
        "parameter": "fraction",
        "values": list(range(101)),
    }
    with pytest.raises(ValidationError, match="more than 100"):
        sweep_payload(request)


def test_webapp_method_sweep_isolates_failed_configurations() -> None:
    request = _guided_payload(
        method="disparity",
        filter_name="significance",
        controls={"alpha": 1.0},
    )
    scored = score_payload(request)
    request.update(
        {
            "score_id": scored["score_id"],
            "variation": {
                "scope": "method",
                "parameter": "pvalue_aggregation",
                "values": ["min", "not-a-policy", "max"],
            },
            "metrics": ["edge_count"],
        }
    )

    swept = sweep_payload(request)

    assert [row["status"] for row in swept["runs"]].count("ok") == 2
    assert [row["status"] for row in swept["runs"]].count("failed") == 1
    failure = next(row for row in swept["runs"] if row["status"] == "failed")
    assert "pvalue_aggregation" in failure["explanation"]
    assert swept["score_cache_hits"] == 0
    assert swept["score_cache_misses"] == 2
    export = experiment_export_payload({"experiment_id": swept["experiment_id"]})
    assert export.filename == "netbone-sweep-experiment.zip"
    assert (
        experiment_export_payload({"experiment_id": swept["experiment_id"]}) == export
    )
    with ZipFile(BytesIO(export.content)) as bundle:
        manifest = json.loads(bundle.read("manifest.json"))
        assert manifest["subject_type"] == "sweep_result"
        assert set(manifest["files"].values()) <= set(bundle.namelist())
        assert "not-a-policy" in bundle.read("tables/failures.csv").decode()
        settings = json.loads(bundle.read("web_settings.json"))
        assert settings["resolved_config"] == swept["configuration"]
        assert settings["variation"] == swept["variation"]
        stored_run = json.loads(bundle.read("sweep.json"))
        assert stored_run["runs"] == swept["runs"]
        assert stored_run["table"] == swept["metrics"]


def test_webapp_experiment_export_rejects_missing_and_expired_ids() -> None:
    with pytest.raises(ValidationError, match="experiment_id must be"):
        experiment_export_payload({})
    with pytest.raises(ValidationError, match="Run the comparison or sweep again"):
        experiment_export_payload({"experiment_id": "expired-experiment"})


def test_webapp_method_filter_grid_preserves_incompatible_failures() -> None:
    request = _guided_payload(
        method="edge_weight",
        filter_name="fraction",
        controls={"fraction": 0.5},
    )
    scored = score_payload(request)
    request.update(
        {
            "score_id": scored["score_id"],
            "variation": {"scope": "grid"},
            "grid": {
                "methods": {
                    "edge_weight": {"weight": "weight"},
                    "disparity": {"weight": "weight"},
                },
                "filters": {
                    "fraction": {"fraction": 0.5},
                    "significance": {"alpha": 0.5},
                },
            },
            "metrics": ["edge_count"],
        }
    )

    preview_request = {**request, "preview_only": True}
    preview = sweep_payload(preview_request)
    swept = sweep_payload(request)

    assert preview["status"] == "preview"
    assert len(preview["configuration"]["configurations"]) == 4
    assert swept["variation"] == {
        "scope": "grid",
        "methods": ["edge_weight", "disparity"],
        "filters": ["fraction", "significance"],
    }
    assert len(swept["runs"]) == 4
    assert any(row["status"] == "failed" for row in swept["runs"])
    assert any(row["status"] == "ok" for row in swept["runs"])


def test_webapp_method_filter_grid_expands_parameters_per_named_entry() -> None:
    request = _guided_payload(
        method="edge_weight",
        filter_name="fraction",
        controls={"fraction": 0.5},
    )
    scored = score_payload(request)
    request.update(
        {
            "score_id": scored["score_id"],
            "variation": {"scope": "grid"},
            "grid": {
                "methods": {
                    "edge_weight": {"weight": "weight"},
                    "disparity": {
                        "weight": "weight",
                        "pvalue_aggregation": ["min", "max"],
                    },
                },
                "filters": {
                    "fraction": {
                        "fraction": [0.25, 0.5],
                        "tie_policy": "exact_stable",
                    }
                },
            },
            "metrics": ["edge_count"],
            "preview_only": True,
        }
    )

    preview = sweep_payload(request)

    configurations = list(preview["configuration"]["configurations"].values())
    assert len(configurations) == 6
    disparity = [
        config for config in configurations if config["method"]["name"] == "disparity"
    ]
    assert {
        config["method"]["parameters"]["pvalue_aggregation"] for config in disparity
    } == {
        "min",
        "max",
    }
    assert {
        config["filter"]["parameters"]["fraction"] for config in configurations
    } == {
        0.25,
        0.5,
    }


def test_webapp_configuration_sweep_keeps_named_setups_independent() -> None:
    request = _guided_payload(
        method="edge_weight",
        filter_name="fraction",
        controls={"fraction": 0.5},
    )
    scored = score_payload(request)
    request.update(
        {
            "score_id": scored["score_id"],
            "variation": {"scope": "configurations"},
            "configurations": [
                {
                    "name": "Disparity significance",
                    "method": {
                        "name": "disparity",
                        "parameters": {"pvalue_aggregation": ["min", "max"]},
                    },
                    "filter": {
                        "name": "significance",
                        "parameters": {"alpha": [0.05, 0.1]},
                    },
                },
                {
                    "name": "Weight fraction",
                    "method": {"name": "edge_weight", "parameters": {}},
                    "filter": {
                        "name": "fraction",
                        "parameters": {"fraction": [0.25, 0.5]},
                    },
                },
            ],
            "metrics": ["edge_count"],
            "preview_only": True,
        }
    )

    preview = sweep_payload(request)
    configurations = list(preview["configuration"]["configurations"].values())

    assert preview["variation"] == {
        "scope": "configurations",
        "configurations": ["Disparity significance", "Weight fraction"],
    }
    assert len(configurations) == 6
    assert list(preview["setup_names"].values()).count("Disparity significance") == 4
    assert list(preview["setup_names"].values()).count("Weight fraction") == 2
    assert {
        (config["method"]["name"], config["filter"]["name"])
        for config in configurations
    } == {("disparity", "significance"), ("edge_weight", "fraction")}

    assert "experiment_id" not in preview
    request["preview_only"] = False
    completed = sweep_payload(request)
    download = experiment_export_payload({"experiment_id": completed["experiment_id"]})
    with ZipFile(BytesIO(download.content)) as bundle:
        assert bundle.testzip() is None
        settings = json.loads(bundle.read("web_settings.json"))
        assert settings["setup_names"] == preview["setup_names"]
        assert settings["resolved_config"] == preview["configuration"]
        runs = json.loads(bundle.read("sweep.json"))["runs"]
        assert runs == completed["runs"]
        assert {
            (
                run["method_parameters"]["pvalue_aggregation"],
                run["filter_parameters"]["alpha"],
            )
            for run in runs
            if run["method"] == "disparity"
        } == {("min", 0.05), ("min", 0.1), ("max", 0.05), ("max", 0.1)}


def test_webapp_configuration_sweep_runs_directly_from_dataset() -> None:
    request = _guided_payload(
        method="edge_weight",
        filter_name="fraction",
        controls={"fraction": 0.5},
    )
    request.update(
        {
            "variation": {"scope": "configurations"},
            "configurations": [
                {
                    "name": "Weight fractions",
                    "method": {"name": "edge_weight", "parameters": {}},
                    "filter": {
                        "name": "fraction",
                        "parameters": {"fraction": [0.25, 0.5]},
                    },
                }
            ],
            "metrics": ["edge_count"],
        }
    )

    swept = sweep_payload(request)

    assert swept["status"] == "ok"
    assert swept["score_id"] is None
    assert len(swept["runs"]) == 2
    assert set(swept["setup_names"].values()) == {"Weight fractions"}
    assert {
        config["method"]["parameters"]["weight"]
        for config in swept["configuration"]["configurations"].values()
    } == {"weight"}
    assert [record["value"] for record in swept["metrics"]] == [1, 2]
    assert swept["score_cache_misses"] == 1
    assert swept["score_cache_hits"] == 1


def test_webapp_configuration_sweep_uses_selected_weight_column() -> None:
    request = _guided_payload(
        method="edge_weight",
        filter_name="fraction",
        controls={"fraction": 0.5},
        weight="strength",
    )
    request["csv_text"] = WEIGHTED_CSV.replace("weight", "strength")
    request.update(
        {
            "variation": {"scope": "configurations"},
            "configurations": [
                {
                    "name": "Strength fractions",
                    "method": {"name": "edge_weight", "parameters": {}},
                    "filter": {
                        "name": "fraction",
                        "parameters": {"fraction": [0.25, 0.5]},
                    },
                }
            ],
            "metrics": ["edge_count"],
        }
    )

    swept = sweep_payload(request)

    assert {
        config["method"]["parameters"]["weight"]
        for config in swept["configuration"]["configurations"].values()
    } == {"strength"}
    assert [record["value"] for record in swept["metrics"]] == [1, 2]


def test_webapp_method_filter_grid_requires_non_empty_sides() -> None:
    request = _guided_payload(
        method="edge_weight",
        filter_name="fraction",
        controls={"fraction": 0.5},
    )
    scored = score_payload(request)
    request.update(
        {
            "score_id": scored["score_id"],
            "variation": {"scope": "grid"},
            "grid": {"methods": {}, "filters": {"fraction": {}}},
            "metrics": ["edge_count"],
        }
    )

    with pytest.raises(ValidationError, match="grid.methods must be a non-empty"):
        sweep_payload(request)


def test_webapp_comparison_preserves_invalid_metric_explanations() -> None:
    edge_result = run_pipeline_from_payload(
        _guided_payload(
            method="edge_weight",
            filter_name="threshold",
            controls={"threshold_value": 2.0, "operator": "greater_equal"},
        )
    )
    node_result = run_pipeline_from_payload(
        _guided_payload(
            method="node_degree",
            filter_name="fraction",
            controls={"fraction": 0.5, "tie_policy": "exact_stable"},
        )
    )

    comparison = comparison_payload(
        {
            "results": [
                {"result_id": edge_result["result_id"], "label": "Edges"},
                {"result_id": node_result["result_id"], "label": "Nodes"},
            ]
        }
    )
    spearman = _metric_record(comparison["pairwise_metrics"], metric="score_spearman")

    assert spearman["status"] == "invalid"
    assert spearman["same_target"] is False
    assert "same result target" in spearman["explanation"]
    alignment = comparison["alignments"][0]
    assert alignment["status"] == "invalid"
    assert alignment["points"] == []
    assert "same result target" in alignment["explanation"]


def test_webapp_comparison_preserves_directed_reciprocal_arc_identity() -> None:
    csv_text = "source,target,weight\na,b,4\nb,a,2\na,c,1\n"
    score_request = _guided_payload(
        method="lans",
        filter_name="fraction",
        controls={},
        directed=True,
    )
    score_request["csv_text"] = csv_text
    score_result = score_payload(score_request)
    results = []
    for label, fraction in (("One arc", 1 / 3), ("Reciprocal arcs", 2 / 3)):
        request = _guided_payload(
            method="lans",
            filter_name="fraction",
            controls={"fraction": fraction, "tie_policy": "exact_stable"},
            directed=True,
        )
        request["csv_text"] = csv_text
        request["score_id"] = score_result["score_id"]
        filtered = filter_payload(request)
        results.append({"result_id": filtered["result_id"], "label": label})

    comparison = comparison_payload({"results": results})
    edge_jaccard = _metric_record(comparison["pairwise_metrics"], metric="edge_jaccard")

    assert edge_jaccard["status"] == "ok"
    assert edge_jaccard["value"] == pytest.approx(0.5)
    assert edge_jaccard["same_original_graph"] is True


def test_webapp_comparison_rejects_missing_results_and_duplicate_labels() -> None:
    result = run_pipeline_from_payload(
        _guided_payload(
            method="edge_weight",
            filter_name="threshold",
            controls={"threshold_value": 2.0},
        )
    )

    with pytest.raises(ValidationError, match="at least two"):
        comparison_payload(
            {"results": [{"result_id": result["result_id"], "label": "Only"}]}
        )
    with pytest.raises(ValidationError, match="labels must be unique"):
        comparison_payload(
            {
                "results": [
                    {"result_id": result["result_id"], "label": "Same"},
                    {"result_id": result["result_id"], "label": "same"},
                ]
            }
        )


def test_webapp_graph_export_accepts_cached_result_id() -> None:
    result = run_pipeline_from_payload(
        _guided_payload(
            method="edge_weight",
            filter_name="threshold",
            controls={"threshold_value": 2.0, "operator": "greater_equal"},
        )
    )

    exported = graph_export_payload(
        {
            "result_id": result["result_id"],
            "export": {"format": "graphml", "scope": "annotated"},
        }
    )

    assert exported.content_type == "application/graphml+xml"
    restored = nx.read_graphml(BytesIO(exported.content))
    edge_attributes = next(iter(restored.edges(data=True)))[2]
    assert any(name.endswith("_selected") for name in edge_attributes)


def test_webapp_guided_run_exposes_result_context_metadata() -> None:
    result = run_pipeline_from_payload(
        _guided_payload(
            method="edge_weight",
            filter_name="threshold",
            controls={
                "threshold_value": 2,
                "operator": "greater_equal",
                "drop_isolates": False,
            },
        )
    )
    extraction = result["extraction"]

    assert extraction["method"] == "edge_weight"
    assert extraction["filter"] == "threshold"
    assert extraction["target"] == "edge"
    assert extraction["output_type"] == "score"
    assert extraction["primary_statistic"] == "score"
    assert extraction["filter_statistic"] == "score"
    assert extraction["preferred_direction"] == "higher"
    assert extraction["selected_count"] == 2
    assert extraction["rejected_count"] == 1


def test_webapp_guided_run_disparity_alpha_control() -> None:
    result = run_pipeline_from_payload(
        _guided_payload(
            method="disparity",
            filter_name="significance",
            controls={
                "alpha": 1.0,
                "correction": "none",
                "pvalue_aggregation": "min",
                "leaf_policy": "ignore",
                "drop_isolates": False,
            },
        )
    )

    assert result["status"] == "ok"
    assert result["summary"]["method"] == "disparity"
    assert result["pipeline"]["filter"]["parameters"]["alpha"] == 1.0
    assert result["pipeline"]["method"]["parameters"]["pvalue_aggregation"] == "min"


def test_webapp_guided_disparity_accepts_average_endpoint_pvalue() -> None:
    result = run_pipeline_from_payload(
        _guided_payload(
            method="disparity",
            filter_name="significance",
            controls={
                "alpha": 1.0,
                "pvalue_aggregation": "average",
                "leaf_policy": "ignore",
            },
        )
    )

    assert result["status"] == "ok"
    assert result["pipeline"]["method"]["parameters"]["pvalue_aggregation"] == "average"


def test_webapp_guided_link_prediction_accepts_shortest_path() -> None:
    result = run_pipeline_from_payload(
        _guided_payload(
            method="link_prediction",
            filter_name="fraction",
            controls={
                "similarity": "shortest_path",
                "link_prediction_mode": "high_similarity",
                "fraction": 0.5,
                "tie_policy": "exact_stable",
            },
        )
    )

    assert result["status"] == "ok"
    assert result["pipeline"]["method"]["parameters"]["similarity"] == ("shortest_path")


@pytest.mark.parametrize(
    ("mode", "operator"),
    [
        ("high_similarity", "greater_equal"),
        ("high_similarity", "greater"),
        ("low_similarity", "less_equal"),
        ("low_similarity", "less"),
    ],
)
def test_webapp_guided_link_prediction_threshold_follows_backbone_mode(
    mode: str,
    operator: str,
) -> None:
    result = run_pipeline_from_payload(
        _guided_payload(
            method="link_prediction",
            filter_name="threshold",
            weight=None,
            controls={
                "similarity": "preferential_attachment",
                "link_prediction_mode": mode,
                "threshold_value": 4.0,
                "operator": operator,
            },
        )
    )

    assert result["status"] == "ok"
    assert result["pipeline"]["filter"]["parameters"]["operator"] == operator


@pytest.mark.parametrize(
    ("mode", "operator"),
    [
        ("high_similarity", "less_equal"),
        ("low_similarity", "greater_equal"),
        ("high_similarity", "equal"),
        ("low_similarity", "not_equal"),
    ],
)
def test_webapp_guided_link_prediction_threshold_rejects_conflicting_operator(
    mode: str,
    operator: str,
) -> None:
    with pytest.raises(ValidationError, match="operator must be one of"):
        run_pipeline_from_payload(
            _guided_payload(
                method="link_prediction",
                filter_name="threshold",
                weight=None,
                controls={
                    "similarity": "preferential_attachment",
                    "link_prediction_mode": mode,
                    "threshold_value": 4.0,
                    "operator": operator,
                },
            )
        )


def test_webapp_guided_pvalue_threshold_defaults_to_lower_values() -> None:
    result = run_pipeline_from_payload(
        _guided_payload(
            method="disparity",
            filter_name="threshold",
            controls={
                "threshold_value": 1.0,
                "pvalue_aggregation": "min",
                "leaf_policy": "ignore",
                "drop_isolates": False,
            },
        )
    )

    assert result["status"] == "ok"
    assert result["pipeline"]["filter"]["parameters"]["operator"] == "less"


def test_webapp_preview_detects_columns_and_counts() -> None:
    result = preview_payload(
        _guided_payload(
            method="edge_weight",
            filter_name="threshold",
            controls={},
        )
    )

    assert result["status"] == "ok"
    assert result["valid"] is True
    assert result["can_run"] is True
    assert result["suggested_columns"]["source"] == "source"
    assert result["suggested_columns"]["target"] == "target"
    assert result["suggested_columns"]["weight"] == "weight"
    assert result["row_count"] == 3
    assert result["node_count"] == 3
    assert result["edge_count"] == 3
    assert result["component_count"] == 1
    assert len(result["records"]) == 3


def test_webapp_preview_warns_when_likely_weight_is_not_selected() -> None:
    result = preview_payload(
        _guided_payload(
            method="edge_weight",
            filter_name="threshold",
            weight=None,
            controls={},
        )
    )

    assert result["status"] == "ok"
    assert result["valid"] is True
    assert result["can_run"] is True
    assert result["likely_weight_columns"] == ["weight"]
    assert "No weight column is selected" in result["warnings"][0]


def test_webapp_preview_blocks_required_weight_method_without_weight() -> None:
    result = preview_payload(
        _guided_payload(
            method="disparity",
            filter_name="significance",
            weight=None,
            controls={},
        )
    )

    assert result["status"] == "ok"
    assert result["valid"] is True
    assert result["can_run"] is False
    assert "requires a weight column" in result["errors"][0]


def test_webapp_graphml_preview_detects_attributes_and_counts() -> None:
    result = preview_payload(_graphml_guided_payload(weight=None))

    assert result["status"] == "ok"
    assert result["valid"] is True
    assert result["can_run"] is True
    assert result["data_mode"] == "graphml"
    assert result["suggested_columns"] == {
        "source": None,
        "target": None,
        "weight": "strength",
    }
    assert result["selected_columns"]["weight"] is None
    assert result["edge_attributes"] == ["relationship", "strength"]
    assert result["numeric_edge_attributes"] == ["strength"]
    assert result["node_attributes"] == ["group"]
    assert result["node_count"] == 3
    assert result["edge_count"] == 3
    assert result["component_count"] == 1
    assert len(result["records"]) == 3


def test_webapp_graphml_preview_counts_disconnected_components_and_isolates() -> None:
    graph = nx.Graph()
    graph.add_edge("a", "b", strength=2.0)
    graph.add_edge("c", "d", strength=1.0)
    graph.add_node("isolated")

    result = preview_payload(_graphml_guided_payload(graph=graph, weight=None))

    assert result["status"] == "ok"
    assert result["valid"] is True
    assert result["node_count"] == 5
    assert result["edge_count"] == 2
    assert result["component_count"] == 3


def test_webapp_graphml_run_uses_selected_numeric_edge_attribute() -> None:
    result = run_pipeline_from_payload(
        _graphml_guided_payload(
            controls={
                "threshold_value": 2,
                "operator": "greater_equal",
                "drop_isolates": False,
            }
        )
    )

    assert result["status"] == "ok"
    assert result["summary"]["original_node_count"] == 3
    assert result["summary"]["original_edge_count"] == 3
    assert result["summary"]["backbone_edge_count"] == 2
    assert result["pipeline"]["method"]["parameters"]["weight"] == "strength"
    assert all(row["weight"] == row["score"] for row in result["statistics"])


def test_webapp_graphml_preview_rejects_non_numeric_selected_weight() -> None:
    result = preview_payload(_graphml_guided_payload(weight="relationship"))

    assert result["status"] == "ok"
    assert result["valid"] is False
    assert "finite numeric value on every edge" in result["errors"][0]


def test_webapp_graphml_preview_reports_directed_connectivity() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b", strength=1.0)

    result = preview_payload(_graphml_guided_payload(graph=graph, method="lans"))

    assert result["status"] == "ok"
    assert result["valid"] is True
    assert result["can_run"] is True
    assert result["directed"] is True
    assert result["component_count"] == 1
    assert result["weakly_connected_component_count"] == 1
    assert result["strongly_connected_component_count"] == 2


def test_webapp_graphml_preview_allows_disparity_for_directed_graph() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b", strength=3.0)
    graph.add_edge("a", "c", strength=1.0)

    result = preview_payload(_graphml_guided_payload(graph=graph, method="disparity"))

    assert result["status"] == "ok"
    assert result["valid"] is True
    assert result["can_run"] is True
    assert result["directed"] is True


def test_webapp_graphml_preview_can_convert_directed_input_to_undirected() -> None:
    graph = nx.DiGraph()
    graph.add_edge("a", "b", strength=4.0, relationship="outbound")
    graph.add_edge("b", "a", strength=2.0, relationship="inbound")
    graph.add_edge("b", "c", strength=1.0, relationship="one-way")

    result = preview_payload(
        _graphml_guided_payload(
            graph=graph,
            method="disparity",
            direction_mode="undirected",
            reciprocal_merge="sum",
        )
    )

    assert result["status"] == "ok"
    assert result["valid"] is True
    assert result["can_run"] is True
    assert result["source_directed"] is True
    assert result["directed"] is False
    assert result["edge_count"] == 2
    assert result["component_count"] == 1
    assert result["direction_handling"] == {
        "mode": "undirected",
        "weight_attribute": "strength",
        "reciprocal_merge": "sum",
        "original_arc_count": 3,
        "undirected_edge_count": 2,
        "reciprocal_pair_count": 1,
        "one_way_edge_count": 1,
        "source_directed": True,
        "output_directed": False,
    }
    assert "Converted the directed network" in result["warnings"][0]


def test_webapp_directed_csv_conversion_is_used_for_pipeline_run() -> None:
    payload = _guided_payload(
        method="edge_weight",
        filter_name="threshold",
        controls={"threshold_value": 3.0, "operator": "greater_equal"},
        directed=True,
        direction_mode="undirected",
        reciprocal_merge="mean",
    )
    payload["csv_text"] = "source,target,weight\na,b,4\nb,a,2\nb,c,1\n"

    result = run_pipeline_from_payload(payload)

    assert result["status"] == "ok"
    assert result["network"]["directed"] is False
    assert result["summary"]["original_edge_count"] == 2
    assert result["summary"]["backbone_edge_count"] == 1
    assert result["direction_conversion"]["reciprocal_merge"] == "mean"
    assert result["resolved_config"]["direction_conversion"] == {
        "mode": "undirected",
        "weight_attribute": "weight",
        "reciprocal_merge": "mean",
    }
    assert "Converted the directed network" in result["warnings"][0]


def test_webapp_direction_conversion_requires_explicit_merge_policy() -> None:
    payload = _guided_payload(
        method="edge_weight",
        filter_name="threshold",
        controls={"threshold_value": 0.0, "operator": "greater_equal"},
        directed=True,
        direction_mode="undirected",
        reciprocal_merge=None,
    )

    result = preview_payload(payload)

    assert result["valid"] is False
    assert "reciprocal_merge must be a non-empty string" in result["errors"][0]


def test_webapp_unweighted_direction_conversion_needs_no_merge_policy() -> None:
    payload = _guided_payload(
        method="node_degree",
        filter_name="fraction",
        controls={"fraction": 0.5},
        weight=None,
        directed=True,
        direction_mode="undirected",
        reciprocal_merge=None,
    )
    payload["csv_text"] = "source,target\na,b\nb,a\nb,c\n"

    result = preview_payload(payload)

    assert result["valid"] is True
    assert result["can_run"] is True
    assert result["directed"] is False
    assert result["edge_count"] == 2
    assert result["direction_handling"]["weight_attribute"] is None
    assert result["direction_handling"]["reciprocal_merge"] is None


def test_webapp_directed_csv_run_preserves_reciprocal_arcs() -> None:
    payload = _guided_payload(
        method="link_salience",
        filter_name="threshold",
        controls={"threshold_value": 0.0, "operator": "greater_equal"},
        weight=None,
        directed=True,
    )
    payload["csv_text"] = "source,target\na,b\nb,a\nb,c\n"

    result = run_pipeline_from_payload(payload)

    assert result["status"] == "ok"
    assert result["network"]["directed"] is True
    assert result["summary"]["weakly_connected_component_count"] == 1
    assert result["summary"]["strongly_connected_component_count"] == 2
    assert result["graph"]["directed"] is True
    assert {(edge["source"], edge["target"]) for edge in result["graph"]["edges"]} == {
        ("a", "b"),
        ("b", "a"),
        ("b", "c"),
    }


def test_webapp_directed_csv_runs_link_prediction_without_projection() -> None:
    payload = _guided_payload(
        method="link_prediction",
        filter_name="fraction",
        controls={
            "similarity": "shortest_path",
            "link_prediction_mode": "high_similarity",
            "fraction": 0.5,
            "tie_policy": "exact_stable",
        },
        weight=None,
        directed=True,
    )
    payload["csv_text"] = "source,target\na,b\nb,a\na,c\nc,b\n"

    result = run_pipeline_from_payload(payload)

    assert result["status"] == "ok"
    assert result["network"]["directed"] is True
    assert result["pipeline"]["method"]["parameters"]["similarity"] == ("shortest_path")
    assert any("forward replacement paths" in warning for warning in result["warnings"])


def test_webapp_temporal_preview_aggregates_repeated_pairs() -> None:
    result = preview_payload(_temporal_guided_payload(method="edge_weight"))

    assert result["status"] == "ok"
    assert result["valid"] is True
    assert result["can_run"] is True
    assert result["data_mode"] == "temporal"
    assert result["row_count"] == 5
    assert result["event_count"] == 5
    assert result["node_count"] == 4
    assert result["edge_count"] == 3
    assert result["component_count"] == 1
    assert result["weighted"] is True
    assert result["selected_columns"]["time"] == "time"
    assert result["selected_columns"]["event_weight"] == "magnitude"
    assert result["temporal_aggregation"]["weighting"] == "asf"
    assert result["positive_integer_weights"] is False


def test_webapp_preview_recognizes_whole_number_temporal_weights() -> None:
    payload = _temporal_guided_payload(method="marginal_likelihood")
    payload["temporal"] = {"weighting": "baseline"}

    result = preview_payload(payload)

    assert result["valid"] is True
    assert result["positive_integer_weights"] is True


def test_webapp_directed_temporal_preview_preserves_reciprocal_arcs() -> None:
    payload = _temporal_guided_payload(method="lans", directed=True)

    result = preview_payload(payload)

    assert result["status"] == "ok"
    assert result["valid"] is True
    assert result["can_run"] is True
    assert result["source_directed"] is True
    assert result["directed"] is True
    assert result["edge_count"] == 4
    assert result["weakly_connected_component_count"] == 1
    assert result["strongly_connected_component_count"] == 3
    assert result["temporal_aggregation"]["directed"] is True


def test_webapp_directed_temporal_run_preserves_arc_direction() -> None:
    payload = _temporal_guided_payload(
        method="link_salience",
        controls={"threshold_value": 0.0, "operator": "greater_equal"},
        directed=True,
    )

    result = run_pipeline_from_payload(payload)

    assert result["status"] == "ok"
    assert result["network"]["directed"] is True
    assert result["summary"]["original_edge_count"] == 4
    assert result["graph"]["directed"] is True
    assert {(edge["source"], edge["target"]) for edge in result["graph"]["edges"]} == {
        ("alice", "bob"),
        ("bob", "alice"),
        ("alice", "carol"),
        ("carol", "dana"),
    }


def test_webapp_directed_temporal_run_supports_disparity() -> None:
    payload = _temporal_guided_payload(
        method="disparity",
        filter_name="significance",
        controls={"alpha": 1.0},
        directed=True,
    )

    preview = preview_payload(payload)
    result = run_pipeline_from_payload(payload)

    assert preview["can_run"] is True
    assert preview["directed"] is True
    assert result["status"] == "ok"
    assert result["summary"]["method"] == "disparity"
    assert result["network"]["directed"] is True
    assert result["pipeline"]["method"]["parameters"]["weight"] == "weight"


def test_webapp_directed_temporal_run_supports_undirected_projection() -> None:
    payload = _temporal_guided_payload(
        method="disparity",
        filter_name="significance",
        controls={"alpha": 1.0},
        directed=True,
        direction_mode="undirected",
        reciprocal_merge="sum",
    )
    payload["temporal"]["weighting"] = "baseline"
    payload["temporal"]["parameters"] = {}

    preview = preview_payload(payload)
    result = run_pipeline_from_payload(payload)

    assert preview["valid"] is True
    assert preview["can_run"] is True
    assert preview["source_directed"] is True
    assert preview["directed"] is False
    assert preview["edge_count"] == 3
    assert preview["direction_handling"]["weight_attribute"] == "weight"
    assert preview["direction_handling"]["reciprocal_merge"] == "sum"
    assert result["status"] == "ok"
    assert result["network"]["directed"] is False
    assert result["direction_conversion"]["original_arc_count"] == 4
    assert result["direction_conversion"]["undirected_edge_count"] == 3


def test_webapp_temporal_run_uses_canonical_aggregate_weight() -> None:
    result = run_pipeline_from_payload(
        _temporal_guided_payload(
            method="edge_weight",
            filter_name="threshold",
            controls={
                "threshold_value": 1.0,
                "operator": "greater_equal",
                "drop_isolates": False,
            },
        )
    )

    assert result["status"] == "ok"
    assert result["pipeline"]["method"]["parameters"]["weight"] == "weight"
    assert result["temporal_aggregation"]["weighting"] == "asf"
    assert result["temporal_aggregation"]["weighting_parameters"] == {
        "p": 3.0,
        "q": 0.0,
        "a": 5.0,
    }
    assert result["resolved_config"]["temporal_aggregation"]["weighting"] == {
        "name": "asf",
        "parameters": {"p": 3.0, "q": 0.0, "a": 5.0},
    }
    assert result["resolved_config"]["pipeline"] == result["pipeline"]


def test_webapp_temporal_run_supports_persistent_elapsed_weighting() -> None:
    payload = _temporal_guided_payload(method="edge_weight")
    payload["temporal"] = {
        "weighting": "persistent_weibull",
        "parameters": {
            "persistent_level": 0.2,
            "scale": 2.0,
            "shape": 1.5,
        },
        "evaluation_time": 4,
        "time_unit": 0.5,
        "snapshot_size": None,
        "snapshot_origin": None,
        "zero_weight_policy": "drop",
    }

    result = run_pipeline_from_payload(payload)

    assert result["status"] == "ok"
    aggregation = result["temporal_aggregation"]
    assert aggregation["weighting"] == "persistent_weibull"
    assert aggregation["age_basis"] == "elapsed"
    assert aggregation["time_unit"] == 0.5
    timing = result["resolved_config"]["temporal_aggregation"]["timing"]
    assert timing["time_unit"] == 0.5
    assert timing["snapshot_size"] is None


def test_webapp_temporal_unit_events_satisfy_weighted_method() -> None:
    payload = _temporal_guided_payload(
        method="disparity",
        filter_name="significance",
        event_weight=None,
        controls={"alpha": 1.0},
    )

    preview = preview_payload(payload)
    result = run_pipeline_from_payload(payload)

    assert preview["can_run"] is True
    assert preview["selected_columns"]["event_weight"] is None
    assert result["status"] == "ok"
    assert result["pipeline"]["method"]["parameters"]["weight"] == "weight"


def test_webapp_guided_run_fraction_slider_value() -> None:
    result = run_pipeline_from_payload(
        _guided_payload(
            method="edge_weight",
            filter_name="fraction",
            controls={
                "fraction": 0.34,
                "tie_policy": "include_all_ties",
                "drop_isolates": False,
            },
        )
    )

    assert result["status"] == "ok"
    assert result["summary"]["backbone_edge_count"] == 2
    assert result["pipeline"]["filter"]["parameters"]["fraction"] == 0.34


def test_webapp_guided_run_structural_method_default_filter() -> None:
    result = run_pipeline_from_payload(
        _guided_payload(
            method="maximum_spanning_forest",
            filter_name="default",
            controls={"drop_isolates": False},
        )
    )

    assert result["status"] == "ok"
    assert result["pipeline"]["filter"]["name"] == "default"
    assert result["summary"]["backbone_edge_count"] == 2


def test_webapp_guided_link_prediction_low_similarity_maps_to_lower_fraction() -> None:
    result = run_pipeline_from_payload(
        _guided_payload(
            method="link_prediction",
            filter_name="fraction",
            weight=None,
            controls={
                "similarity": "preferential_attachment",
                "link_prediction_mode": "low_similarity",
                "fraction": 0.5,
                "tie_policy": "include_all_ties",
                "drop_isolates": False,
            },
        )
    )

    assert result["status"] == "ok"
    assert result["pipeline"]["filter"]["parameters"]["direction"] == "lower"


def test_webapp_http_smoke_ui_schema_and_run() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), NetboneWebHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        schema = _get_json(f"http://127.0.0.1:{port}/api/ui-schema")
        preview = _post_json(
            f"http://127.0.0.1:{port}/api/preview",
            _guided_payload(
                method="edge_weight",
                filter_name="threshold",
                controls={},
            ),
        )
        score_request = _guided_payload(
            method="edge_weight",
            filter_name="threshold",
            controls={},
        )
        score_result = _post_json(
            f"http://127.0.0.1:{port}/api/score",
            score_request,
        )
        filter_request = _guided_payload(
            method="edge_weight",
            filter_name="threshold",
            controls={
                "threshold_value": 2,
                "operator": "greater_equal",
                "drop_isolates": False,
            },
        )
        filter_request["score_id"] = score_result["score_id"]
        filter_preview = _post_json(
            f"http://127.0.0.1:{port}/api/filter-preview",
            filter_request,
        )
        filter_result = _post_json(
            f"http://127.0.0.1:{port}/api/filter",
            filter_request,
        )
        result = _post_json(
            f"http://127.0.0.1:{port}/api/run",
            _guided_payload(
                method="edge_weight",
                filter_name="threshold",
                controls={
                    "threshold_value": 2,
                    "operator": "greater_equal",
                    "drop_isolates": False,
                },
            ),
        )
        comparison = _post_json(
            f"http://127.0.0.1:{port}/api/compare",
            {
                "results": [
                    {"result_id": filter_result["result_id"], "label": "Filtered"},
                    {"result_id": result["result_id"], "label": "One shot"},
                ]
            },
        )
        sweep_request = _guided_payload(
            method="edge_weight",
            filter_name="threshold",
            controls={"threshold_value": 2, "operator": "greater_equal"},
        )
        sweep_request.update(
            {
                "score_id": score_result["score_id"],
                "variation": {
                    "scope": "filter",
                    "parameter": "value",
                    "values": [1, 2, 4],
                },
                "metrics": ["edge_count"],
            }
        )
        sweep = _post_json(
            f"http://127.0.0.1:{port}/api/sweep",
            sweep_request,
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert len(schema["methods"]) == len(nb.list_methods())
    assert preview["status"] == "ok"
    assert preview["can_run"] is True
    assert score_result["status"] == "ok"
    assert str(score_result["score_id"]).startswith("score-")
    assert filter_preview["status"] == "ok"
    assert filter_preview["node_coverage_count"] == 3
    assert filter_result["status"] == "ok"
    assert filter_result["summary"]["backbone_edge_count"] == 2
    assert str(filter_result["result_id"]).startswith("result-")
    assert result["status"] == "ok"
    assert result["summary"]["backbone_edge_count"] == 2
    assert str(result["result_id"]).startswith("result-")
    assert comparison["status"] == "ok"
    assert any(
        row["metric"] == "score_spearman" for row in comparison["pairwise_metrics"]
    )
    assert sweep["status"] == "ok"
    assert len(sweep["runs"]) == 3
    assert sweep["score_cache_hits"] == 2


def test_webapp_http_accepts_local_requests_larger_than_five_megabytes() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), NetboneWebHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        payload = _guided_payload(
            method="edge_weight",
            filter_name="threshold",
            controls={},
        )
        payload["local_padding"] = "x" * (5 * 1024 * 1024 + 1)
        result = _post_json(f"http://127.0.0.1:{port}/api/preview", payload)
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert result["status"] == "ok"
    assert result["valid"] is True


def test_webapp_http_graph_export_download() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), NetboneWebHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        score_result = _post_json(
            f"http://127.0.0.1:{port}/api/score",
            _guided_payload(method="edge_weight", filter_name="threshold", controls={}),
        )
        payload = _guided_payload(
            method="edge_weight",
            filter_name="threshold",
            controls={"threshold_value": 2, "operator": "greater_equal"},
        )
        payload["score_id"] = score_result["score_id"]
        payload["export"] = {"format": "graphml", "scope": "annotated"}
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/export",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            content = response.read()
            content_type = response.headers.get_content_type()
            disposition = response.headers["Content-Disposition"]
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert content_type == "application/graphml+xml"
    assert disposition == (
        'attachment; filename="netbone-edge-weight-annotated.graphml"'
    )
    assert b"#0072B2" in content
    assert b"#D9D9D9" in content


def test_webapp_run_pipeline_rejects_non_object_payload() -> None:
    with pytest.raises(ValidationError, match="JSON object"):
        run_pipeline_from_payload([])


def test_webapp_http_extraction_report_and_bundle() -> None:
    payload = _temporal_guided_payload(
        method="edge_weight", controls={"threshold_value": 2}
    )
    payload["context"] = "Collaboration over time"
    result = run_pipeline_from_payload(payload)
    server = ThreadingHTTPServer(("127.0.0.1", 0), NetboneWebHandler)
    url = f"http://127.0.0.1:{server.server_address[1]}/api/export-result"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    exports: dict[str, bytes] = {}
    try:
        for file_format, content_type, suffix in (
            ("markdown", "text/markdown", "report.md"),
            ("zip", "application/zip", "experiment.zip"),
        ):
            request = urllib.request.Request(
                url,
                data=json.dumps(
                    {"result_id": result["result_id"], "format": file_format}
                ).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                assert response.headers.get_content_type() == content_type
                assert response.headers["Content-Disposition"] == (
                    f'attachment; filename="netbone-edge-weight-{suffix}"'
                )
                exports[file_format] = response.read()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert exports["markdown"].startswith(b"# Netbone Backbone Report")
    with ZipFile(BytesIO(exports["zip"])) as bundle:
        manifest = json.loads(bundle.read("manifest.json"))
        assert manifest["subject_type"] == "backbone_result"
        assert set(manifest["files"].values()) <= set(bundle.namelist())
        assert bundle.read("report.md") == exports["markdown"]
        assert json.loads(bundle.read("pipeline.json")) == result["pipeline"]
        assert json.loads(bundle.read("web_settings.json")) == {
            "context": "Collaboration over time",
            "resolved_config": result["resolved_config"],
        }
        assert "temporal_aggregation.json" in bundle.namelist()
        assert "tables/method_statistics.csv" in bundle.namelist()
        assert "graphs/backbone.graphml" in bundle.namelist()


def test_webapp_result_export_rejects_unknown_formats_and_expired_results() -> None:
    with pytest.raises(ValidationError, match="format must be"):
        result_export_payload({"format": "pdf", "result_id": "expired-test-result"})
    with pytest.raises(ValidationError, match="Extract the backbone again"):
        result_export_payload({"format": "zip", "result_id": "expired-test-result"})


def test_webapp_error_payload_is_json_compatible() -> None:
    error = ValidationError("Missing edge list.")

    payload = error_payload(error)

    assert payload == {
        "status": "error",
        "error": "ValidationError",
        "message": "Missing edge list.",
    }


def _guided_payload(
    *,
    method: str,
    filter_name: str,
    controls: Mapping[str, object],
    weight: str | None = "weight",
    directed: bool = False,
    direction_mode: str = "preserve",
    reciprocal_merge: str | None = "sum",
) -> dict[str, object]:
    return {
        "csv_text": WEIGHTED_CSV,
        "source": "source",
        "target": "target",
        "weight": weight,
        "delimiter": ",",
        "directed": directed,
        "direction_mode": direction_mode,
        "reciprocal_merge": reciprocal_merge,
        "context": "test web run",
        "guided": {
            "method": method,
            "filter": filter_name,
            "controls": dict(controls),
        },
    }


def _temporal_guided_payload(
    *,
    method: str,
    filter_name: str = "threshold",
    event_weight: str | None = "magnitude",
    controls: Mapping[str, object] | None = None,
    directed: bool = False,
    direction_mode: str = "preserve",
    reciprocal_merge: str | None = "sum",
) -> dict[str, object]:
    return {
        "data_mode": "temporal",
        "csv_text": TEMPORAL_CSV,
        "source": "source",
        "target": "target",
        "time": "time",
        "event_weight": event_weight,
        "weight": None,
        "delimiter": ",",
        "directed": directed,
        "direction_mode": direction_mode,
        "reciprocal_merge": reciprocal_merge,
        "context": "test temporal web run",
        "temporal": {
            "weighting": "asf",
            "parameters": {"p": 3, "q": 0, "a": 5},
            "evaluation_time": None,
            "time_unit": None,
            "snapshot_size": None,
            "snapshot_origin": None,
            "zero_weight_policy": "drop",
        },
        "guided": {
            "method": method,
            "filter": filter_name,
            "controls": dict(controls or {}),
        },
    }


def _graphml_guided_payload(
    *,
    method: str = "edge_weight",
    filter_name: str = "threshold",
    weight: str | None = "strength",
    controls: Mapping[str, object] | None = None,
    graph: nx.Graph | None = None,
    direction_mode: str = "preserve",
    reciprocal_merge: str | None = "sum",
) -> dict[str, object]:
    if graph is None:
        graph = nx.Graph()
        graph.add_node("a", group="one")
        graph.add_node("b", group="one")
        graph.add_node("c", group="two")
        graph.add_edge("a", "b", strength=4.0, relationship="strong")
        graph.add_edge("b", "c", strength=2.0, relationship="medium")
        graph.add_edge("a", "c", strength=1.0, relationship="weak")
    stream = BytesIO()
    nx.write_graphml(graph, stream)
    graphml_text = stream.getvalue().decode("utf-8")
    return {
        "data_mode": "graphml",
        "graphml_text": graphml_text,
        "source": None,
        "target": None,
        "weight": weight,
        "direction_mode": direction_mode,
        "reciprocal_merge": reciprocal_merge,
        "context": "test GraphML web run",
        "guided": {
            "method": method,
            "filter": filter_name,
            "controls": dict(controls or {}),
        },
    }


def _get_json(url: str) -> Mapping[str, Any]:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload: Mapping[str, object]) -> Mapping[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _static_text(filename: str) -> str:
    return (
        resources.files("netbone.webapp")
        .joinpath("static", filename)
        .read_text(encoding="utf-8")
    )


def _frontend_text(*parts: str) -> str:
    return (
        Path(__file__)
        .resolve()
        .parents[1]
        .joinpath("web", "src", *parts)
        .read_text(encoding="utf-8")
    )


def _retained_count(records: Iterable[Mapping[str, object]]) -> int:
    return sum(1 for record in records if record["retained"] is True)


def _metric_record(
    records: Iterable[Mapping[str, Any]],
    *,
    metric: str,
    result: str | None = None,
) -> Mapping[str, Any]:
    for record in records:
        if record["metric"] == metric and (
            result is None or record.get("result") == result
        ):
            return record
    raise AssertionError(f"Metric record {metric!r} was not returned.")


def _method_cards(schema: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return list(schema["methods"])


def _control_names(controls: Iterable[Mapping[str, object]]) -> set[str]:
    return {str(control["name"]) for control in controls}


def _option_values(control: Mapping[str, Any]) -> set[str]:
    return {str(option["value"]) for option in control["options"]}


def _controls_by_name(
    controls: Iterable[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    return {str(control["name"]): control for control in controls}


def _all_controls(schema: Mapping[str, Any]) -> Iterable[Mapping[str, object]]:
    controls = schema["controls"]
    yield from controls["data"]
    for group_controls in controls["filters"].values():
        yield from group_controls
    for group_controls in controls["methods"].values():
        yield from group_controls
    for group_controls in schema["temporal"]["controls"].values():
        yield from group_controls


def test_webapp_live_graph_matches_saved_backbone_and_config() -> None:
    payload = _guided_payload(
        method="link_salience",
        filter_name="threshold",
        controls={
            "threshold_value": 0.5,
            "operator": "greater_equal",
            "drop_isolates": True,
        },
        weight=None,
        directed=True,
    )
    payload["csv_text"] = "source,target\na,b\nb,a\nb,c\nd,a\n"
    payload["score_id"] = score_payload(payload)["score_id"]

    draft = filter_preview_payload(payload)
    saved = filter_payload(payload)

    assert draft["graph"] == saved["graph"]
    assert draft["resolved_config"] == saved["resolved_config"]
    assert draft["graph"]["directed"] is True
    assert draft["backbone_edge_count"] == 2
    assert draft["backbone_component_count"] == 1
    assert {node["id"]: node["component"] for node in draft["graph"]["nodes"]} == {
        "a": 1,
        "b": 1,
        "c": 1,
        "d": None,
    }
    assert all("weight" not in row for row in saved["statistics"])
    assert draft["graph"]["truncated"] is False
    assert {
        (arc["source"], arc["target"]): arc["retained"]
        for arc in draft["graph"]["edges"]
    } == {("a", "b"): True, ("b", "a"): False, ("b", "c"): True, ("d", "a"): False}
    assert {node["id"] for node in draft["graph"]["nodes"] if node["retained"]} == {
        "a",
        "b",
        "c",
    }


def test_webapp_live_graph_is_bounded_without_truncating_retention_counts() -> None:
    payload = _guided_payload(
        method="edge_weight",
        filter_name="threshold",
        controls={"threshold_value": 1, "operator": "greater_equal"},
    )
    edges = [(a, b) for a in range(48) for b in range(a + 1, 48)]
    edges.extend((a, a + 1) for a in range(47, 80))
    payload["csv_text"] = "source,target,weight\n" + "".join(
        f"n{a:03},n{b:03},1\n" for a, b in edges
    )
    payload["score_id"] = score_payload(payload)["score_id"]

    draft = filter_preview_payload(payload)
    sampled_graph = draft["graph"]
    sampled_nodes = {node["id"] for node in sampled_graph["nodes"]}

    assert draft["original_node_count"] == 81
    assert draft["selected_item_count"] == len(edges)
    assert draft["backbone_edge_count"] == len(edges)
    assert draft["backbone_component_count"] == 1
    assert draft["node_coverage_count"] == 81
    assert sampled_graph["truncated"] is True
    assert len(sampled_nodes) == 80
    assert len(sampled_graph["edges"]) == 1000
    assert all(
        edge["retained"]
        and edge["source"] in sampled_nodes
        and edge["target"] in sampled_nodes
        for edge in sampled_graph["edges"]
    )
    assert filter_preview_payload(payload)["graph"] == sampled_graph


def test_webapp_reads_space_separated_edge_and_event_lists() -> None:
    static = _csv_payload_with_delimiter(
        'source  target\tweight\nalice bob 4\n"New York" carol 1\n\n  carol dana 2\n'
    )
    temporal = _temporal_guided_payload(method="edge_weight")
    temporal["csv_text"] = str(temporal["csv_text"]).replace(",", "   ")
    temporal["delimiter"] = " "

    static_preview = preview_payload(static)
    temporal_preview = preview_payload(temporal)
    comma_preview = preview_payload(_temporal_guided_payload(method="edge_weight"))

    assert static_preview["valid"] is True
    assert static_preview["edge_count"] == 3
    assert static_preview["headers"] == ["source", "target", "weight"]
    assert temporal_preview["valid"] is True
    assert temporal_preview["edge_count"] == comma_preview["edge_count"]
    assert temporal_preview["event_count"] == comma_preview["event_count"]
    delimiter = next(
        control
        for control in ui_schema_payload()["controls"]["data"]
        if control["name"] == "delimiter"
    )
    assert {"value": " ", "label": "Space"} in delimiter["options"]


def test_webapp_space_delimiter_rejects_rows_with_extra_values() -> None:
    preview = preview_payload(
        _csv_payload_with_delimiter("source target weight\na b 1 9\n")
    )

    assert preview["valid"] is False
    assert "row 2 has 4 values" in str(preview["errors"])


def _csv_payload_with_delimiter(
    csv_text: str, delimiter: str = " "
) -> dict[str, object]:
    return {
        "csv_text": csv_text,
        "source": "source",
        "target": "target",
        "weight": "weight",
        "delimiter": delimiter,
        "method": {"name": "edge_weight", "parameters": {"weight": "weight"}},
        "filter": {"name": "fraction", "parameters": {"fraction": 0.5}},
    }
