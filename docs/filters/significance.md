# Significance Filter

`significance` selects rows from p-value method results using an alpha
threshold and an optional multiple-testing correction.

## Summary

- **Name:** `significance`
- **Input:** `MethodResult` with `output_type="pvalue"`
- **Output:** `Selection`
- **Default statistic:** method `primary_statistic`
- **Default alpha:** `0.05`
- **Default correction:** `none`
- **Default isolate behavior:** keep isolates

## Parameters

- `alpha`: significance level from `0` to `1`.
- `statistic`: optional p-value column. Defaults to the method result's primary
  statistic.
- `correction`: `none`, `bonferroni`, `holm`, or `fdr_bh`.
- `drop_isolates`: whether isolated nodes should be removed after edge
  filtering. Defaults to `False`.

## Behavior

The filter adjusts p-values according to the configured correction and selects
rows where the adjusted value is strictly less than `alpha`.

When `correction="none"`, the selection includes a warning that no
multiple-testing correction was used.

## Validation

The filter raises:

- `ConfigurationError` for non-p-value method results, unknown correction
  names, or missing statistic columns.
- `ValidationError` for invalid alpha values or p-values outside `[0, 1]`.
