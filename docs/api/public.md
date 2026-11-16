# Public API

This page documents the intentionally public `netbone` package surface.

Use discovery helpers first when working interactively:

```python
import netbone as nb

nb.list_methods()
nb.list_filters()
nb.list_metrics()
```

::: netbone
    options:
      members:
        - from_graph
        - from_edgelist
        - from_graphml
        - from_temporal_edgelist
        - aggregate_temporal
        - pipeline
        - score
        - filter_scores
        - compare
        - sweep
        - report
        - save_experiment
        - list_methods
        - describe_method
        - list_filters
        - describe_filter
        - list_metrics
        - describe_metric
        - list_temporal_weightings
        - describe_temporal_weighting
        - Network
        - Pipeline
        - MethodResult
        - Selection
        - BackboneResult
        - Comparison
        - Sweep
        - SweepResult
        - Report
        - TemporalNetwork
        - TemporalAggregationConfig
        - NetboneError
        - ConfigurationError
        - CompatibilityError
        - ValidationError
        - UndefinedMetricError
