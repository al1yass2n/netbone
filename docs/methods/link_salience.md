# Link Salience

Registered name `link_salience`

Counts the fraction of roots whose shortest-path graph contains the edge. For a
directed arc the method follows outgoing paths and divides by all roots,
including those that cannot reach the arc. Equal shortest paths can include
multiple predecessors.

The default `weight="auto"` uses the `weight` attribute when every edge has
one and hop counts otherwise. Pass `weight=None` to force hop counts.
`distance_transform="inverse"` treats weights as strengths and `"identity"`
treats them as distances.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `link_salience` | higher | Supported | Positive or unit weights |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("link_salience", weight="weight")
result = candidate.filter("default").run(graph)
print(result.summary())
```

[Algorithm reference](https://doi.org/10.1038/ncomms1847)
