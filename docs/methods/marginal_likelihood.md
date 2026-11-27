# Marginal Likelihood

Registered name `marginal_likelihood`

Uses an inclusive binomial upper tail for the observed edge count. If `W` is
total edge count and the two endpoint strengths are `s` and `t`, the method
uses `W` trials and probability `s * t / (2 * W ** 2)`. Weights are required;
the default `weight="auto"` reads the `weight` attribute, or name a count
attribute. Floating-point representations of whole
counts are accepted. Use a continuous-weight method when the observed values
are rates or averaged measurements.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `marginal_likelihood_pvalue` | lower | Unsupported | Positive integer counts |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("marginal_likelihood", weight="weight")
result = candidate.filter("significance", alpha=0.05, correction="holm").run(graph)
print(result.summary())
```

[Algorithm reference](https://doi.org/10.1103/PhysRevE.93.012304)
