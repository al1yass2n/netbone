# Edge Betweenness

Registered name `edge_betweenness`

Ranks edges by their share of shortest paths between node pairs. It can
highlight links that connect regions even when their raw weights are modest.
`weight=None` uses hop counts. For positive weights,
`distance_transform="inverse"` (default) converts strengths to distances and
`"identity"` uses the given distances. `normalized=True` is the default.
Computing all-pairs path centrality can be expensive on large graphs.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `edge_betweenness` | higher | Unsupported | Positive when weighted |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("edge_betweenness")
result = candidate.filter("default").run(graph)
print(result.summary())
```

[Algorithm reference](https://doi.org/10.1073/pnas.122653799)
