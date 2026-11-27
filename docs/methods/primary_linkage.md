# Primary Linkage

Each node nominates its strongest link. Use it when each node's leading
connection is the signal, as in flows between regions.
{: .lede }

<dl class="method-facts">
<div><dt>Registered name</dt><dd><code>primary_linkage</code></dd></div>
<div><dt>Scores</dt><dd>Edges</dd></div>
<div><dt>Statistic</dt><dd><code>primary_linkage_selected</code>, higher is stronger</dd></div>
<div><dt>Directed graphs</dt><dd>Not supported</dd></div>
<div><dt>Weights</dt><dd>Required, finite numbers</dd></div>
<div><dt>Suggested filter</dt><dd>Selection flag = 1</dd></div>
</dl>

## How it works

Each node nominates the incident edge with the largest weight. An edge is
kept if at least one endpoint nominates it. Equal weights are ordered by
internal `edge_id`.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `weight` | `"auto"` | Edge attribute to read. `"auto"` uses `weight` when every edge has it; see [how weights are chosen](../reference/methods.md#how-weights-are-chosen). |

## Output columns

| Column | Meaning |
| --- | --- |
| `primary_linkage_weight` | The weight read from the graph. |
| `primary_linkage_endpoint_count` | How many endpoints nominated the edge: 0, 1, or 2. |
| `primary_linkage_selected` | 1 when at least one endpoint nominated it, 0 otherwise. |

Every row also has `edge_id`, `source`, and `target`, plus Netbone's internal
`source_id` and `target_id`.

## Cost

Linear in the number of edges.

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("primary_linkage", weight="weight")
result = candidate.filter("default").run(graph)
print(result.summary())
```

## References

<div class="method-references" markdown="1">

- Nystuen, J. D., & Dacey, M. F. (1961). A graph theory interpretation of nodal regions. Papers of the Regional Science Association, 7(1), 29–42. [doi:10.1111/j.1435-5597.1961.tb01769.x](https://doi.org/10.1111/j.1435-5597.1961.tb01769.x)

<details class="bibtex" markdown="1">
<summary>BibTeX</summary>

```bibtex
@article{nystuen1961graph,
  author = {Nystuen, J. D. and Dacey, M. F.},
  title = {A graph theory interpretation of nodal regions},
  journal = {Papers of the Regional Science Association},
  year = {1961},
  volume = {7},
  number = {1},
  pages = {29--42},
  doi = {10.1111/j.1435-5597.1961.tb01769.x}
}
```

</details>

</div>
