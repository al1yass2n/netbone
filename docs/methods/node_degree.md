# Node Degree

Registered name `node_degree`

Ranks nodes by the number of incident links. The scorer takes no method
parameters. It accepts `weight=None` or `weight="auto"`, and naming a weight
attribute records a warning in `result.warnings`. Use
[Node Strength](node_strength.md) to sum weights instead. Apply a fraction or
threshold to keep nodes with the desired degree and use the resulting induced
graph to inspect their connections.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| node | `node_degree` | higher | Unsupported | Weights ignored |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("node_degree")
result = candidate.filter("fraction", fraction=0.5, tie_policy="exact_stable").run(
    graph
)
print(result.summary())
```

## References

- Freeman, L. C. (1978). Centrality in social networks: Conceptual clarification. Social Networks, 1(3), 215–239. [doi:10.1016/0378-8733(78)90021-7](https://doi.org/10.1016/0378-8733(78)90021-7)
