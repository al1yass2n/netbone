# Locally Adaptive Network Sparsification

Compares an edge's share of an endpoint's strength with the other shares at
that endpoint, without assuming a null model.
{: .lede }

<dl class="method-facts">
<div><dt>Registered name</dt><dd><code>lans</code></dd></div>
<div><dt>Scores</dt><dd>Edges</dd></div>
<div><dt>Statistic</dt><dd><code>lans_pvalue</code>, lower is stronger</dd></div>
<div><dt>Directed graphs</dt><dd>Supported</dd></div>
<div><dt>Weights</dt><dd>Required, positive</dd></div>
<div><dt>Suggested filter</dt><dd>Significance</dd></div>
</dl>

## How it works

At an endpoint \(i\), each incident edge carries the share \(f = w / s_i\) of
the strength \(s_i\). The p-value of an edge is the fraction of the \(k_i\)
incident edges whose share is larger than its own:

$$
p_i = 1 - \hat{F}_i(f) = \frac{\left|\{\, e' \ni i : f_{e'} > f \,\}\right|}{k_i}
$$

This empirical tail replaces the uniform model used by
[Disparity](disparity.md). A directed arc is compared with the source's
outgoing and the target's incoming distribution.

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
| `lans_weight` | The weight read from the graph. |
| `lans_source_fraction` | The edge's share of the source's strength. |
| `lans_target_fraction` | The edge's share of the target's strength. |
| `lans_source_pvalue` | The p-value at the source. |
| `lans_target_pvalue` | The p-value at the target. |
| `lans_pvalue` | The combined p-value. |

Every row also has `edge_id`, `source`, and `target`, plus Netbone's internal
`source_id` and `target_id`.

## Cost

Sorting each node's incident weights: about \(O(m \log d)\) for \(m\) edges
and largest degree \(d\).

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
pipeline = nb.pipeline().score("lans", weight="weight", leaf_policy="ignore")
backbone = pipeline.filter("default").run(graph)
print(backbone.summary())
```

## References

<div class="method-references" markdown="1">

- Foti, N. J., Hughes, J. M., & Rockmore, D. N. (2011). Nonparametric sparsification of complex multiscale networks. PLoS ONE, 6(2), e16431. [doi:10.1371/journal.pone.0016431](https://doi.org/10.1371/journal.pone.0016431)

<details class="bibtex" markdown="1">
<summary>BibTeX</summary>

```bibtex
@article{foti2011nonparametric,
  author = {Foti, N. J. and Hughes, J. M. and Rockmore, D. N.},
  title = {Nonparametric sparsification of complex multiscale networks},
  journal = {PLoS ONE},
  year = {2011},
  volume = {6},
  number = {2},
  pages = {e16431},
  doi = {10.1371/journal.pone.0016431}
}
```

</details>

</div>
