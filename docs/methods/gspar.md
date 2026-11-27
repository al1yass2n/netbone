# GSPAR

Registered name `gspar`

Ranks links by the Jaccard similarity of their endpoints' open neighborhoods,
the count of common neighbors divided by the count of distinct neighbors. A
higher value indicates more shared neighbors. The scorer takes no method
parameters. It accepts `weight=None` or `weight="auto"`, and naming a weight
attribute records a warning in `result.warnings`, because weights do not change
the score. Use a fraction filter to control how much the global ranking keeps
and report the realized fraction when scores tie.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `gspar_jaccard_similarity` | higher | Unsupported | Weights ignored |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("gspar")
result = candidate.filter("fraction", fraction=0.5, tie_policy="exact_stable").run(
    graph
)
print(result.summary())
```

## References

- Satuluri, V., Parthasarathy, S., & Ruan, Y. (2011). Local graph sparsification for scalable clustering. In Proceedings of the 2011 ACM SIGMOD International Conference on Management of Data, 721–732. ACM. [doi:10.1145/1989323.1989399](https://doi.org/10.1145/1989323.1989399)
