# Link Prediction Isolation Forest

Registered name `link_prediction_iforest`

Fits scikit-learn's Isolation Forest to one or more edge similarity features.
Higher scores identify edges that are more unusual in the chosen feature space.
Install the [ml extra](../start/install.md#optional-tools). Retention is set by
the Netbone filter.

Pass `similarities` as one name or a sequence of the
[Link Prediction](link_prediction.md) similarity names. The method shares the
`weight`, `weight_alpha`, `distance_transform`, and `epsilon` options. Model
controls default to `n_estimators=100`, `max_samples="auto"`,
`max_features=1.0`, `bootstrap=False`, and `random_state=0`. Inspect warnings
if the selected features give identical values across edges.

| Target | Primary statistic | Preferred direction | Directed input | Weight requirement |
| --- | --- | --- | --- | --- |
| edge | `link_prediction_iforest_score` | higher | Supported | Positive when weighted |

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
candidate = nb.pipeline().score(
    "link_prediction_iforest",
    similarities=["preferential_attachment", "shortest_path"],
    random_state=0,
)
result = candidate.filter("fraction", fraction=0.5).run(graph)
print(result.summary())
```

[Algorithm reference](https://doi.org/10.1007/978-3-031-92898-7_13)
