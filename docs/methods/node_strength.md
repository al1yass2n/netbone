# Node Strength

Registered name `node_strength`

Ranks nodes by the sum of the weights on their incident links. An isolated node
has strength zero. Use the `weight` parameter to choose the numeric attribute,
which defaults to `"auto"` and reads the `weight` attribute. Weights are
required. This measure can rank a node with a few strong
links ahead of a node with many weak links.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| node | `node_strength` | higher | Unsupported | Finite numeric |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("node_strength", weight="weight")
result = candidate.filter("fraction", fraction=0.5, tie_policy="exact_stable").run(
    graph
)
print(result.summary())
```
