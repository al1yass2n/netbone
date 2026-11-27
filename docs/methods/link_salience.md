# Link Salience

Counts how many nodes have the edge in their shortest-path tree. Salient links
are the ones most nodes rely on to reach the rest of the network.
{: .lede }

<dl class="method-facts">
<div><dt>Registered name</dt><dd><code>link_salience</code></dd></div>
<div><dt>Scores</dt><dd>Edges</dd></div>
<div><dt>Statistic</dt><dd><code>link_salience</code>, higher is stronger</dd></div>
<div><dt>Directed graphs</dt><dd>Supported</dd></div>
<div><dt>Weights</dt><dd>Optional, positive</dd></div>
<div><dt>Suggested filter</dt><dd>Score ≥ 0.5</dd></div>
</dl>

## How it works

For each root node \(r\), \(T(r)\) is the set of edges on shortest paths from
\(r\) to every other node. The salience of an edge is the fraction of the
\(n\) roots whose tree contains it:

$$
S(e) = \frac{1}{n} \sum_{r} \mathbf{1}\left[\, e \in T(r) \,\right]
$$

When two shortest paths tie, both are kept. A directed arc follows outgoing
paths and is still divided by all \(n\) roots, including those that cannot
reach it.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `weight` | `"auto"` | Edge attribute to read. `"auto"` uses `weight` when every edge has it and runs unweighted otherwise; `None` always runs unweighted. See [how weights are chosen](../reference/methods.md#how-weights-are-chosen). |
| `distance_transform` | `"inverse"` | `"inverse"` reads larger weights as stronger, closer ties and uses `1 / weight` as path length. `"identity"` reads the weight as a length. |

## Output columns

| Column | Meaning |
| --- | --- |
| `link_salience_weight` | The weight read from the graph. |
| `link_salience_distance` | The path length used for the edge. |
| `link_salience_count` | The number of roots whose tree contains the edge. |
| `link_salience` | The salience, the count divided by the number of nodes. |

Every row also has `edge_id`, `source`, and `target`, plus Netbone's internal
`source_id` and `target_id`.

## Cost

One shortest-path search from every node: about \(O(nm + n^2 \log n)\) for
\(n\) nodes and \(m\) edges.

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("link_salience", weight="weight")
result = candidate.filter("default").run(graph)
print(result.summary())
```

## References

<div class="method-references" markdown="1">

- Grady, D., Thiemann, C., & Brockmann, D. (2012). Robust classification of salient links in complex networks. Nature Communications, 3, 864. [doi:10.1038/ncomms1847](https://doi.org/10.1038/ncomms1847)

<details class="bibtex" markdown="1">
<summary>BibTeX</summary>

```bibtex
@article{grady2012robust,
  author = {Grady, D. and Thiemann, C. and Brockmann, D.},
  title = {Robust classification of salient links in complex networks},
  journal = {Nature Communications},
  year = {2012},
  volume = {3},
  pages = {864},
  doi = {10.1038/ncomms1847}
}
```

</details>

</div>
