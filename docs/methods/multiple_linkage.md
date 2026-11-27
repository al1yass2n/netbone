# Multiple Linkage

Registered name `multiple_linkage`

Fits a local set of strongest links for each node. It orders positive incident
weights, compares their weight shares to equal-share top-k patterns, and uses
the prefix with the best fit. An edge is marked if either endpoint selects it.

Weights are required; the default `weight="auto"` reads the non-negative
`weight` attribute, or name another one. Zero-weight rows
remain in the statistics and are excluded from the local fit. Equal weights use
internal `edge_id` ordering.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `multiple_linkage_selected` | higher | Unsupported | Non-negative |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("multiple_linkage", weight="weight")
result = candidate.filter("default").run(graph)
print(result.summary())
```

[Algorithm reference](https://doi.org/10.1111/j.1467-9663.2009.00547.x)
