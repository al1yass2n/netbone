# Choose what to keep

Start with the reason for reducing the graph. If absolute connection strength
matters, rank raw weights. If each node operates at a different scale,
consider an endpoint-based method such as [Disparity](../methods/disparity.md)
or [LANS](../methods/lans.md). For minimum connectivity within input
components, start with a [maximum spanning forest](../methods/maximum_spanning_forest.md).
The [method catalog](../reference/methods.md) compares the input requirements
and selection defaults.

## Match the filter to the statistic

| Analysis goal | Filter | What to specify |
| --- | --- | --- |
| Apply a numerical rule | [Threshold](../filters/threshold.md) | A cutoff and an explicit comparison operator |
| Compare methods at a similar budget | [Fraction](../filters/fraction.md) | A retained fraction and, when it matters, a ranking direction and tie policy |
| Use an output classified as a p-value | [Significance](../filters/significance.md) | An alpha level and a multiple-testing correction |
| Use a method's configured selection | [Default](../filters/default.md) | Any overrides required for that method |

A method reports `target`, `output_type`, `primary_statistic`, and
`preferred_direction`. Small p-values are preferred. For a similarity score,
the useful end of the scale depends on whether you want well-supported
connections or structurally unusual ones. Use the primary statistic unless you
have a specific secondary column in mind.

An edge filter selects edge IDs. By default, the resulting graph keeps all
input nodes, including isolates. Pass `drop_isolates=True` to omit nodes with
no retained incident edge. A node filter selects node IDs and keeps every input
edge between selected nodes. A node retention budget can therefore produce
different edge retention rates on different graphs.

## Reuse an existing score table

Score once when a method is expensive and you only need to change the filter.
This example keeps the strongest two links and then keeps links above a cutoff
from the same scores.

```python
import networkx as nx
import netbone as nb

graph = nx.Graph()
graph.add_weighted_edges_from([("A", "B", 7), ("B", "C", 4), ("C", "D", 2)])
scores = nb.score(graph, "edge_weight", weight="weight")

top = nb.filter_scores(graph, scores, "fraction", fraction=0.5)
cutoff = nb.filter_scores(graph, scores, "threshold", value=5, operator="greater_equal")
assert top.graph.number_of_edges() == 2
assert cutoff.graph.number_of_edges() == 1
```

Pass the same input graph or normalized network to both calls. Statistics
contain internal IDs that identify rows in that input. Read `result.warnings`
alongside the selection, particularly when ties or an uncorrected significance
filter affect the interpretation.

## Apply a custom rule

A custom filter receives a `MethodResult`, the input graph with original
labels, and your keyword arguments. It must return a `Selection` for the same
target, with IDs from the score table. The mask follows the table's row order.
This filter computes its cutoff from the scores and delegates selection to a
built-in helper. It uses `graph` from the previous example.

```python
from netbone.filters import apply_threshold


def above_median(method_result, original_graph):
    column = method_result.primary_statistic
    return apply_threshold(
        method_result,
        value=method_result.statistics[column].median(),
        operator="greater",
    )


result = (
    nb.pipeline().score("edge_weight", weight="weight").filter(above_median).run(graph)
)
assert result.graph.number_of_edges() == 1
```

Keep the callable in your Python source when sharing the workflow. The
[pipeline JSON format](reproduce.md) supports registered method and filter names.
