# Link Prediction Isolation Forest

`link_prediction_iforest` scores observed edges by how unusual their selected
link-prediction similarities are. It supports one similarity or a combination
of similarities and uses scikit-learn's Isolation Forest as an optional
second-stage scorer.

## Contract

- **Name:** `link_prediction_iforest`
- **Target:** edge
- **Output type:** score
- **Primary statistic:** `link_prediction_iforest_score`
- **Preferred direction:** higher
- **Default filter:** retained fraction `0.1`
- **Directed input:** supported with the base Link Prediction method's ordered
  semantics
- **Optional dependency:** `netbone[ml]`

The method negates scikit-learn's `score_samples` output. Larger Netbone scores
therefore mean more anomalous feature vectors. An edge may be anomalous because
its similarities are unusually low, unusually high, or unusual in combination.

The method does not use Isolation Forest's contamination classification.
Backbone extraction remains separate and uses Netbone's `fraction` or
`threshold` filters.

## Similarity Features

Pass one similarity name as a string:

```python
scores = nb.score(
    network,
    method="link_prediction_iforest",
    similarities="preferential_attachment",
)
```

Pass an ordered list to fit a multivariate Isolation Forest:

```python
scores = nb.score(
    network,
    method="link_prediction_iforest",
    similarities=[
        "preferential_attachment",
        "shortest_path",
        "local_path",
    ],
    epsilon=0.25,
    random_state=0,
)
```

Supported similarities are `preferential_attachment`, `shortest_path`, and
`local_path`. Their definitions and weighted behavior are the same as in
[`link_prediction`](link_prediction.md). `epsilon` applies only when
`local_path` is selected.

For directed input, every feature uses the same directed definition as the
base scorer: source-out/target-in Preferential Attachment and forward
source-to-target Shortest Path and Local Path. Reciprocal arcs are separate
observations for Isolation Forest and may receive different anomaly scores.

## Filtering

Keep a fraction of the most anomalous edges:

```python
result = (
    nb.pipeline()
    .score(
        "link_prediction_iforest",
        similarities=["preferential_attachment", "shortest_path"],
    )
    .filter("fraction", fraction=0.1)
    .run(network)
)
```

Or apply an explicit anomaly-score threshold:

```python
result = (
    nb.pipeline()
    .score(
        "link_prediction_iforest",
        similarities="local_path",
    )
    .filter("threshold", value=0.6, operator="greater_equal")
    .run(network)
)
```

Inspect observed scores before choosing a threshold; their scale depends on the
fitted network and selected features.

## Isolation Forest Parameters

- `n_estimators=100`: number of isolation trees;
- `max_samples="auto"`: samples used to fit each tree;
- `max_features=1.0`: features considered by each tree;
- `bootstrap=False`: whether tree samples use replacement;
- `random_state=0`: deterministic random seed.

`contamination` is intentionally not exposed because it would combine scoring
and selection. Use Netbone filters to control the retained backbone.

## Statistics

The statistics table contains edge identity columns, one input column per
selected similarity, and the primary anomaly score. For example:

- `link_prediction_iforest_preferential_attachment_similarity`
- `link_prediction_iforest_shortest_path_similarity`
- `link_prediction_iforest_local_path_similarity`
- `link_prediction_iforest_score`

Identical feature vectors produce tied anomaly scores. Fraction-filter tie
behavior is controlled by the selected `tie_policy`.

## References

- Yassin, Cherifi, Seba, and Togni, *Integrating Link Prediction and Isolation
  Forest for Backbone Extraction*, WAW 2025, LNCS 15699, pp. 189-204,
  DOI [`10.1007/978-3-031-92898-7_13`](https://doi.org/10.1007/978-3-031-92898-7_13).
- Liu, Ting, and Zhou, *Isolation Forest*, IEEE ICDM (2008),
  DOI `10.1109/ICDM.2008.17`.
