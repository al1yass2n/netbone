# Marginal Likelihood

`marginal_likelihood` computes significance p-values for integer-weighted
edges under a configuration-model-inspired marginal likelihood filter.

## Summary

- **Name:** `marginal_likelihood`
- **Target:** edge
- **Output type:** `pvalue`
- **Primary statistic:** `marginal_likelihood_pvalue`
- **Preferred direction:** `lower`
- **Weighted input:** required
- **Positive integer weights:** required
- **Default filter:** `significance`

## Definition

For each undirected edge `(i, j)`, Netbone computes the binomial probability:

```text
p_ij = s_i * s_j / (2 * W^2)
```

where `s_i` and `s_j` are node strengths and `W` is total edge weight. The
reported p-value is the inclusive upper-tail probability `P[X >= w_ij]`.

The current implementation uses a deterministic standard-library binomial-tail
helper. A future review should evaluate an optional SciPy-backed survival
function implementation for large-count numerical accuracy and performance.

## Output

- `marginal_likelihood_weight`
- `marginal_likelihood_source_strength`
- `marginal_likelihood_target_strength`
- `marginal_likelihood_probability`
- `marginal_likelihood_pvalue`

## Reference

Dianati, N. (2016). Unwinding the hairball graph: Pruning algorithms for
weighted complex networks. DOI: `10.1103/PhysRevE.93.012304`.
