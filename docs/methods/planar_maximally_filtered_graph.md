# Planar Maximally Filtered Graph

Keeps the strongest links that still allow the network to be drawn without
crossings. Unlike a spanning forest, it keeps cycles.
{: .lede }

<dl class="method-facts">
<div><dt>Registered name</dt><dd><code>planar_maximally_filtered_graph</code></dd></div>
<div><dt>Scores</dt><dd>Edges</dd></div>
<div><dt>Statistic</dt><dd><code>pmfg_selected</code>, higher is stronger</dd></div>
<div><dt>Directed graphs</dt><dd>Not supported</dd></div>
<div><dt>Weights</dt><dd>Optional, finite numbers</dd></div>
<div><dt>Suggested filter</dt><dd>Selection flag = 1</dd></div>
</dl>

## How it works

Edges are tried in descending weight order, and each one is kept if the
retained graph stays planar. The search stops at \(3(n - 2)\) edges, the most a
planar graph on \(n\) nodes can have. Only edges present in the input are
tried. Ties use internal `edge_id`, and the result warns when equal weights
fall on both sides of the final selection.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `weight` | `"auto"` | Edge attribute to read. `"auto"` uses `weight` when every edge has it and runs unweighted otherwise; `None` always runs unweighted. See [how weights are chosen](../reference/methods.md#how-weights-are-chosen). Without weights every edge weighs the same. |

## Output columns

| Column | Meaning |
| --- | --- |
| `pmfg_weight` | The weight read from the graph. |
| `pmfg_order` | The order in which the edge was accepted, if it was. |
| `pmfg_selected` | 1 for a kept edge, 0 otherwise. |

Every row also has `edge_id`, `source`, and `target`, plus Netbone's internal
`source_id` and `target_id`.

## Cost

One planarity test per candidate edge: about \(O(mn)\) for \(n\) nodes and
\(m\) edges.

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("planar_maximally_filtered_graph", weight="weight")
result = candidate.filter("default").run(graph)
print(result.summary())
```

## References

<div class="method-references" markdown="1">

- Tumminello, M., Aste, T., Di Matteo, T., & Mantegna, R. N. (2005). A tool for filtering information in complex systems. Proceedings of the National Academy of Sciences, 102(30), 10421–10426. [doi:10.1073/pnas.0500298102](https://doi.org/10.1073/pnas.0500298102)

<details class="bibtex" markdown="1">
<summary>BibTeX</summary>

```bibtex
@article{tumminello2005tool,
  author = {Tumminello, M. and Aste, T. and Di Matteo, T. and Mantegna, R. N.},
  title = {A tool for filtering information in complex systems},
  journal = {Proceedings of the National Academy of Sciences},
  year = {2005},
  volume = {102},
  number = {30},
  pages = {10421--10426},
  doi = {10.1073/pnas.0500298102}
}
```

</details>

</div>
