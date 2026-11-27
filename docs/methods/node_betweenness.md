# Node Betweenness

Ranks nodes by their share of shortest paths between other nodes. It finds
brokers that connect parts of the network.
{: .lede }

<dl class="method-facts">
<div><dt>Registered name</dt><dd><code>node_betweenness</code></dd></div>
<div><dt>Scores</dt><dd>Nodes</dd></div>
<div><dt>Statistic</dt><dd><code>node_betweenness</code>, higher is stronger</dd></div>
<div><dt>Directed graphs</dt><dd>Not supported</dd></div>
<div><dt>Weights</dt><dd>Optional, positive</dd></div>
<div><dt>Suggested filter</dt><dd>10% fraction</dd></div>
</dl>

## How it works

For each pair of nodes \(s, t\), \(\sigma_{st}\) counts the shortest paths
between them and \(\sigma_{st}(v)\) counts those that pass through \(v\):

$$
b(v) = \sum_{s \neq v \neq t} \frac{\sigma_{st}(v)}{\sigma_{st}}
$$

With `normalized=True` the sum is divided by the number of pairs that exclude
\(v\). Set `endpoints=True` to also count paths that start or end at \(v\). The
backbone keeps the links among the selected nodes, so paths through omitted
nodes can disappear.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `weight` | `"auto"` | Edge attribute to read. `"auto"` uses `weight` when every edge has it and runs unweighted otherwise; `None` always runs unweighted. See [how weights are chosen](../reference/methods.md#how-weights-are-chosen). |
| `distance_transform` | `"inverse"` | `"inverse"` reads larger weights as stronger, closer ties and uses `1 / weight` as path length. `"identity"` reads the weight as a length. |
| `normalized` | `True` | Divide by the number of node pairs. |
| `endpoints` | `False` | Count path endpoints in the score. |

## Output columns

| Column | Meaning |
| --- | --- |
| `node_betweenness` | The betweenness score. |

Every row also has `node_id` and the original `node` label.

## Cost

Brandes's algorithm: about \(O(nm)\) unweighted and \(O(nm + n^2 \log n)\)
weighted.

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
pipeline = nb.pipeline().score("node_betweenness")
pipeline = pipeline.filter("fraction", fraction=0.5, tie_policy="exact_stable")
backbone = pipeline.run(graph)
print(backbone.summary())
```

## References

Freeman defined the measure. Netbone computes it with Brandes's algorithm
through NetworkX.

<div class="method-references" markdown="1">

- Freeman, L. C. (1977). A set of measures of centrality based on betweenness. Sociometry, 40(1), 35–41. [doi:10.2307/3033543](https://doi.org/10.2307/3033543)
- Brandes, U. (2001). A faster algorithm for betweenness centrality. Journal of Mathematical Sociology, 25(2), 163–177. [doi:10.1080/0022250X.2001.9990249](https://doi.org/10.1080/0022250X.2001.9990249)

<details class="bibtex" markdown="1">
<summary>BibTeX</summary>

```bibtex
@article{freeman1977set,
  author = {Freeman, L. C.},
  title = {A set of measures of centrality based on betweenness},
  journal = {Sociometry},
  year = {1977},
  volume = {40},
  number = {1},
  pages = {35--41},
  doi = {10.2307/3033543}
}

@article{brandes2001faster,
  author = {Brandes, U.},
  title = {A faster algorithm for betweenness centrality},
  journal = {Journal of Mathematical Sociology},
  year = {2001},
  volume = {25},
  number = {2},
  pages = {163--177},
  doi = {10.1080/0022250X.2001.9990249}
}
```

</details>

</div>
