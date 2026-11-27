# Disparity

Registered name `disparity`

Tests whether an edge accounts for an unusually large share of an endpoint's
strength under a uniform allocation model. For degree `k > 1` and weight share
`p`, the endpoint p-value is `(1 - p) ** (k - 1)`. Directed arcs use the
source's outgoing and target's incoming weight distributions.

Weights are required; the default `weight="auto"` reads the `weight`
attribute, or name another strength attribute. Combine the endpoint p-values with `pvalue_aggregation`; see
[Combining the two ends](#combining-the-two-ends).
The default `leaf_policy="zero"` assigns a degree-one endpoint p-value zero;
choose `"ignore"` to omit that endpoint. When both endpoints are ignored, the primary p-value is 1. The
table exposes the endpoint fractions and p-values for diagnosis.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `disparity_pvalue` | lower | Supported | Positive |

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
candidate = nb.pipeline().score("disparity", weight="weight", leaf_policy="ignore")
result = candidate.filter("significance", alpha=0.05, correction="holm").run(graph)
print(result.summary())
```

[Algorithm reference](https://doi.org/10.1073/pnas.0808904106)
