# Link Prediction Isolation Forest

Fits an Isolation Forest to link-prediction similarities and scores each edge
by how unusual it is among all edges.
{: .lede }

<dl class="method-facts">
<div><dt>Registered name</dt><dd><code>link_prediction_iforest</code></dd></div>
<div><dt>Scores</dt><dd>Edges</dd></div>
<div><dt>Statistic</dt><dd><code>link_prediction_iforest_score</code>, higher is stronger</dd></div>
<div><dt>Directed graphs</dt><dd>Supported</dd></div>
<div><dt>Weights</dt><dd>Optional, positive</dd></div>
<div><dt>Suggested filter</dt><dd>10% fraction</dd></div>
</dl>

## How it works

The chosen [Link Prediction](link_prediction.md) similarities are computed for
every edge and used as features. scikit-learn's Isolation Forest is fitted to
those feature vectors, and the score is the negated `score_samples` value, so
higher scores mark more anomalous edges. The Netbone filter, not the model's
`contamination`, decides how many edges to keep. Inspect the warnings if the
features are identical across edges.

!!! note "Needs scikit-learn"
    Install the [ml extra](../start/install.md#optional-tools) to use this
    method.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `similarities` | required | One similarity name or a list of them, from [Link Prediction](link_prediction.md). |
| `epsilon` | `1.0` | Weight of three-step paths in `"local_path"`. |
| `weight` | `"auto"` | Edge attribute to read. `"auto"` uses `weight` when every edge has it and runs unweighted otherwise; `None` always runs unweighted. See [how weights are chosen](../reference/methods.md#how-weights-are-chosen). |
| `weight_alpha` | `1.0` | Exponent applied to each weight before scoring. |
| `distance_transform` | `"inverse"` | `"inverse"` reads larger weights as stronger, closer ties and uses `1 / weight` as path length. `"identity"` reads the weight as a length. |
| `n_estimators` | `100` | Number of isolation trees. |
| `max_samples` | `"auto"` | Edges drawn to fit each tree, as in scikit-learn. |
| `max_features` | `1.0` | Features drawn for each tree, as in scikit-learn. |
| `bootstrap` | `False` | Draw edges with replacement. |
| `random_state` | `0` | Seed that makes the scores reproducible. |

## Output columns

| Column | Meaning |
| --- | --- |
| `link_prediction_iforest_<similarity>_similarity` | One column per chosen similarity. |
| `link_prediction_iforest_score` | The anomaly score. |

Every row also has `edge_id`, `source`, and `target`, plus Netbone's internal
`source_id` and `target_id`.

## Cost

The cost of the chosen similarities, plus fitting the forest, which grows with
`n_estimators` and the number of edges.

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
pipeline = nb.pipeline().score(
    "link_prediction_iforest",
    similarities=["preferential_attachment", "shortest_path"],
    random_state=0,
)
backbone = pipeline.filter("fraction", fraction=0.5).run(graph)
print(backbone.summary())
```

## References

The first paper defines the method. The second defines the Isolation Forest
model it applies.

<div class="method-references" markdown="1">

- Yassin, A., Cherifi, H., Seba, H., & Togni, O. (2025). Integrating link prediction and isolation forest for backbone extraction. In Modelling and Mining Networks (WAW 2025), Lecture Notes in Computer Science 15699, 189–204. Springer. [doi:10.1007/978-3-031-92898-7_13](https://doi.org/10.1007/978-3-031-92898-7_13)
- Liu, F. T., Ting, K. M., & Zhou, Z.-H. (2008). Isolation forest. In 2008 Eighth IEEE International Conference on Data Mining, 413–422. IEEE. [doi:10.1109/ICDM.2008.17](https://doi.org/10.1109/ICDM.2008.17)

<details class="bibtex" markdown="1">
<summary>BibTeX</summary>

```bibtex
@inproceedings{yassin2025integrating,
  author = {Yassin, A. and Cherifi, H. and Seba, H. and Togni, O.},
  title = {Integrating link prediction and isolation forest for backbone extraction},
  booktitle = {Modelling and Mining Networks (WAW 2025)},
  series = {Lecture Notes in Computer Science},
  volume = {15699},
  year = {2025},
  publisher = {Springer},
  pages = {189--204},
  doi = {10.1007/978-3-031-92898-7_13}
}

@inproceedings{liu2008isolation,
  author = {Liu, F. T. and Ting, K. M. and Zhou, Z.-H.},
  title = {Isolation forest},
  booktitle = {2008 Eighth IEEE International Conference on Data Mining},
  year = {2008},
  publisher = {IEEE},
  pages = {413--422},
  doi = {10.1109/ICDM.2008.17}
}
```

</details>

</div>
