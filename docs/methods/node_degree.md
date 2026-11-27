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
