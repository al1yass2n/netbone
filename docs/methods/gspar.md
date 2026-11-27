# GSPAR

Ranks links by how many neighbours their endpoints share. Links inside dense
groups score high.
{: .lede }

<dl class="method-facts">
<div><dt>Registered name</dt><dd><code>gspar</code></dd></div>
<div><dt>Scores</dt><dd>Edges</dd></div>
<div><dt>Statistic</dt><dd><code>gspar_jaccard_similarity</code>, higher is stronger</dd></div>
<div><dt>Directed graphs</dt><dd>Not supported</dd></div>
<div><dt>Weights</dt><dd>Ignored</dd></div>
<div><dt>Suggested filter</dt><dd>10% fraction</dd></div>
</dl>

## How it works

The score is the Jaccard similarity of the endpoints' open neighbourhoods
\(N(u)\) and \(N(v)\):

$$
J(u, v) = \frac{\left|N(u) \cap N(v)\right|}{\left|N(u) \cup N(v)\right|}
$$

Use a fraction filter to control how much the global ranking keeps, and
report the realized fraction when scores tie.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `weight` | `"auto"` | Accepted so one loop can pass the same weight to every method. Naming an attribute records a warning, because weights do not change the score. |

## Output columns

| Column | Meaning |
| --- | --- |
| `gspar_jaccard_similarity` | The Jaccard similarity. |

Every row also has `edge_id`, `source`, and `target`, plus Netbone's internal
`source_id` and `target_id`.

## Cost

Linear in the sum of endpoint degrees over all edges.

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("gspar")
result = candidate.filter("fraction", fraction=0.5, tie_policy="exact_stable").run(
    graph
)
print(result.summary())
```

## References

<div class="method-references" markdown="1">

- Satuluri, V., Parthasarathy, S., & Ruan, Y. (2011). Local graph sparsification for scalable clustering. In Proceedings of the 2011 ACM SIGMOD International Conference on Management of Data, 721–732. ACM. [doi:10.1145/1989323.1989399](https://doi.org/10.1145/1989323.1989399)

<details class="bibtex" markdown="1">
<summary>BibTeX</summary>

```bibtex
@inproceedings{satuluri2011local,
  author = {Satuluri, V. and Parthasarathy, S. and Ruan, Y.},
  title = {Local graph sparsification for scalable clustering},
  booktitle = {Proceedings of the 2011 ACM SIGMOD International Conference on Management of Data},
  year = {2011},
  publisher = {ACM},
  pages = {721--732},
  doi = {10.1145/1989323.1989399}
}
```

</details>

</div>
