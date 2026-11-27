# Marginal Likelihood

Tests whether an edge's count is larger than expected from its endpoints'
total counts.
{: .lede }

<dl class="method-facts">
<div><dt>Registered name</dt><dd><code>marginal_likelihood</code></dd></div>
<div><dt>Scores</dt><dd>Edges</dd></div>
<div><dt>Statistic</dt><dd><code>marginal_likelihood_pvalue</code>, lower is stronger</dd></div>
<div><dt>Directed graphs</dt><dd>Not supported</dd></div>
<div><dt>Weights</dt><dd>Required, positive whole numbers</dd></div>
<div><dt>Suggested filter</dt><dd>Significance</dd></div>
</dl>

## How it works

For an edge between nodes with strengths \(s_i\) and \(s_j\) in a graph with
total count \(W\), the observed count \(w_{ij}\) is compared with a binomial
null model:

$$
X \sim \mathrm{Binomial}\left(W, \frac{s_i s_j}{2W^2}\right), \qquad
p = \Pr\left[X \geq w_{ij}\right]
$$

Floating-point values that hold whole counts are accepted. Use a
continuous-weight method when the values are rates or averages.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `weight` | `"auto"` | Edge attribute to read. `"auto"` uses `weight` when every edge has it; see [how weights are chosen](../reference/methods.md#how-weights-are-chosen). |

## Output columns

| Column | Meaning |
| --- | --- |
| `marginal_likelihood_weight` | The count read from the graph. |
| `marginal_likelihood_source_strength` | The source's total count. |
| `marginal_likelihood_target_strength` | The target's total count. |
| `marginal_likelihood_probability` | The binomial success probability. |
| `marginal_likelihood_pvalue` | The p-value. |

Every row also has `edge_id`, `source`, and `target`, plus Netbone's internal
`source_id` and `target_id`.

## Cost

One binomial tail per edge, so linear in the number of edges.

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("marginal_likelihood", weight="weight")
result = candidate.filter("significance", alpha=0.05, correction="holm").run(graph)
print(result.summary())
```

## References

<div class="method-references" markdown="1">

- Dianati, N. (2016). Unwinding the hairball graph: Pruning algorithms for weighted complex networks. Physical Review E, 93(1), 012304. [doi:10.1103/PhysRevE.93.012304](https://doi.org/10.1103/PhysRevE.93.012304)

<details class="bibtex" markdown="1">
<summary>BibTeX</summary>

```bibtex
@article{dianati2016unwinding,
  author = {Dianati, N.},
  title = {Unwinding the hairball graph: Pruning algorithms for weighted complex networks},
  journal = {Physical Review E},
  year = {2016},
  volume = {93},
  number = {1},
  pages = {012304},
  doi = {10.1103/PhysRevE.93.012304}
}
```

</details>

</div>
