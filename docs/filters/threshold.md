# Threshold

Use `threshold` when the score has a meaningful cutoff. `value` is a finite
number. `operator` is required and determines how equality is handled.

| Operator | Keep a row when its statistic |
| --- | --- |
| `greater` | Is greater than the cutoff |
| `greater_equal` | Is greater than or equal to the cutoff |
| `less` | Is less than the cutoff |
| `less_equal` | Is less than or equal to the cutoff |
| `equal` | Equals the cutoff |
| `not_equal` | Differs from the cutoff |

Use `statistic="column_name"` to select a numeric column other than the primary
statistic. Missing, non-numeric, or non-finite values cause a validation error.
Use `drop_isolates=True` to remove isolated nodes after edge filtering.

```python
result = nb.filter_scores(graph, scores, "threshold", value=5, operator="greater_equal")
```

See [how to reuse an existing score table](../python/select.md#reuse-an-existing-score-table)
for a complete example and [significance](significance.md) for p-value
correction.
