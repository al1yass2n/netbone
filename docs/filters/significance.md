# Significance

Use `significance` with methods that report `output_type="pvalue"`.
The filter selects rows whose adjusted p-value is strictly less than `alpha`
(default 0.05). Both alpha and each p-value must be in the closed interval from
0 to 1. Use `statistic` to select an alternate valid p-value column.

| `correction` | Adjustment |
| --- | --- |
| `none` (default) | Raw p-values are used and a warning is recorded. |
| `bonferroni` | Bonferroni adjustment for the number of tested rows. |
| `holm` | Holm step-down adjustment for family-wise error. |
| `fdr_bh` | Benjamini–Hochberg false discovery rate adjustment. |

Choose the correction with the method's null model and the set of tests in
mind. The web app offers all four under **Advanced filter options**
as **Correction**. To omit isolated nodes after edge filtering, set `drop_isolates=True`.

```python
pvalues = nb.score(graph, "disparity", weight="weight")
result = nb.filter_scores(graph, pvalues, "significance", alpha=0.05, correction="holm")
```

Use the [sample graph](../reference/methods.md#try-a-method) to try this rule.
