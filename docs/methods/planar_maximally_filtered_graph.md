# Planar Maximally Filtered Graph

Registered name `planar_maximally_filtered_graph`

Tries input links in descending weight order and accepts each link if the
retained graph stays planar. Use PMFG when the output needs cycles and must
also admit a drawing without crossings. The algorithm tests available links
only.

`weight="weight"` is the default. Pass `weight=None` to make weights equal.
Ties use internal `edge_id`. The result warns when equal weights appear on both
sides of the final selection.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `pmfg_selected` | higher | Unsupported | Finite numeric or unit weights |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("planar_maximally_filtered_graph", weight="weight")
result = candidate.filter("default").run(graph)
print(result.summary())
```

[Algorithm reference](https://doi.org/10.1073/pnas.0500298102)
