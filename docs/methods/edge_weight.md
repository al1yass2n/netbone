# Edge Weight

Registered name `edge_weight`

Keep links with the largest observed weights. The score is the value of the
chosen edge attribute. With `weight=None` (the default), every edge receives
1.0, so ranking an unweighted graph reduces to tie handling.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `score` | higher | Unsupported | Finite numeric or unit weights |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("edge_weight", weight="weight")
result = candidate.filter("threshold", value=5, operator="greater_equal").run(graph)
print(result.summary())
```
