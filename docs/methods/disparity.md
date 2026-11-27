# Disparity

Tests whether an edge carries an unusually large share of an endpoint's
strength, compared with weights spread uniformly at random.
{: .lede }

<dl class="method-facts">
<div><dt>Registered name</dt><dd><code>disparity</code></dd></div>
<div><dt>Scores</dt><dd>Edges</dd></div>
<div><dt>Statistic</dt><dd><code>disparity_pvalue</code>, lower is stronger</dd></div>
<div><dt>Directed graphs</dt><dd>Supported</dd></div>
<div><dt>Weights</dt><dd>Required, positive</dd></div>
<div><dt>Suggested filter</dt><dd>Significance</dd></div>
</dl>

## How it works

At an endpoint \(i\) with degree \(k_i > 1\) and strength \(s_i\), an edge with
weight \(w\) carries the share \(f = w / s_i\). Under the uniform null model its
p-value is

$$
p_i = \left(1 - f\right)^{k_i - 1}
$$

A directed arc uses the source's outgoing and the target's incoming weights
and degrees. The two endpoint p-values are combined by `pvalue_aggregation`.

## Combining the two ends

Each edge gets one p-value per end: on a directed graph, \(p_{out}\) from the
source's outgoing distribution and \(p_{in}\) from the target's incoming
distribution. `pvalue_aggregation` turns them into the edge p-value that the
significance filter compares with `alpha`.

| `pvalue_aggregation` | Edge p-value | Keeps an edge that is |
| --- | --- | --- |
| `"min"` (default) | \(\min(p_{out}, p_{in})\) | important for at least one end |
| `"max"` | \(\max(p_{out}, p_{in})\) | important for both ends |
| `"average"` | mean of the two | balanced between the two ends |
| `"out"` (directed only) | \(p_{out}\) | important for the sender |
| `"in"` (directed only) | \(p_{in}\) | important for the receiver |

`"out"` and `"in"` raise a `ConfigurationError` on an undirected graph, where
an edge has no source or target end.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `weight` | `"auto"` | Edge attribute to read. `"auto"` uses `weight` when every edge has it; see [how weights are chosen](../reference/methods.md#how-weights-are-chosen). |
| `pvalue_aggregation` | `"min"` | How the two endpoint p-values become the edge p-value: `"min"`, `"max"`, `"average"`, or, on directed graphs, `"out"` or `"in"`. See [Combining the two ends](#combining-the-two-ends). |
| `leaf_policy` | `"zero"` | `"zero"` gives an endpoint of degree one the p-value 0. `"ignore"` leaves that endpoint out, and an edge with no remaining endpoint gets p-value 1. |

## Output columns

| Column | Meaning |
| --- | --- |
| `disparity_weight` | The weight read from the graph. |
| `disparity_source_fraction` | The edge's share of the source's strength. |
| `disparity_target_fraction` | The edge's share of the target's strength. |
| `disparity_source_pvalue` | The p-value at the source. |
| `disparity_target_pvalue` | The p-value at the target. |
| `disparity_pvalue` | The combined p-value. |

Every row also has `edge_id`, `source`, and `target`, plus Netbone's internal
`source_id` and `target_id`.

## Cost

Linear in the number of edges.

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("disparity", weight="weight", leaf_policy="ignore")
result = candidate.filter("significance", alpha=0.05, correction="holm").run(graph)
print(result.summary())
```

## References

<div class="method-references" markdown="1">

- Serrano, M. Á., Boguñá, M., & Vespignani, A. (2009). Extracting the multiscale backbone of complex weighted networks. Proceedings of the National Academy of Sciences, 106(16), 6483–6488. [doi:10.1073/pnas.0808904106](https://doi.org/10.1073/pnas.0808904106)

<details class="bibtex" markdown="1">
<summary>BibTeX</summary>

```bibtex
@article{serrano2009extracting,
  author = {Serrano, M. Á. and Boguñá, M. and Vespignani, A.},
  title = {Extracting the multiscale backbone of complex weighted networks},
  journal = {Proceedings of the National Academy of Sciences},
  year = {2009},
  volume = {106},
  number = {16},
  pages = {6483--6488},
  doi = {10.1073/pnas.0808904106}
}
```

</details>

</div>
