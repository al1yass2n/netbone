# Maximum Spanning Forest

Registered name `maximum_spanning_forest`

Adds edges in descending weight order, skipping additions that would create a
cycle. The result spans each original connected component. Use this to retain
connectivity with a minimum number of links, at the cost of removing every
cycle.

The default `weight="auto"` uses the `weight` attribute when every edge has one
and equal weights otherwise. Pass `weight=None` to give each edge the same
weight. Equal weights are ordered by internal `edge_id`. The
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

## References

Kruskal's algorithm builds the forest. Mantegna used the spanning tree to filter correlation networks.

- Kruskal, J. B. (1956). On the shortest spanning subtree of a graph and the traveling salesman problem. Proceedings of the American Mathematical Society, 7(1), 48–50. [doi:10.1090/S0002-9939-1956-0078686-7](https://doi.org/10.1090/S0002-9939-1956-0078686-7)
- Mantegna, R. N. (1999). Hierarchical structure in financial markets. The European Physical Journal B, 11(1), 193–197. [doi:10.1007/s100510050929](https://doi.org/10.1007/s100510050929)
