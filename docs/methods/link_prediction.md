# Link Prediction

Registered name `link_prediction`

Scores each observed link after temporarily removing it from the working graph.
Choose `similarity="preferential_attachment"` for the endpoint degree or
strength product, `"shortest_path"` for inverse replacement-path distance, or
`"local_path"` for support from paths of length two and three. `epsilon=1.0`
sets the contribution of length-three paths in Local Path. Directed support
uses the source's outgoing and target's incoming topology. Path-based
similarities follow the arc direction.

Weights are optional. The default `weight="auto"` uses the `weight` attribute
when every edge has one and ignores weights otherwise; pass `weight=None` to
ignore them. Weighted scoring requires positive weights.
`weight_alpha=1.0` is the weight exponent. `distance_transform="inverse"`
treats weights as strengths and `"identity"` as distances. For fraction or
default filtering, explicitly choose `direction="higher"` for well-supported
links or `"lower"` for links with weaker structural support.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `link_prediction_similarity` | higher | Supported | Positive when weighted |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("link_prediction", similarity="local_path")
result = candidate.filter("fraction", fraction=0.5, direction="lower").run(graph)
print(result.summary())
```

## References

- Yassin, A., Cherifi, H., Seba, H., & Togni, O. (2025). High and low similarity backbone extraction using similarity-based link prediction. Applied Network Science, 10(1). [doi:10.1007/s41109-025-00705-y](https://doi.org/10.1007/s41109-025-00705-y)
