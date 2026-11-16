# Primary Linkage

Registered name `primary_linkage`

Each node nominates its strongest incident link. An edge is marked if at least
one endpoint nominates it. Choose this when each node's leading connection is
the relevant signal. Use `weight="weight"` (default) or name another finite
numeric attribute. Equal weights are ordered by internal `edge_id`. The score
table also reports the number of nominations per edge.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `primary_linkage_selected` | higher | Unsupported | Finite numeric |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("primary_linkage", weight="weight")
result = candidate.filter("default").run(graph)
print(result.summary())
```

[Algorithm reference](https://doi.org/10.1111/j.1467-9663.2009.00547.x)
