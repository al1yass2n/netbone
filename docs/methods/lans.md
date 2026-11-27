# Locally Adaptive Network Sparsification

Registered name `lans`

Compares the fraction of an endpoint's strength carried by a link to the
empirical distribution of fractions at that endpoint. This empirical tail
differs from the uniform model used by [Disparity](disparity.md). Both
endpoints are checked: in a directed graph an arc is compared with the
source's outgoing distribution and the target's incoming distribution.

Weights are required. The default `weight="auto"` reads the `weight`
attribute, or name your strength attribute. `pvalue_aggregation` combines the
two endpoint values; see [Combining the two ends](#combining-the-two-ends). The default `leaf_policy="zero"` assigns
p-value zero at degree one. Choose `"ignore"` to omit that endpoint. If no
endpoint value is available, the primary p-value is 1.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `lans_pvalue` | lower | Supported | Positive |

## Combining the two ends

Each edge gets one p-value per end: on a directed graph, `p_out` from the
source's outgoing distribution and `p_in` from the target's incoming
distribution. `pvalue_aggregation` turns them into the edge p-value that
the significance filter compares with `alpha`.

| `pvalue_aggregation` | Edge p-value | Keeps an edge that is |
| --- | --- | --- |
| `"min"` (default) | `min(p_out, p_in)` | important for at least one end |
| `"max"` | `max(p_out, p_in)` | important for both ends |
| `"average"` | mean of the two | balanced between the two ends |
| `"out"` (directed only) | `p_out` | important for the sender |
| `"in"` (directed only) | `p_in` | important for the receiver |

`"out"` and `"in"` raise a `ConfigurationError` on an undirected graph, where
an edge has no source or target end. With `leaf_policy="ignore"`, an ignored
end counts as missing, and an edge with no remaining value gets p-value 1.

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("lans", weight="weight", leaf_policy="ignore")
result = candidate.filter("default").run(graph)
print(result.summary())
```

[Algorithm reference](https://doi.org/10.1371/journal.pone.0016431)
