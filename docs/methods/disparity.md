# Disparity

Registered name `disparity`

Tests whether an edge accounts for an unusually large share of an endpoint's
strength under a uniform allocation model. For degree `k > 1` and weight share
`p`, the endpoint p-value is `(1 - p) ** (k - 1)`. Directed arcs use the
source's outgoing and target's incoming weight distributions.

Weights are required; the default `weight="auto"` reads the `weight`
attribute, or name another strength attribute. Combine the endpoint p-values
with `pvalue_aggregation="min"` (default), `"max"`, or `"average"`.
`leaf_policy="ignore"` omits a degree-one endpoint and `"zero"` assigns it
p-value zero. When both endpoints are ignored, the primary p-value is 1. The
table exposes the endpoint fractions and p-values for diagnosis.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `disparity_pvalue` | lower | Supported | Positive |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("disparity", weight="weight", leaf_policy="ignore")
result = candidate.filter("significance", alpha=0.05, correction="holm").run(graph)
print(result.summary())
```

[Algorithm reference](https://doi.org/10.1073/pnas.0808904106)
