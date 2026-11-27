# Globally and Locally Adaptive Network Backbone

Combines how much an edge carries shortest paths with how dominant it is at
each endpoint. The exponent `c` sets how much degree matters.
{: .lede }

<dl class="method-facts">
<div><dt>Registered name</dt><dd><code>glanb</code></dd></div>
<div><dt>Scores</dt><dd>Edges</dd></div>
<div><dt>Statistic</dt><dd><code>glanb_significance</code>, lower is stronger</dd></div>
<div><dt>Directed graphs</dt><dd>Not supported</dd></div>
<div><dt>Weights</dt><dd>Optional, positive</dd></div>
<div><dt>Suggested filter</dt><dd>Significance</dd></div>
</dl>

## How it works

At an endpoint of degree \(k > 1\), let \(p\) be the edge's involvement, its
share of the shortest paths that leave the endpoint through it. The endpoint
statistic is

$$
g = \left(1 - p\right)^{(k - 1)^{c}}
$$

and the edge keeps the more significant of its two endpoint values. A very
large `c` gives the exact limit: 0 when \(p > 0\) and 1 when \(p = 0\). Set `c`
explicitly and record it when you compare results.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `c` | required | Non-negative exponent on the degree term. |
| `weight` | `"auto"` | Edge attribute to read. `"auto"` uses `weight` when every edge has it and runs unweighted otherwise; `None` always runs unweighted. See [how weights are chosen](../reference/methods.md#how-weights-are-chosen). Weights are read as strengths and inverted for path lengths. |

## Output columns

| Column | Meaning |
| --- | --- |
| `glanb_weight` | The weight read from the graph. |
| `glanb_distance` | The path length used for the edge. |
| `glanb_source_involvement` | The involvement at the source. |
| `glanb_target_involvement` | The involvement at the target. |
| `glanb_source_significance` | The statistic at the source. |
| `glanb_target_significance` | The statistic at the target. |
| `glanb_significance` | The edge statistic. |

Every row also has `edge_id`, `source`, and `target`, plus Netbone's internal
`source_id` and `target_id`.

## Cost

One shortest-path search from every node: about \(O(nm + n^2 \log n)\).

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
pipeline = nb.pipeline().score("glanb", c=1.0, weight="weight")
backbone = pipeline.filter("default").run(graph)
print(backbone.summary())
```

## References

<div class="method-references" markdown="1">

- Zhang, X., Zhang, Z., Zhao, H., Wang, Q., & Zhu, J. (2014). Extracting the globally and locally adaptive backbone of complex networks. PLoS ONE, 9(6), e100428. [doi:10.1371/journal.pone.0100428](https://doi.org/10.1371/journal.pone.0100428)

<details class="bibtex" markdown="1">
<summary>BibTeX</summary>

```bibtex
@article{zhang2014extracting,
  author = {Zhang, X. and Zhang, Z. and Zhao, H. and Wang, Q. and Zhu, J.},
  title = {Extracting the globally and locally adaptive backbone of complex networks},
  journal = {PLoS ONE},
  year = {2014},
  volume = {9},
  number = {6},
  pages = {e100428},
  doi = {10.1371/journal.pone.0100428}
}
```

</details>

</div>
