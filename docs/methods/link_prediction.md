# Link Prediction

Scores each observed link by how well a link-prediction similarity would have
predicted it after removing it from the graph.
{: .lede }

<dl class="method-facts">
<div><dt>Registered name</dt><dd><code>link_prediction</code></dd></div>
<div><dt>Scores</dt><dd>Edges</dd></div>
<div><dt>Statistic</dt><dd><code>link_prediction_similarity</code>, higher is stronger</dd></div>
<div><dt>Directed graphs</dt><dd>Supported</dd></div>
<div><dt>Weights</dt><dd>Optional, positive</dd></div>
<div><dt>Suggested filter</dt><dd>10% fraction with explicit direction</dd></div>
</dl>

## How it works

Each edge \((u, v)\) is removed from a working copy of the graph and scored
with one similarity. With weights, each edge uses \(w^{\alpha}\), where
\(\alpha\) is `weight_alpha`; without weights every edge counts 1.

| `similarity` | Score |
| --- | --- |
| `"preferential_attachment"` | \(s_u \, s_v\), the product of the endpoint strengths (degrees when unweighted) |
| `"shortest_path"` | \(1 / d(u, v)\), the inverse length of the best remaining path, or 0 when none is left |
| `"local_path"` | the weighted count of two-step paths plus \(\epsilon\) times the weighted count of three-step paths |

On a directed graph, preferential attachment uses the source's out-strength
and the target's in-strength, and path similarities follow the arc direction.
For fraction or default filtering, choose `direction="higher"` to keep
well-supported links or `"lower"` to keep links with weak structural support.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `similarity` | required | `"preferential_attachment"`, `"shortest_path"`, or `"local_path"`. |
| `epsilon` | `1.0` | Weight of three-step paths in `"local_path"`. |
| `weight` | `"auto"` | Edge attribute to read. `"auto"` uses `weight` when every edge has it and runs unweighted otherwise; `None` always runs unweighted. See [how weights are chosen](../reference/methods.md#how-weights-are-chosen). |
| `weight_alpha` | `1.0` | Exponent applied to each weight before scoring. |
| `distance_transform` | `"inverse"` | `"inverse"` reads larger weights as stronger, closer ties and uses `1 / weight` as path length. `"identity"` reads the weight as a length. |

## Output columns

| Column | Meaning |
| --- | --- |
| `link_prediction_similarity` | The similarity score. |
| `link_prediction_similarity_method` | The similarity that produced it. |
| `link_prediction_edge_weight` | The weight read from the graph. |
| `link_prediction_edge_effective_weight` | The weight after `weight_alpha`. |
| `link_prediction_source_degree`, `…_target_degree` | Endpoint degrees, for preferential attachment. |
| `link_prediction_source_strength`, `…_target_strength` | Endpoint strengths, for preferential attachment. |
| `link_prediction_shortest_path_length` | The remaining path length, for shortest path. |
| `link_prediction_disconnected` | Whether no path remained, for shortest path. |
| `link_prediction_paths_length_2`, `…_3` | Path counts, for local path; the `weighted_` columns hold the weighted sums. |

Every row also has `edge_id`, `source`, and `target`, plus Netbone's internal
`source_id` and `target_id`.

## Cost

Preferential attachment is linear in the number of edges. Local path grows
with \(d_u d_v\) per edge, so hubs dominate. Shortest path runs one path
search per edge, about \(O(m(m + n \log n))\), and is the slowest choice.

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score("link_prediction", similarity="local_path")
result = candidate.filter("fraction", fraction=0.5, direction="lower").run(graph)
print(result.summary())
```

## References

<div class="method-references" markdown="1">

- Yassin, A., Cherifi, H., Seba, H., & Togni, O. (2025). High and low similarity backbone extraction using similarity-based link prediction. Applied Network Science, 10(1). [doi:10.1007/s41109-025-00705-y](https://doi.org/10.1007/s41109-025-00705-y)

<details class="bibtex" markdown="1">
<summary>BibTeX</summary>

```bibtex
@article{yassin2025high,
  author = {Yassin, A. and Cherifi, H. and Seba, H. and Togni, O.},
  title = {High and low similarity backbone extraction using similarity-based link prediction},
  journal = {Applied Network Science},
  year = {2025},
  volume = {10},
  number = {1},
  doi = {10.1007/s41109-025-00705-y}
}
```

</details>

</div>
