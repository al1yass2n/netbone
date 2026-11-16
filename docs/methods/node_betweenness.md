# Node Betweenness

Registered name `node_betweenness`

Ranks nodes by the share of shortest paths that pass through them.
`weight=None` (default) uses hop counts. For positive weights use
`distance_transform="inverse"` (default) for strengths or `"identity"` for
distances. Defaults are `normalized=True` and `endpoints=False`. Set
`endpoints=True` to count path endpoints in the centrality. The extracted graph
includes links among the selected nodes, so paths through omitted nodes can
disappear.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| node | `node_betweenness` | higher | Unsupported | Positive when weighted |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("node_betweenness")
result = candidate.filter("fraction", fraction=0.5, tie_policy="exact_stable").run(
    graph
)
print(result.summary())
```

[Algorithm reference](https://doi.org/10.1080/0022250X.2001.9990249)
