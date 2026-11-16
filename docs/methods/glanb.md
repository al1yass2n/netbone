# Globally and Locally Adaptive Network Backbone

Registered name `glanb`

Measures significance from shortest-path involvement and local edge shares. It
aggregates the more significant of the two endpoint values. Set the required
non-negative parameter `c` explicitly and record it when comparing results. At
an endpoint of degree `k > 1` and involvement `p`, the statistic is
`(1 - p) ** ((k - 1) ** c)`. Use `weight=None` (default) for hop counts or
provide positive strength weights, which are inverted for path distances.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `glanb_significance` | lower | Unsupported | Positive when weighted |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("glanb", c=1.0, weight="weight")
result = candidate.filter("default").run(graph)
print(result.summary())
```

[Algorithm reference](https://doi.org/10.1371/journal.pone.0100428)
