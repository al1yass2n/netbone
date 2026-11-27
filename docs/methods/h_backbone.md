# H-Backbone

Combines strong links and bridging links, each chosen by an h-index cutoff.
{: .lede }

<dl class="method-facts">
<div><dt>Registered name</dt><dd><code>h_backbone</code></dd></div>
<div><dt>Scores</dt><dd>Edges</dd></div>
<div><dt>Statistic</dt><dd><code>h_backbone_selected</code>, higher is stronger</dd></div>
<div><dt>Directed graphs</dt><dd>Not supported</dd></div>
<div><dt>Weights</dt><dd>Required, positive</dd></div>
<div><dt>Suggested filter</dt><dd>Selection flag = 1</dd></div>
</dl>

## How it works

Two h-index cutoffs are computed. \(h_s\) is the largest \(h\) such that \(h\)
edges have weight at least \(h\). \(h_b\) is the same over the bridging score,
the unnormalized edge betweenness divided by the number of nodes. An edge is
kept if it meets at least one positive cutoff.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `weight` | `"auto"` | Edge attribute to read. `"auto"` uses `weight` when every edge has it; see [how weights are chosen](../reference/methods.md#how-weights-are-chosen). |
| `distance_transform` | `"inverse"` | `"inverse"` reads larger weights as stronger, closer ties and uses `1 / weight` as path length. `"identity"` reads the weight as a length. |

## Output columns

| Column | Meaning |
| --- | --- |
| `h_backbone_weight` | The weight read from the graph. |
| `h_backbone_bridge` | The bridging score. |
| `h_backbone_h_strength` | The weight cutoff \(h_s\). |
| `h_backbone_h_bridge` | The bridging cutoff \(h_b\). |
| `h_backbone_selected` | 1 for a kept edge, 0 otherwise. |

Every row also has `edge_id`, `source`, and `target`, plus Netbone's internal
`source_id` and `target_id`.

## Cost

Dominated by edge betweenness: about \(O(nm + n^2 \log n)\).

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
pipeline = nb.pipeline().score("h_backbone", weight="weight")
backbone = pipeline.filter("default").run(graph)
print(backbone.summary())
```

## References

<div class="method-references" markdown="1">

- Zhang, R. J., Stanley, H. E., & Ye, F. Y. (2018). Extracting h-backbone as a core structure in weighted networks. Scientific Reports, 8, 14356. [doi:10.1038/s41598-018-32430-1](https://doi.org/10.1038/s41598-018-32430-1)

<details class="bibtex" markdown="1">
<summary>BibTeX</summary>

```bibtex
@article{zhang2018extracting,
  author = {Zhang, R. J. and Stanley, H. E. and Ye, F. Y.},
  title = {Extracting h-backbone as a core structure in weighted networks},
  journal = {Scientific Reports},
  year = {2018},
  volume = {8},
  pages = {14356},
  doi = {10.1038/s41598-018-32430-1}
}
```

</details>

</div>
