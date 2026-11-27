# Node Strength

Registered name `node_strength`

Ranks nodes by the sum of the weights on their incident links. An isolated node
has strength zero. Use the `weight` parameter to choose the numeric attribute,
which defaults to `"auto"` and reads the `weight` attribute. Weights are
required. This measure can rank a node with a few strong
links ahead of a node with many weak links.

On a directed graph, `direction` chooses which arcs count. The default
`"total"` adds incoming and outgoing weights, `"in"` gives in-strength, and
`"out"` gives out-strength. An undirected graph has one strength per node, so
`"in"` and `"out"` give the total and add a warning.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| node | `node_strength` | higher | Supported | Finite numeric |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("node_strength", weight="weight")
# On a directed graph: nb.pipeline().score("node_strength", direction="in")
result = candidate.filter("fraction", fraction=0.5, tie_policy="exact_stable").run(
    graph
)
print(result.summary())
```
