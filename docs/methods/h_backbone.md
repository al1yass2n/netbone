# H-Backbone

Registered name `h_backbone`

Finds two h-index cutoffs, one over raw weights and one over unnormalized edge
betweenness divided by the number of nodes. A link is marked if it meets at
least one positive cutoff. This combines raw strength with a shortest-path
measure of bridging.

Weights are required. The default `weight="auto"` reads the `weight` attribute.
Use `distance_transform="inverse"` (default) for
strengths or `"identity"` for path distances. Inspect `h_backbone_h_strength`
and `h_backbone_h_bridge` in the score table for the chosen cutoffs.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `h_backbone_selected` | higher | Unsupported | Positive |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("h_backbone", weight="weight")
result = candidate.filter("default").run(graph)
print(result.summary())
```

## References

- Zhang, R. J., Stanley, H. E., & Ye, F. Y. (2018). Extracting h-backbone as a core structure in weighted networks. Scientific Reports, 8, 14356. [doi:10.1038/s41598-018-32430-1](https://doi.org/10.1038/s41598-018-32430-1)
