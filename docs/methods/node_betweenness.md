# Node Betweenness

Registered name `node_betweenness`

Ranks nodes by the share of shortest paths that pass through them.
The default `weight="auto"` uses the `weight` attribute when every edge has one
and hop counts otherwise; `weight=None` forces hop counts. For positive weights
use
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

## References

Freeman defined the measure. Netbone computes it with Brandes's algorithm through NetworkX.

- Freeman, L. C. (1977). A set of measures of centrality based on betweenness. Sociometry, 40(1), 35–41. [doi:10.2307/3033543](https://doi.org/10.2307/3033543)
- Brandes, U. (2001). A faster algorithm for betweenness centrality. Journal of Mathematical Sociology, 25(2), 163–177. [doi:10.1080/0022250X.2001.9990249](https://doi.org/10.1080/0022250X.2001.9990249)
