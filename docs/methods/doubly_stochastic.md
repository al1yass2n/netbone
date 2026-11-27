# Doubly Stochastic

Rescales the weights so that every node's row and column sum to one, then
keeps the strongest rescaled links that connect each component.
{: .lede }

<dl class="method-facts">
<div><dt>Registered name</dt><dd><code>doubly_stochastic</code></dd></div>
<div><dt>Scores</dt><dd>Edges</dd></div>
<div><dt>Statistic</dt><dd><code>doubly_stochastic_score</code>, higher is stronger</dd></div>
<div><dt>Directed graphs</dt><dd>Not supported</dd></div>
<div><dt>Weights</dt><dd>Required, positive</dd></div>
<div><dt>Suggested filter</dt><dd>Connected-selection flag = 1</dd></div>
</dl>

## How it works

For each connected component, the weighted adjacency matrix \(W\) is filled
with a small \(\epsilon\) and balanced by Sinkhorn iteration: diagonal
matrices \(D_1\) and \(D_2\) are found so that

$$
P = D_1 \left(W + \epsilon\right) D_2
$$

has unit row and column sums. The score of an edge is its entry in \(P\). The
default selection adds edges in descending score order until each input
component is connected. In `"relative"` mode \(\epsilon\) is multiplied by the
mean edge weight of the component; in `"absolute"` mode it is used as given.
Check convergence warnings before interpreting the scores.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `weight` | `"auto"` | Edge attribute to read. `"auto"` uses `weight` when every edge has it; see [how weights are chosen](../reference/methods.md#how-weights-are-chosen). |
| `epsilon` | `1e-4` | Smoothing added to the whole matrix before balancing. |
| `epsilon_mode` | `"relative"` | `"relative"` scales `epsilon` by the mean edge weight; `"absolute"` uses it as given. |
| `tolerance` | `1e-12` | Largest row or column error accepted as converged. |
| `max_iterations` | `1000` | Most Sinkhorn iterations before a warning. |

## Output columns

| Column | Meaning |
| --- | --- |
| `doubly_stochastic_weight` | The weight read from the graph. |
| `doubly_stochastic_score` | The balanced value. |
| `doubly_stochastic_connected_order` | The order in which the edge joined the connected selection, if it did. |
| `doubly_stochastic_connected_selected` | 1 for an edge in the connected selection, 0 otherwise. |

Every row also has `edge_id`, `source`, and `target`, plus Netbone's internal
`source_id` and `target_id`.

## Cost

The matrix is dense: memory grows with \(n_c^2\) for a component of \(n_c\)
nodes, and each iteration costs \(O(n_c^2)\). Avoid it on components with tens
of thousands of nodes.

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("doubly_stochastic", weight="weight")
result = candidate.filter("default").run(graph)
print(result.summary())
```

## References

<div class="method-references" markdown="1">

- Slater, P. B. (2009). A two-stage algorithm for extracting the multiscale backbone of complex weighted networks. Proceedings of the National Academy of Sciences, 106(26), E66. [doi:10.1073/pnas.0904725106](https://doi.org/10.1073/pnas.0904725106)

<details class="bibtex" markdown="1">
<summary>BibTeX</summary>

```bibtex
@article{slater2009twostage,
  author = {Slater, P. B.},
  title = {A two-stage algorithm for extracting the multiscale backbone of complex weighted networks},
  journal = {Proceedings of the National Academy of Sciences},
  year = {2009},
  volume = {106},
  number = {26},
  pages = {E66},
  doi = {10.1073/pnas.0904725106}
}
```

</details>

</div>
