# Quickstart

This page shows the smallest complete Netbone workflow:

```text
load graph -> score -> filter -> inspect result
```

## Create A Graph

```python
import networkx as nx
import netbone as nb

graph = nx.Graph()
graph.add_edge("alice", "bob", weight=4.0)
graph.add_edge("bob", "carol", weight=2.0)
graph.add_edge("carol", "dana", weight=1.0)
```

## Build A Pipeline

Pipelines separate scoring from filtering. A method computes statistics, and a
filter converts those statistics into a selected backbone.

```python
pipeline = (
    nb.pipeline()
    .score("edge_weight", weight="weight")
    .filter("threshold", value=2.0, operator="greater_equal")
)
```

## Inspect Scores

```python
scores = pipeline.compute(graph)
print(scores.statistics[["source", "target", "score"]])
```

## Extract The Backbone

```python
result = pipeline.run(graph)

print(sorted(result.graph.edges()))
print(result.summary())
```

The returned graph uses the original node ids. The result keeps the original
graph, method statistics, selection metadata, pipeline configuration, warnings,
and a summary of retained nodes and edges.

## Use A P-Value Method

For statistical methods such as `disparity`, use the `significance` filter:

```python
result = (
    nb.pipeline()
    .score("disparity", weight="weight")
    .filter("significance", alpha=0.05)
    .run(graph)
)
```

When `statistic` is omitted, the filter uses the method's primary statistic.
For `disparity`, that is `disparity_pvalue`.

## Discover Available Components

```python
nb.list_methods()
nb.describe_method("disparity")

nb.list_filters()
nb.describe_filter("fraction")

nb.list_metrics()
nb.describe_metric("edge_retention")
```

## Next Steps

- [Choosing methods](../user-guide/choosing-methods.md)
- [Filtering](../user-guide/filtering.md)
- [Method comparison](../workflows/method_comparison.md)
- [Parameter sweeps](../workflows/parameter_sweeps.md)
- [Experiment bundles](../workflows/experiment_bundles.md)
