# Threshold Filter

`threshold` converts method output values into a selection by comparing one
named value column against an explicit threshold.

## Summary

- **Name:** `threshold`
- **Input:** `MethodResult`
- **Output:** `Selection`
- **Supported targets:** edge selections in the current vertical slice
- **Default isolate behavior:** keep isolates

## Parameters

- `statistic`: optional value column to compare, such as `score`. When omitted,
  the method's `primary_statistic` is used.
- `value`: finite numeric threshold.
- `operator`: comparison operator.
- `drop_isolates`: whether isolated nodes should be removed after edge
  filtering. Defaults to `False`.

Supported operators:

- `greater`
- `greater_equal`
- `less`
- `less_equal`
- `equal`
- `not_equal`

## Behavior

For each row in the method output table, `threshold` evaluates:

```text
row[statistic] operator value
```

Rows where the expression is true become selected ids. Rows where it is false
become rejected ids.

Most users do not need to pass `statistic`. The method result already declares
its primary statistic, and `threshold` uses that by default. Passing
`statistic=...` is an advanced override for method results with multiple
comparable columns.

For edge selections, `Pipeline.run()` extracts a new NetworkX graph from the
selected edge ids. Original node ids are used in the returned graph.

## Isolates

When `drop_isolates=False`, all original nodes are kept, even if they have no
selected incident edges.

When `drop_isolates=True`, nodes without retained incident edges are omitted
from the backbone graph.

## Validation

The filter raises:

- `ConfigurationError` for unknown operators or missing statistic columns.
- `ValidationError` for non-numeric, missing, infinite, or NaN threshold/value
  data.

## Interpretation

The threshold filter does not infer which direction is scientifically correct.
Users must choose the statistic and operator explicitly. This is intentional:
some methods prefer higher values, while others may prefer lower values such as
p-values.
