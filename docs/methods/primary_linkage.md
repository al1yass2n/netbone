# Primary Linkage

Registered name `primary_linkage`

Each node nominates its strongest incident link. An edge is marked if at least
one endpoint nominates it. Choose this when each node's leading connection is
the relevant signal. Weights are required. The default `weight="auto"` reads the
`weight` attribute, or name another finite numeric attribute. Equal weights are ordered by internal `edge_id`. The score
table also reports the number of nominations per edge.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `primary_linkage_selected` | higher | Unsupported | Finite numeric |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("primary_linkage", weight="weight")
result = candidate.filter("default").run(graph)
print(result.summary())
```

## References

- Nystuen, J. D., & Dacey, M. F. (1961). A graph theory interpretation of nodal regions. Papers of the Regional Science Association, 7(1), 29–42. [doi:10.1111/j.1435-5597.1961.tb01769.x](https://doi.org/10.1111/j.1435-5597.1961.tb01769.x)
