# Node Strength

Ranks nodes by the total weight of their links. A node with a few strong links
can rank above one with many weak links.
{: .lede }

<dl class="method-facts">
<div><dt>Registered name</dt><dd><code>node_strength</code></dd></div>
<div><dt>Scores</dt><dd>Nodes</dd></div>
<div><dt>Statistic</dt><dd><code>node_strength</code>, higher is stronger</dd></div>
<div><dt>Directed graphs</dt><dd>Supported</dd></div>
<div><dt>Weights</dt><dd>Required, finite numbers</dd></div>
<div><dt>Suggested filter</dt><dd>10% fraction</dd></div>
</dl>

## How it works

The strength of node \(i\) is the sum of the weights on its links:

$$
s_i = \sum_{j} w_{ij}
$$

An isolated node has strength zero. On a directed graph, `direction` chooses
which arcs count: `"total"` adds incoming and outgoing weights, `"in"` gives
in-strength, and `"out"` gives out-strength. An undirected graph has one
strength per node, so `"in"` and `"out"` give the total and add a warning.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `weight` | `"auto"` | Edge attribute to read. `"auto"` uses `weight` when every edge has it; see [how weights are chosen](../reference/methods.md#how-weights-are-chosen). |
| `direction` | `"total"` | `"total"`, `"in"`, or `"out"` on directed graphs. |

## Output columns

| Column | Meaning |
| --- | --- |
| `node_strength` | The strength. |

Every row also has `node_id` and the original `node` label.

## Cost

Linear in the number of edges.

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
# On a directed graph, add direction="in" or "out" to .score().
pipeline = nb.pipeline().score("node_strength", weight="weight")
pipeline = pipeline.filter("fraction", fraction=0.5, tie_policy="exact_stable")
backbone = pipeline.run(graph)
print(backbone.summary())
```

## References

<div class="method-references" markdown="1">

- Barrat, A., Barthélemy, M., Pastor-Satorras, R., & Vespignani, A. (2004). The architecture of complex weighted networks. Proceedings of the National Academy of Sciences, 101(11), 3747–3752. [doi:10.1073/pnas.0400087101](https://doi.org/10.1073/pnas.0400087101)

<details class="bibtex" markdown="1">
<summary>BibTeX</summary>

```bibtex
@article{barrat2004architecture,
  author = {Barrat, A. and Barthélemy, M. and Pastor-Satorras, R. and Vespignani, A.},
  title = {The architecture of complex weighted networks},
  journal = {Proceedings of the National Academy of Sciences},
  year = {2004},
  volume = {101},
  number = {11},
  pages = {3747--3752},
  doi = {10.1073/pnas.0400087101}
}
```

</details>

</div>
