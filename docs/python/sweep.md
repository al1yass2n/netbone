# Find settings with a sweep

Sweep a set of candidate settings when you need to see how an outcome changes
over a range. Choose measurements that matter to the analysis. For example,
edge retention quantifies the reduction while component count reveals
fragmentation.

```python
import networkx as nx
import netbone as nb

graph = nx.Graph()
graph.add_weighted_edges_from(
    [("A", "B", 8), ("A", "C", 3), ("B", "C", 5), ("C", "D", 2)]
)

sweep_result = (
    nb.sweep(graph)
    .score("edge_weight", weight="weight")
    .filter("threshold", operator="greater_equal")
    .vary_filter(value=[2, 3, 5, 8])
    .measure(["edge_retention", "connected_component_count"])
    .run()
)
print(sweep_result.table().to_string(index=False))
assert len(sweep_result.runs) == 4
assert sweep_result.score_cache_misses == 1
```

All four runs reuse one score computation. The lowest cutoff keeps all four
links. The highest cutoff keeps only the link with weight eight.

## Vary a method or cross method and filter settings

Use `vary_method(...)` when changing a method parameter with fixed filter
settings. Use `grid(methods=..., filters=...)` for a Cartesian product
of the entries. Mapping keys are registered names. A scalar is one value
and a sequence expands into multiple candidates. To pass a list as a single
parameter value, wrap it in an outer list, for example
`{"similarities": [["local_path", "shortest_path"]]}`.

```python
grid = (
    nb.sweep(graph)
    .grid(
        methods={
            "edge_weight": {"weight": "weight"},
            "link_salience": {"weight": "weight"},
        },
        filters={
            "fraction": {"fraction": [0.25, 0.50], "tie_policy": "exact_stable"},
        },
    )
    .measure(["edge_retention"])
    .run()
)
assert len(grid.runs) == 4
```

Different method settings have separate score computations. If a generated
configuration fails, inspect `failures` for details. Successful runs remain
available in `results`. Use `runs` for the configuration-level records and
`table()` for the tidy measurement records. Inspect the status of a metric
before using its value.

With the optional plotting extra installed, use
`netbone.viz.plot_sweep_metric(sweep_result, "edge_retention")` for the
single-parameter example. For auditing settings or results, see
[reproducing an analysis](reproduce.md).
