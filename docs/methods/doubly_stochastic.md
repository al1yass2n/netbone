# Doubly Stochastic

Registered name `doubly_stochastic`

Balances the weighted adjacency matrix of each connected component toward unit
row and column sums. Its default extraction keeps a descending-score prefix
sufficient to connect each input component. Read `doubly_stochastic_score` for
the balanced values and `doubly_stochastic_connected_selected` for the
selection used by `default`.

Parameters default to `weight="auto"` (see [weights](../reference/methods.md#how-weights-are-chosen)), `epsilon=1e-4`,
`epsilon_mode="relative"`, `tolerance=1e-12`, and `max_iterations=1000`.
Epsilon fills the matrix and is added to observed weights. In relative mode it
is multiplied by mean edge weight within the component. In `"absolute"` mode it
is used directly. Check convergence warnings before interpreting scores,
especially on large components where the dense matrix is costly.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `doubly_stochastic_score` | higher | Unsupported | Positive |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("doubly_stochastic", weight="weight")
result = candidate.filter("default").run(graph)
print(result.summary())
```

## References

- Slater, P. B. (2009). A two-stage algorithm for extracting the multiscale backbone of complex weighted networks. Proceedings of the National Academy of Sciences, 106(26), E66. [doi:10.1073/pnas.0904725106](https://doi.org/10.1073/pnas.0904725106)
