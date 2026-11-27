# Fraction

Use `fraction` for a retention budget on score, p-value, or numeric custom
statistics. Give a number from 0 to 1. The requested count is
`ceil(fraction * number_of_rows)`, computed after rounding away floating-point
noise so that `0.07` of 100 rows keeps 7. A fraction of zero keeps zero items and a
fraction of one keeps all items.

The filter defaults to the primary statistic and the method's preferred
direction. Override them with `statistic` and `direction="higher"` or
`direction="lower"`. [Link Prediction](../methods/link_prediction.md)
requires an explicit direction.

## Ties at the cutoff

| `tie_policy` | Behavior |
| --- | --- |
| `include_all_ties` (default) | Keep every item tied at the cutoff. The realized count can exceed the requested count. |
| `exact_stable` | Break ties by internal ID and keep the requested count. |
| `raise_on_tie` | Raise an error if the cutoff splits a tie. |
| `random_seeded` | Choose the remaining items from the tied group using the required integer `random_seed`. |

In the web app, these rules are under **Advanced filter options** as **Tie
policy**. Choosing **random, seeded** shows a **Random seed** box, and the same
seed always keeps the same tied items.

Inspect the requested and actual counts in `result.selection.parameters`.
Missing, non-numeric, or non-finite values cause a validation error. Use
`drop_isolates=True` if you want an edge-target result without isolates.

```python
result = nb.filter_scores(
    graph, scores, "fraction", fraction=0.5, tie_policy="exact_stable"
)
```

Use `graph` and `scores` from [the score reuse example](../python/select.md#reuse-an-existing-score-table).
