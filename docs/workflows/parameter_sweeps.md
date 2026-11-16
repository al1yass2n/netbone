# Parameter Sweep Workflow

Use parameter sweeps to compare pipeline configurations.

## Filter Sweeps

Use filter sweeps when the scoring method stays fixed and only filter
parameters change. Method scores are cached by graph identity, method name, and
method parameters, so changing only thresholds, fractions, or alpha values
reuses the computed statistics.

```python
sweep_result = (
    nb.sweep(graph)
    .score("disparity", weight="weight")
    .vary_filter(
        "significance",
        alpha=[0.01, 0.05, 0.10],
    )
    .measure(["edge_retention", "weight_retention"])
    .run()
)

metrics = sweep_result.table()
runs = sweep_result.runs
```

For threshold sweeps with fixed non-varying filter parameters, configure the
base filter first:

```python
sweep_result = (
    nb.sweep(graph)
    .score("edge_weight", weight="weight")
    .filter("threshold", operator="greater_equal")
    .vary_filter(value=[1.0, 2.0, 4.0])
    .measure(["edge_count", "edge_retention"])
    .run()
)
```

Retained-fraction sweeps use the existing deterministic tie policies:

```python
sweep_result = (
    nb.sweep(graph)
    .score("edge_weight", weight="weight")
    .filter("fraction", tie_policy="include_all_ties")
    .vary_filter(fraction=[0.10, 0.25, 0.50])
    .run()
)
```

## Method-Parameter Sweeps

Changing method parameters creates separate score computations:

```python
sweep_result = (
    nb.sweep(graph)
    .score("disparity", weight="weight")
    .filter("significance", alpha=0.05)
    .vary_method(pvalue_aggregation=["min", "max", "average"])
    .measure(["edge_count", "edge_retention"])
    .run()
)
```

## Method-Filter Grids

Use `grid(...)` when both method configurations and filter configurations
should vary. The sweep runs the Cartesian product of method parameter
combinations and filter parameter combinations. Incompatible pairs become
failed rows instead of stopping the whole sweep.

```python
sweep_result = (
    nb.sweep(graph)
    .grid(
        methods={
            "edge_weight": {"weight": "weight"},
            "disparity": {
                "weight": "weight",
                "pvalue_aggregation": ["min", "max"],
            },
        },
        filters={
            "fraction": {"fraction": [0.05, 0.10, 0.20]},
            "significance": {"alpha": [0.01, 0.05]},
        },
    )
    .measure(["edge_retention", "connected_component_count"])
    .run()
)
```

Use one filter entry when you want the same filter across methods:

```python
sweep_result = (
    nb.sweep(graph)
    .grid(
        methods={
            "edge_weight": {"weight": "weight"},
            "disparity": {
                "weight": "weight",
                "pvalue_aggregation": ["min", "max"],
            },
            "link_salience": {"weight": "weight"},
        },
        filters={"fraction": {"fraction": 0.10}},
    )
    .measure(["edge_retention", "connected_component_count"])
    .run()
)
```

This produces:

- every `edge_weight` configuration crossed with every filter configuration;
- every `disparity` configuration crossed with every filter configuration;
- score reuse across filter configurations for the same method parameters;
- failed rows for incompatible pairs such as a score method with the
  `significance` filter.

## Output Tables

`sweep_result.table()` returns tidy metric rows with:

- `run_id`
- `pipeline_name`
- `method`
- `method_parameters`
- `filter`
- `filter_parameters`
- `varied_parameter`
- `parameter_value`
- `varied_parameters`
- `metric`
- `value`
- `status`
- `explanation`
- `warning`
- `failure_detail`
- `score_cache_key`
- `score_cache_hit`

`sweep_result.runs` returns one row per configuration, and
`sweep_result.failures` returns only failed configurations. Failed
configurations are recorded as `status="failed"` rows while successful
configurations remain available in `sweep_result.results`.

If a configuration extracts successfully but a requested metric is invalid,
the configuration remains available and the metric row records
`status="invalid"` with an explanation.

`SweepResult.to_dict()` converts invalid numeric values such as pandas `NaN`
to JSON `null`, so the summary payload can be serialized directly.

`sweep_result.plot_data` returns plot-ready pandas tables without adding a
plotting dependency to the core package.
