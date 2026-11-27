# Edge Weight

Registered name `edge_weight`

Keep links with the largest observed weights. The score is the value of the
chosen edge attribute. The default `weight="auto"` reads the `weight`
attribute when every edge has one. On an unweighted graph, or with
`weight=None`, every edge receives 1.0, so ranking reduces to tie handling.
Directed arcs keep their own weights.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `score` | higher | Supported | Finite numeric or unit weights |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("edge_weight", weight="weight")
result = candidate.filter("threshold", value=5, operator="greater_equal").run(graph)
print(result.summary())
```

## References

Edge Weight is a baseline that ranks edges by their own weight, so it has no single source paper.
