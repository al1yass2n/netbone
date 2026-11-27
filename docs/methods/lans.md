# Locally Adaptive Network Sparsification

Registered name `lans`

Compares the fraction of an endpoint's strength carried by a link to the
empirical distribution of fractions at that endpoint. This empirical tail
differs from the uniform model used by [Disparity](disparity.md). Directed arcs
are evaluated against the source's outgoing distribution alone.

Weights are required. The default `weight="auto"` reads the `weight`
attribute, or name your strength attribute. In an
undirected graph, `pvalue_aggregation` combines endpoint values using `"min"`
(default), `"max"`, or `"average"`. The default `leaf_policy="zero"` assigns
p-value zero at degree one. Choose `"ignore"` to omit that endpoint. If no
endpoint value is available, the primary p-value is 1.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `lans_pvalue` | lower | Supported | Positive |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("lans", weight="weight", leaf_policy="ignore")
result = candidate.filter("default").run(graph)
print(result.summary())
```

[Algorithm reference](https://doi.org/10.1371/journal.pone.0016431)
