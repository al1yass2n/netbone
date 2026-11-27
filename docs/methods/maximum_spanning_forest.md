# Maximum Spanning Forest

Keeps the strongest links that connect every component without forming a
cycle. It keeps connectivity with the fewest links.
{: .lede }

<dl class="method-facts">
<div><dt>Registered name</dt><dd><code>maximum_spanning_forest</code></dd></div>
<div><dt>Scores</dt><dd>Edges</dd></div>
<div><dt>Statistic</dt><dd><code>maximum_spanning_forest_selected</code>, higher is stronger</dd></div>
<div><dt>Directed graphs</dt><dd>Not supported</dd></div>
<div><dt>Weights</dt><dd>Optional, finite numbers</dd></div>
<div><dt>Suggested filter</dt><dd>Selection flag = 1</dd></div>
</dl>

## How it works

Edges are added in descending weight order, and an edge that would close a
cycle is skipped (Kruskal's algorithm). The result spans each connected
component of the input. Equal weights are ordered by internal `edge_id`. The
primary statistic is a 1/0 flag, so use the default filter to extract the
marked edges.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `weight` | `"auto"` | Edge attribute to read. `"auto"` uses `weight` when every edge has it and runs unweighted otherwise; `None` always runs unweighted. See [how weights are chosen](../reference/methods.md#how-weights-are-chosen). Without weights every edge weighs the same. |

## Output columns

| Column | Meaning |
| --- | --- |
| `maximum_spanning_forest_weight` | The weight read from the graph. |
| `maximum_spanning_forest_order` | The order in which the edge was added, if it was. |
| `maximum_spanning_forest_selected` | 1 for a forest edge, 0 otherwise. |

Every row also has `edge_id`, `source`, and `target`, plus Netbone's internal
`source_id` and `target_id`.

## Cost

Sorting the edges: \(O(m \log m)\) for \(m\) edges.

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
pipeline = nb.pipeline().score("maximum_spanning_forest", weight="weight")
backbone = pipeline.filter("default").run(graph)
print(backbone.summary())
```

## References

Kruskal's algorithm builds the forest. Mantegna used the spanning tree to
filter correlation networks.

<div class="method-references" markdown="1">

- Kruskal, J. B. (1956). On the shortest spanning subtree of a graph and the traveling salesman problem. Proceedings of the American Mathematical Society, 7(1), 48–50. [doi:10.1090/S0002-9939-1956-0078686-7](https://doi.org/10.1090/S0002-9939-1956-0078686-7)
- Mantegna, R. N. (1999). Hierarchical structure in financial markets. The European Physical Journal B, 11(1), 193–197. [doi:10.1007/s100510050929](https://doi.org/10.1007/s100510050929)

<details class="bibtex" markdown="1">
<summary>BibTeX</summary>

```bibtex
@article{kruskal1956shortest,
  author = {Kruskal, J. B.},
  title = {On the shortest spanning subtree of a graph and the traveling salesman problem},
  journal = {Proceedings of the American Mathematical Society},
  year = {1956},
  volume = {7},
  number = {1},
  pages = {48--50},
  doi = {10.1090/S0002-9939-1956-0078686-7}
}

@article{mantegna1999hierarchical,
  author = {Mantegna, R. N.},
  title = {Hierarchical structure in financial markets},
  journal = {The European Physical Journal B},
  year = {1999},
  volume = {11},
  number = {1},
  pages = {193--197},
  doi = {10.1007/s100510050929}
}
```

</details>

</div>
