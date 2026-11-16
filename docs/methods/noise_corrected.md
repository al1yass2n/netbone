# Noise Corrected

Registered name `noise_corrected`

Uses the Bayesian reference calculation to estimate lift and uncertainty for an
observed interaction count. Directed input preserves separate outgoing and
incoming margins. The score table contains `noise_corrected_score` (lift),
`noise_corrected_stddev`, and `noise_corrected_z` (lift divided by its standard
deviation). A degenerate margin can leave the uncertainty undefined. Inspect
the warnings and the corresponding rows.

Use `weight="weight"` (default) or name the count attribute. The default
threshold is a strict inequality at 1.64 standard deviations. This statistic is
a score, so use the default, threshold, or fraction filter.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `noise_corrected_z` | higher | Supported | Positive integer counts |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("noise_corrected", weight="weight")
result = candidate.filter("default").run(graph)
print(result.summary())
```

[Algorithm reference](https://doi.org/10.1109/ICDE.2017.100)
