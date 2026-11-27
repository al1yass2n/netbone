# Noise Corrected

Estimates how much an edge's count exceeds what its endpoints' totals predict,
and how certain that estimate is.
{: .lede }

<dl class="method-facts">
<div><dt>Registered name</dt><dd><code>noise_corrected</code></dd></div>
<div><dt>Scores</dt><dd>Edges</dd></div>
<div><dt>Statistic</dt><dd><code>noise_corrected_z</code>, higher is stronger</dd></div>
<div><dt>Directed graphs</dt><dd>Supported</dd></div>
<div><dt>Weights</dt><dd>Required, positive whole numbers</dd></div>
<div><dt>Suggested filter</dt><dd>Score > 1.64</dd></div>
</dl>

## How it works

Netbone follows the authors' Bayesian reference code. For each edge it
estimates the lift \(L\) of the observed count over the count expected from
the endpoint totals, and the standard deviation \(\sigma\) of that lift. The
primary statistic is

$$
z = \frac{L}{\sigma}
$$

Directed input keeps separate outgoing and incoming totals. The default
filter keeps edges with \(z > 1.64\). A degenerate total can leave \(\sigma\)
undefined, so inspect the warnings and those rows.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `weight` | `"auto"` | Edge attribute to read. `"auto"` uses `weight` when every edge has it; see [how weights are chosen](../reference/methods.md#how-weights-are-chosen). |

## Output columns

| Column | Meaning |
| --- | --- |
| `noise_corrected_score` | The lift \(L\). |
| `noise_corrected_stddev` | Its standard deviation \(\sigma\). |
| `noise_corrected_z` | The lift divided by its standard deviation. |

Every row also has `edge_id`, `source`, and `target`, plus Netbone's internal
`source_id` and `target_id`.

## Cost

Linear in the number of edges.

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
pipeline = nb.pipeline().score("noise_corrected", weight="weight")
backbone = pipeline.filter("default").run(graph)
print(backbone.summary())
```

## References

<div class="method-references" markdown="1">

- Coscia, M., & Neffke, F. M. H. (2017). Network backboning with noisy data. In 2017 IEEE 33rd International Conference on Data Engineering (ICDE), 425–436. IEEE. [doi:10.1109/ICDE.2017.100](https://doi.org/10.1109/ICDE.2017.100)

<details class="bibtex" markdown="1">
<summary>BibTeX</summary>

```bibtex
@inproceedings{coscia2017network,
  author = {Coscia, M. and Neffke, F. M. H.},
  title = {Network backboning with noisy data},
  booktitle = {2017 IEEE 33rd International Conference on Data Engineering (ICDE)},
  year = {2017},
  publisher = {IEEE},
  pages = {425--436},
  doi = {10.1109/ICDE.2017.100}
}
```

</details>

</div>
