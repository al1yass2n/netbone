from __future__ import annotations

import json
import math

import pandas as pd
import pytest

import netbone as nb


def _write_events(tmp_path, rows: list[dict[str, object]]):
    path = tmp_path / "events.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_temporal_loader_keeps_repeated_pairs_and_removes_self_interactions(
    tmp_path,
) -> None:
    path = _write_events(
        tmp_path,
        [
            {"source": "a", "target": "b", "time": 0, "magnitude": 2},
            {"source": "b", "target": "a", "time": 1, "magnitude": 3},
            {"source": "a", "target": "c", "time": 2, "magnitude": 4},
            {"source": "c", "target": "c", "time": 2, "magnitude": 9},
        ],
    )

    with pytest.warns(UserWarning, match="Removed 1 temporal self-interaction"):
        temporal = nb.from_temporal_edgelist(path, event_weight="magnitude")

    assert temporal.event_count == 3
    assert temporal.node_count == 3
    assert temporal.directed is False
    assert temporal.nodes == ("a", "b", "c")
    assert temporal.time_kind == "numeric"
    assert temporal.observed_start == 0
    assert temporal.observed_end == 2
    assert temporal.metadata["self_interaction_count"] == 1
    assert temporal.metadata["temporal_source_path"] == str(path)
    assert temporal.metadata["temporal_delimiter"] == ","
    assert temporal.events["event_weight"].tolist() == [2.0, 3.0, 4.0]


def test_removed_self_interaction_does_not_change_observed_time_range(tmp_path) -> None:
    path = _write_events(
        tmp_path,
        [
            {"source": "a", "target": "b", "time": 1},
            {"source": "c", "target": "c", "time": 100},
        ],
    )

    with pytest.warns(UserWarning, match="Removed 1 temporal self-interaction"):
        temporal = nb.from_temporal_edgelist(path)

    assert temporal.observed_start == 1
    assert temporal.observed_end == 1
    network = nb.aggregate_temporal(temporal, weighting="baseline")
    assert network.to_original_graph().edges["a", "b"]["weight"] == 1.0


def test_baseline_aggregation_sums_event_weights_and_preserves_provenance(
    tmp_path,
) -> None:
    path = _write_events(
        tmp_path,
        [
            {"source": "a", "target": "b", "time": 0, "magnitude": 2},
            {"source": "b", "target": "a", "time": 1, "magnitude": 3},
            {"source": "a", "target": "c", "time": 2, "magnitude": 4},
        ],
    )
    temporal = nb.from_temporal_edgelist(path, event_weight="magnitude")

    network = nb.aggregate_temporal(temporal, weighting="baseline")
    graph = network.to_original_graph()

    assert graph.is_directed() is False
    assert graph.edges["a", "b"] == {
        "weight": 5.0,
        "temporal_event_count": 2,
        "temporal_event_weight_sum": 5.0,
        "temporal_first_time": 0,
        "temporal_last_time": 1,
    }
    assert graph.edges["a", "c"]["weight"] == 4.0
    aggregation = network.metadata["temporal_aggregation"]
    assert isinstance(aggregation, dict)
    assert aggregation["weighting"] == "baseline"
    assert aggregation["evaluation_time"] == 2
    assert aggregation["included_event_count"] == 3
    assert aggregation["future_event_count"] == 0


def test_directed_temporal_aggregation_preserves_reciprocal_arcs(tmp_path) -> None:
    path = _write_events(
        tmp_path,
        [
            {"source": "a", "target": "b", "time": 0, "magnitude": 2},
            {"source": "b", "target": "a", "time": 1, "magnitude": 3},
            {"source": "a", "target": "b", "time": 2, "magnitude": 4},
            {"source": "b", "target": "c", "time": 3, "magnitude": 5},
        ],
    )

    temporal = nb.from_temporal_edgelist(
        path,
        event_weight="magnitude",
        directed=True,
    )
    network = nb.aggregate_temporal(temporal, weighting="baseline")
    graph = network.to_original_graph()

    assert temporal.directed is True
    assert temporal.summary()["directed"] is True
    assert temporal.metadata["temporal_directed"] is True
    assert graph.is_directed()
    assert set(graph.edges) == {("a", "b"), ("b", "a"), ("b", "c")}
    assert graph.edges["a", "b"]["weight"] == 6.0
    assert graph.edges["a", "b"]["temporal_event_count"] == 2
    assert graph.edges["b", "a"]["weight"] == 3.0
    assert network.metadata["temporal_aggregation"]["directed"] is True


def test_temporal_loader_rejects_non_boolean_directed_option(tmp_path) -> None:
    path = _write_events(
        tmp_path,
        [{"source": "a", "target": "b", "time": 0}],
    )

    with pytest.raises(nb.ValidationError, match="directed.*boolean"):
        nb.from_temporal_edgelist(path, directed="yes")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("weighting", "parameters", "expected"),
    [
        (
            "asf",
            {"p": 3.0, "q": 0.0, "a": 5.0},
            1.0 / (1.0 + math.exp(2.0 / 3.0 - 5.0)) + 1.0 / (1.0 + math.exp(-5.0)),
        ),
        (
            "persistent_exponential",
            {"persistent_level": 0.2, "decay_rate": 0.5},
            0.2 + 0.8 * math.exp(-1.0) + 1.0,
        ),
        (
            "persistent_weibull",
            {"persistent_level": 0.2, "scale": 2.0, "shape": 2.0},
            0.2 + 0.8 * math.exp(-1.0) + 1.0,
        ),
        (
            "persistent_log_logistic",
            {"persistent_level": 0.2, "scale": 2.0, "shape": 2.0},
            0.2 + 0.8 / 2.0 + 1.0,
        ),
    ],
)
def test_temporal_weighting_formulas_are_applied_per_event(
    tmp_path,
    weighting: str,
    parameters: dict[str, object],
    expected: float,
) -> None:
    path = _write_events(
        tmp_path,
        [
            {"source": "a", "target": "b", "time": 0},
            {"source": "a", "target": "b", "time": 2},
        ],
    )
    temporal = nb.from_temporal_edgelist(path)

    network = nb.aggregate_temporal(
        temporal,
        weighting=weighting,
        evaluation_time=2,
        **parameters,
    )

    assert network.to_original_graph().edges["a", "b"]["weight"] == pytest.approx(
        expected
    )


def test_persistent_weighting_uses_exact_numeric_ages_and_stores_components(
    tmp_path,
) -> None:
    path = _write_events(
        tmp_path,
        [
            {"source": "a", "target": "b", "time": 0.25, "magnitude": 2},
            {"source": "b", "target": "a", "time": 1.25, "magnitude": 3},
        ],
    )
    temporal = nb.from_temporal_edgelist(path, event_weight="magnitude")

    network = nb.aggregate_temporal(
        temporal,
        weighting="persistent_exponential",
        evaluation_time=2.25,
        time_unit=0.5,
        persistent_level=0.25,
        decay_rate=0.5,
    )
    edge = network.to_original_graph().edges["a", "b"]
    expected_persistent = 0.25 * (2.0 + 3.0)
    expected_transient = 0.75 * (
        2.0 * math.exp(-0.5 * 4.0) + 3.0 * math.exp(-0.5 * 2.0)
    )

    assert edge["temporal_persistent_contribution"] == pytest.approx(
        expected_persistent
    )
    assert edge["temporal_transient_contribution"] == pytest.approx(expected_transient)
    assert edge["weight"] == pytest.approx(expected_persistent + expected_transient)
    aggregation = network.metadata["temporal_aggregation"]
    assert isinstance(aggregation, dict)
    assert aggregation["age_basis"] == "elapsed"
    assert aggregation["evaluation_snapshot"] is None
    assert aggregation["time_unit"] == 0.5


def test_persistent_weighting_uses_fractional_datetime_age(tmp_path) -> None:
    path = _write_events(
        tmp_path,
        [
            {"source": "a", "target": "b", "time": "2026-01-01T00:00:00Z"},
            {"source": "a", "target": "b", "time": "2026-01-01T12:00:00Z"},
        ],
    )
    temporal = nb.from_temporal_edgelist(path)

    network = nb.aggregate_temporal(
        temporal,
        weighting="persistent_log_logistic",
        evaluation_time="2026-01-02T00:00:00Z",
        time_unit="1d",
        persistent_level=0.1,
        scale=1.0,
        shape=2.0,
    )

    expected = 0.1 + 0.9 / 2.0 + 0.1 + 0.9 / 1.25
    edge = network.to_original_graph().edges["a", "b"]
    assert edge["weight"] == pytest.approx(expected)
    aggregation = network.metadata["temporal_aggregation"]
    assert isinstance(aggregation, dict)
    assert aggregation["time_unit"] == "P1DT0H0M0S"


def test_raw_numeric_times_are_binned_into_discrete_snapshots(tmp_path) -> None:
    path = _write_events(
        tmp_path,
        [
            {"source": "a", "target": "b", "time": 0},
            {"source": "a", "target": "b", "time": 39},
            {"source": "a", "target": "c", "time": 40},
        ],
    )
    temporal = nb.from_temporal_edgelist(path)

    network = nb.aggregate_temporal(
        temporal,
        weighting="asf",
        evaluation_time=79,
        snapshot_size=40,
        snapshot_origin=0,
        p=1.0,
        q=0.0,
        a=0.0,
    )
    graph = network.to_original_graph()

    assert graph.edges["a", "b"]["weight"] == pytest.approx(2.0 / (1.0 + math.exp(1.0)))
    assert graph.edges["a", "c"]["weight"] == pytest.approx(0.5)
    aggregation = network.metadata["temporal_aggregation"]
    assert isinstance(aggregation, dict)
    assert aggregation["evaluation_snapshot"] == 1
    assert aggregation["snapshot_size"] == 40
    assert aggregation["snapshot_origin"] == 0


def test_datetime_events_require_and_use_discrete_snapshot_duration(tmp_path) -> None:
    path = _write_events(
        tmp_path,
        [
            {"source": "a", "target": "b", "time": "2026-01-01T00:00:00Z"},
            {"source": "a", "target": "b", "time": "2026-01-01T00:00:39Z"},
            {"source": "a", "target": "c", "time": "2026-01-01T00:00:40Z"},
        ],
    )
    temporal = nb.from_temporal_edgelist(path)

    with pytest.raises(nb.ConfigurationError, match="requires an explicit"):
        nb.aggregate_temporal(temporal, weighting="baseline")

    network = nb.aggregate_temporal(
        temporal,
        weighting="asf",
        evaluation_time="2026-01-01T00:01:20Z",
        snapshot_size="40s",
        snapshot_origin="2026-01-01T00:00:00Z",
        p=1.0,
        q=0.0,
        a=0.0,
    )
    graph = network.to_original_graph()

    assert graph.edges["a", "b"]["weight"] == pytest.approx(2.0 / (1.0 + math.exp(2.0)))
    assert graph.edges["a", "c"]["weight"] == pytest.approx(1.0 / (1.0 + math.exp(1.0)))
    assert graph.edges["a", "b"]["temporal_first_time"] == ("2026-01-01T00:00:00+00:00")


def test_future_events_are_ignored_before_snapshot_weighting(tmp_path) -> None:
    path = _write_events(
        tmp_path,
        [
            {"source": "a", "target": "b", "time": 0},
            {"source": "a", "target": "c", "time": 6},
        ],
    )
    temporal = nb.from_temporal_edgelist(path)

    with pytest.warns(UserWarning, match="Ignored 1 temporal event"):
        network = nb.aggregate_temporal(
            temporal,
            weighting="baseline",
            evaluation_time=5,
            snapshot_size=10,
            snapshot_origin=0,
        )

    graph = network.to_original_graph()
    assert sorted(graph.edges()) == [("a", "b")]
    assert set(graph.nodes()) == {"a", "b", "c"}
    aggregation = network.metadata["temporal_aggregation"]
    assert isinstance(aggregation, dict)
    assert aggregation["future_event_count"] == 1
    result = (
        nb.pipeline()
        .score("edge_weight")
        .filter("threshold", value=0.0, operator="greater_equal")
        .run(network)
    )
    assert result.warnings == (
        "Ignored 1 temporal event(s) after the evaluation time.",
    )


def test_zero_weight_policy_drops_or_keeps_zero_aggregate_edges(tmp_path) -> None:
    path = _write_events(
        tmp_path,
        [{"source": "a", "target": "b", "time": 0, "magnitude": 0}],
    )
    temporal = nb.from_temporal_edgelist(path, event_weight="magnitude")

    with pytest.warns(UserWarning, match="Dropped 1 temporal edge"):
        dropped = nb.aggregate_temporal(
            temporal,
            weighting="baseline",
        )
    kept = nb.aggregate_temporal(
        temporal,
        weighting="baseline",
        zero_weight_policy="keep",
    )

    assert dropped.edge_count == 0
    assert dropped.node_count == 2
    assert kept.to_original_graph().edges["a", "b"]["weight"] == 0.0
    dropped_metadata = dropped.metadata["temporal_aggregation"]
    assert isinstance(dropped_metadata, dict)
    assert dropped_metadata["zero_weight_edge_count"] == 1


def test_temporal_config_round_trips_and_runs_as_saved(tmp_path) -> None:
    config = nb.TemporalAggregationConfig(
        weighting="persistent_weibull",
        parameters={"persistent_level": 0.2, "scale": 4, "shape": 2},
        evaluation_time=10.5,
        time_unit=2,
        zero_weight_policy="keep",
    )
    payload = json.loads(json.dumps(config.to_dict()))
    restored = nb.TemporalAggregationConfig.from_dict(payload)
    path = tmp_path / "temporal.json"
    config.to_json(path)

    assert restored.to_dict() == config.to_dict()
    assert nb.TemporalAggregationConfig.from_json(path).to_dict() == config.to_dict()

    events_path = _write_events(
        tmp_path,
        [{"source": "a", "target": "b", "time": 8.5}],
    )
    temporal = nb.from_temporal_edgelist(events_path)
    network = nb.aggregate_temporal(temporal, config=restored)
    assert network.edge_count == 1

    with pytest.raises(nb.ConfigurationError, match="cannot combine"):
        nb.aggregate_temporal(temporal, config=restored, weighting="baseline")


def test_temporal_registry_and_parameter_validation_are_explicit() -> None:
    assert nb.list_temporal_weightings() == (
        "asf",
        "baseline",
        "persistent_exponential",
        "persistent_log_logistic",
        "persistent_weibull",
    )
    assert nb.describe_temporal_weighting("baseline")["formula"] == "phi(x) = 1"
    assert nb.describe_temporal_weighting("asf")["default_parameters"] == {
        "p": 3.0,
        "q": 0.0,
        "a": 5.0,
    }
    assert nb.describe_temporal_weighting("persistent_weibull")[
        "required_parameters"
    ] == ("persistent_level", "scale", "shape")

    with pytest.raises(nb.ConfigurationError, match="Unknown temporal weighting"):
        nb.TemporalAggregationConfig(weighting="unknown")
    with pytest.raises(nb.ValidationError, match="parameter 'p' must be positive"):
        nb.TemporalAggregationConfig(weighting="asf", parameters={"p": 0})
    with pytest.raises(nb.ValidationError, match="parameter 'q'.*non-negative"):
        nb.TemporalAggregationConfig(weighting="asf", parameters={"q": -1})
    with pytest.raises(nb.ConfigurationError, match="does not accept parameter"):
        nb.TemporalAggregationConfig(
            weighting="baseline",
            parameters={"unknown": 1},
        )
    with pytest.raises(nb.ConfigurationError, match="requires parameter"):
        nb.TemporalAggregationConfig(
            weighting="persistent_exponential",
            parameters={"persistent_level": 0.2},
        )
    with pytest.raises(nb.ValidationError, match="between 0 and 1"):
        nb.TemporalAggregationConfig(
            weighting="persistent_exponential",
            parameters={"persistent_level": 1.1, "decay_rate": 1},
        )
    with pytest.raises(nb.ValidationError, match="scale.*positive"):
        nb.TemporalAggregationConfig(
            weighting="persistent_weibull",
            parameters={"persistent_level": 0.2, "scale": 0, "shape": 1},
        )
    with pytest.raises(nb.ValidationError, match="shape.*positive"):
        nb.TemporalAggregationConfig(
            weighting="persistent_log_logistic",
            parameters={"persistent_level": 0.2, "scale": 1, "shape": 0},
        )
    for removed in ("exponential", "power_law", "sliding_window"):
        with pytest.raises(nb.ConfigurationError, match="Unknown temporal weighting"):
            nb.TemporalAggregationConfig(weighting=removed)
    with pytest.raises(nb.ConfigurationError, match="exact elapsed time"):
        nb.TemporalAggregationConfig(
            weighting="persistent_exponential",
            parameters={"persistent_level": 0.2, "decay_rate": 1},
            snapshot_size=1,
        )
    with pytest.raises(nb.ConfigurationError, match="does not accept time_unit"):
        nb.TemporalAggregationConfig(weighting="asf", time_unit=1)
    with pytest.raises(nb.ValidationError, match="snapshot_size must be positive"):
        nb.TemporalAggregationConfig(snapshot_size=0)
    with pytest.raises(nb.ValidationError, match="evaluation_time must be finite"):
        nb.TemporalAggregationConfig(evaluation_time=math.inf)


def test_temporal_input_and_snapshot_validation_errors_are_actionable(tmp_path) -> None:
    missing_path = _write_events(
        tmp_path,
        [{"source": "a", "target": "b"}],
    )
    with pytest.raises(nb.ValidationError, match="missing required column"):
        nb.from_temporal_edgelist(missing_path)

    invalid_path = _write_events(
        tmp_path,
        [{"source": "a", "target": "b", "time": "not-a-time"}],
    )
    with pytest.raises(nb.ValidationError, match="invalid numeric or datetime"):
        nb.from_temporal_edgelist(invalid_path)

    weighted_path = _write_events(
        tmp_path,
        [{"source": "a", "target": "b", "time": 0, "magnitude": -1}],
    )
    with pytest.raises(nb.ValidationError, match="finite and non-negative"):
        nb.from_temporal_edgelist(weighted_path, event_weight="magnitude")

    fractional_path = _write_events(
        tmp_path,
        [{"source": "a", "target": "b", "time": 0.5}],
    )
    temporal = nb.from_temporal_edgelist(fractional_path)
    with pytest.raises(nb.ValidationError, match="integer snapshot id"):
        nb.aggregate_temporal(temporal)

    self_only_path = _write_events(
        tmp_path,
        [{"source": "a", "target": "a", "time": 0}],
    )
    with pytest.raises(nb.ValidationError, match="no non-self interaction"):
        nb.from_temporal_edgelist(self_only_path)

    boolean_time_path = _write_events(
        tmp_path,
        [{"source": "a", "target": "b", "time": True}],
    )
    with pytest.raises(nb.ValidationError, match="boolean time value"):
        nb.from_temporal_edgelist(boolean_time_path)

    boolean_weight_path = _write_events(
        tmp_path,
        [
            {
                "source": "a",
                "target": "b",
                "time": 0,
                "magnitude": True,
            }
        ],
    )
    with pytest.raises(nb.ValidationError, match="boolean event weight"):
        nb.from_temporal_edgelist(boolean_weight_path, event_weight="magnitude")


def test_aggregated_temporal_network_uses_existing_backbone_pipeline(tmp_path) -> None:
    path = _write_events(
        tmp_path,
        [
            {"source": "a", "target": "b", "time": 0},
            {"source": "a", "target": "b", "time": 1},
            {"source": "b", "target": "c", "time": 1},
        ],
    )
    temporal = nb.from_temporal_edgelist(path)
    network = temporal.aggregate(weighting="baseline")

    result = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("threshold", value=2.0, operator="greater_equal")
        .run(network)
    )

    assert sorted(result.graph.edges()) == [("a", "b")]
    assert network.metadata["temporal_aggregation"]["weighting"] == "baseline"
    assert result.network_metadata["temporal_aggregation"]["weighting"] == ("baseline")


def test_temporal_experiment_bundle_preserves_resolved_aggregation_config(
    tmp_path,
) -> None:
    path = _write_events(
        tmp_path,
        [
            {"source": "a", "target": "b", "time": 0},
            {"source": "a", "target": "b", "time": 1},
            {"source": "b", "target": "c", "time": 2},
        ],
    )
    temporal = nb.from_temporal_edgelist(path)
    network = nb.aggregate_temporal(
        temporal,
        weighting="persistent_exponential",
        persistent_level=0.2,
        decay_rate=1.0,
    )
    result = (
        nb.pipeline()
        .score("edge_weight")
        .filter("fraction", fraction=0.5, tie_policy="exact_stable")
        .run(network)
    )

    bundle = nb.save_experiment(result, tmp_path / "experiment")
    restored = nb.TemporalAggregationConfig.from_json(
        bundle / "temporal_aggregation.json"
    )
    metadata = json.loads(
        (bundle / "network_metadata.json").read_text(encoding="utf-8")
    )

    assert restored.weighting == "persistent_exponential"
    assert restored.parameters == {"persistent_level": 0.2, "decay_rate": 1.0}
    assert restored.evaluation_time == 2
    assert metadata["temporal_aggregation"]["included_event_count"] == 3
    assert metadata["temporal_source_path"] == str(path)
