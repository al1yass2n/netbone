# Maximum Spanning Forest

Registered name `maximum_spanning_forest`

Adds edges in descending weight order, skipping additions that would create a
cycle. The result spans each original connected component. Use this to retain
connectivity with a minimum number of links, at the cost of removing every
cycle.

The weight attribute defaults to `"weight"`. Pass `weight=None` to give each
edge the same weight. Equal weights are ordered by internal `edge_id`. The
primary statistic is a 1/0 membership flag. Use the default filter to extract
marked edges.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `maximum_spanning_forest_selected` | higher | Unsupported | Finite numeric or unit weights |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("maximum_spanning_forest", weight="weight")
result = candidate.filter("default").run(graph)
print(result.summary())
```
