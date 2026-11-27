# Edge Betweenness

Ranks edges by their share of shortest paths between node pairs. It can
highlight links that connect regions even when their weights are modest.
{: .lede }

<dl class="method-facts">
<div><dt>Registered name</dt><dd><code>edge_betweenness</code></dd></div>
<div><dt>Scores</dt><dd>Edges</dd></div>
<div><dt>Statistic</dt><dd><code>edge_betweenness</code>, higher is stronger</dd></div>
<div><dt>Directed graphs</dt><dd>Not supported</dd></div>
<div><dt>Weights</dt><dd>Optional, positive</dd></div>
<div><dt>Suggested filter</dt><dd>10% fraction</dd></div>
</dl>

## How it works

For each pair of nodes \(s, t\), \(\sigma_{st}\) counts the shortest paths
between them and \(\sigma_{st}(e)\) counts those that use edge \(e\):

$$
b(e) = \sum_{s \neq t} \frac{\sigma_{st}(e)}{\sigma_{st}}
$$

With `normalized=True` the sum is divided by the number of node pairs.
Weighted paths use the distance chosen by `distance_transform`; unweighted
paths count hops.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `weight` | `"auto"` | Edge attribute to read. `"auto"` uses `weight` when every edge has it and runs unweighted otherwise; `None` always runs unweighted. See [how weights are chosen](../reference/methods.md#how-weights-are-chosen). |
| `distance_transform` | `"inverse"` | `"inverse"` reads larger weights as stronger, closer ties and uses `1 / weight` as path length. `"identity"` reads the weight as a length. |
| `normalized` | `True` | Divide by the number of node pairs. |

## Output columns

| Column | Meaning |
| --- | --- |
| `edge_betweenness_weight` | The weight read from the graph. |
| `edge_betweenness_distance` | The path length used for the edge. |
| `edge_betweenness` | The betweenness score. |

Every row also has `edge_id`, `source`, and `target`, plus Netbone's internal
`source_id` and `target_id`.

## Cost

One shortest-path search from every node: about \(O(nm)\) unweighted and
\(O(nm + n^2 \log n)\) weighted, for \(n\) nodes and \(m\) edges. This is slow
on graphs with many thousands of nodes.

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
pipeline = nb.pipeline().score("edge_betweenness")
backbone = pipeline.filter("default").run(graph)
print(backbone.summary())
```

## References

<div class="method-references" markdown="1">

- Girvan, M., & Newman, M. E. J. (2002). Community structure in social and biological networks. Proceedings of the National Academy of Sciences, 99(12), 7821–7826. [doi:10.1073/pnas.122653799](https://doi.org/10.1073/pnas.122653799)

<details class="bibtex" markdown="1">
<summary>BibTeX</summary>

```bibtex
@article{girvan2002community,
  author = {Girvan, M. and Newman, M. E. J.},
  title = {Community structure in social and biological networks},
  journal = {Proceedings of the National Academy of Sciences},
  year = {2002},
  volume = {99},
  number = {12},
  pages = {7821--7826},
  doi = {10.1073/pnas.122653799}
}
```

</details>

</div>
