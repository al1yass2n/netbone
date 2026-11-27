# Node Degree

Ranks nodes by their number of links. The backbone is the subgraph induced by
the kept nodes.
{: .lede }

<dl class="method-facts">
<div><dt>Registered name</dt><dd><code>node_degree</code></dd></div>
<div><dt>Scores</dt><dd>Nodes</dd></div>
<div><dt>Statistic</dt><dd><code>node_degree</code>, higher is stronger</dd></div>
<div><dt>Directed graphs</dt><dd>Not supported</dd></div>
<div><dt>Weights</dt><dd>Ignored</dd></div>
<div><dt>Suggested filter</dt><dd>10% fraction</dd></div>
</dl>

## How it works

The degree \(k_i\) of node \(i\) is its number of incident links. Use
[Node Strength](node_strength.md) to sum weights instead. Apply a fraction or
threshold to keep nodes with the desired degree, then inspect their
connections in the induced graph.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `weight` | `"auto"` | Accepted so one loop can pass the same weight to every method. Naming an attribute records a warning, because weights do not change the score. |

## Output columns

| Column | Meaning |
| --- | --- |
| `node_degree` | The degree. |

Every row also has `node_id` and the original `node` label.

## Cost

Linear in the number of edges.

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("node_degree")
result = candidate.filter("fraction", fraction=0.5, tie_policy="exact_stable").run(
    graph
)
print(result.summary())
```

## References

<div class="method-references" markdown="1">

- Freeman, L. C. (1978). Centrality in social networks: Conceptual clarification. Social Networks, 1(3), 215–239. [doi:10.1016/0378-8733(78)90021-7](https://doi.org/10.1016/0378-8733(78)90021-7)

<details class="bibtex" markdown="1">
<summary>BibTeX</summary>

```bibtex
@article{freeman1978centrality,
  author = {Freeman, L. C.},
  title = {Centrality in social networks: Conceptual clarification},
  journal = {Social Networks},
  year = {1978},
  volume = {1},
  number = {3},
  pages = {215--239},
  doi = {10.1016/0378-8733(78)90021-7}
}
```

</details>

</div>
