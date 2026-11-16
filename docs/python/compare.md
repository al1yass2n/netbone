# Compare backbone results

Run each candidate on the same input graph. If the question is which edges
different methods prefer, start with a similar edge budget and check the
achieved retention. For node-target methods, report node retention and edge
retention separately.

The example applies two cutoffs to the same collaboration network. One
retains one edge and the other retains two.

```python
import networkx as nx
import netbone as nb

graph = nx.Graph()
graph.add_weighted_edges_from([("A", "B", 8), ("B", "C", 5), ("C", "D", 2)])
scores = nb.score(graph, "edge_weight", weight="weight")
results = {
    label: nb.filter_scores(
        graph, scores, "threshold", value=value, operator="greater_equal"
    )
    for label, value in {"strict": 8, "relaxed": 5}.items()
}
comparison = nb.compare(results)

print(comparison.table(metrics=["edge_retention", "connected_component_count"]))
print(comparison.pairwise(metrics=["edge_jaccard"]))
print(comparison.spearman())
```

The edge Jaccard value is `0.5` because one edge is shared out of two in the
union. The score ranks agree because the two runs used the same scores. This
illustrates how selections can differ even when the underlying ranks agree.

## Read the comparison tables

- `table()` measures each result. Use `list_metrics(scope="single")` to
  discover counts, node and edge retention, weight retention, and connectivity
  metrics. For directed results, use weak or strong component counts as
  appropriate.
- `pairwise()` measures overlap between results. Jaccard divides the
  intersection by the union. The overlap coefficient divides by the size
  of the smaller set. Overlap metrics require matching original topology.
- `score_alignment(name_a, name_b)` provides aligned statistics and importance
  ranks. `spearman()` measures rank agreement across result pairs. Both require
  the same attributed original graph and matching score targets. Constant
  ranks can make correlation undefined.

In metric tables, inspect `status` and `explanation` before using `value`.
An `invalid` row records an incompatible metric or comparison, and an
`undefined` row records a metric that cannot be evaluated mathematically.
Treat these rows as missing measurements.

## Plot a measurement

Install the [viz extra](../start/install.md#optional-tools), then continue
from the earlier example. The helper returns a Matplotlib axes.

```python
from netbone import viz

ax = viz.plot_comparison_metric(comparison, "edge_retention")
ax.figure.savefig("edge-retention.png", dpi=160, bbox_inches="tight")
```

Use `plot_pairwise_metric(comparison, "edge_jaccard")` for the corresponding
pairwise chart. See the [comparison API](../reference/measurement.md) for
additional table and plotting entry points.
