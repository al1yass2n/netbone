# Multiple Linkage

Lets each node keep its few dominant links instead of one, by fitting how its
weight is spread.
{: .lede }

<dl class="method-facts">
<div><dt>Registered name</dt><dd><code>multiple_linkage</code></dd></div>
<div><dt>Scores</dt><dd>Edges</dd></div>
<div><dt>Statistic</dt><dd><code>multiple_linkage_selected</code>, higher is stronger</dd></div>
<div><dt>Directed graphs</dt><dd>Not supported</dd></div>
<div><dt>Weights</dt><dd>Required, non-negative</dd></div>
<div><dt>Suggested filter</dt><dd>Selection flag = 1</dd></div>
</dl>

## How it works

Each node sorts its positive incident weights in descending order and
compares their shares with the ideal top-\(k\) patterns, where \(k\) links get
equal shares and the rest get none. The prefix with the best fit is the
node's selection, and an edge is kept if either endpoint selects it.
Zero-weight edges stay in the table but are left out of the fit. Equal
weights use internal `edge_id` ordering.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `weight` | `"auto"` | Edge attribute to read. `"auto"` uses `weight` when every edge has it; see [how weights are chosen](../reference/methods.md#how-weights-are-chosen). |

## Output columns

| Column | Meaning |
| --- | --- |
| `multiple_linkage_weight` | The weight read from the graph. |
| `multiple_linkage_endpoint_count` | How many endpoints selected the edge: 0, 1, or 2. |
| `multiple_linkage_selected` | 1 when at least one endpoint selected it, 0 otherwise. |

Every row also has `edge_id`, `source`, and `target`, plus Netbone's internal
`source_id` and `target_id`.

## Cost

Sorting each node's incident weights: about \(O(m \log d)\) for \(m\) edges
and largest degree \(d\).

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("multiple_linkage", weight="weight")
result = candidate.filter("default").run(graph)
print(result.summary())
```

## References

<div class="method-references" markdown="1">

- Van Nuffel, N. (2007). Determination of the number of significant flows in origin–destination specific analysis: The case of commuting in Flanders. Regional Studies, 41(4), 509–524. [doi:10.1080/00343400701281808](https://doi.org/10.1080/00343400701281808)

<details class="bibtex" markdown="1">
<summary>BibTeX</summary>

```bibtex
@article{vannuffel2007determination,
  author = {Van Nuffel, N.},
  title = {Determination of the number of significant flows in origin–destination specific analysis: The case of commuting in Flanders},
  journal = {Regional Studies},
  year = {2007},
  volume = {41},
  number = {4},
  pages = {509--524},
  doi = {10.1080/00343400701281808}
}
```

</details>

</div>
