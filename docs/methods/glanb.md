# GLANB

`glanb` implements Globally and Locally Adaptive Network Backbone scoring.

## Summary

- **Name:** `glanb`
- **Target:** edge
- **Output type:** `pvalue`
- **Primary statistic:** `glanb_significance`
- **Preferred direction:** `lower`
- **Weighted input:** optional
- **Positive weights:** required when `weight` is provided
- **Required parameter:** nonnegative `c`
- **Default filter:** `significance`

## Definition

When `weight` is provided, weights are converted to shortest-path distances as
`1 / weight`. When `weight=None`, GLANB uses unweighted shortest paths.

For endpoint `i` and adjacent edge `(i, j)`, Netbone first computes the
involvement:

```text
I_ij = (1 / (N - 1)) * sum over n != i of sigma_in(ij) / sigma_in
```

where `sigma_in` is the number of shortest paths from `i` to `n`, and
`sigma_in(ij)` is how many of those shortest paths contain edge `(i, j)`.
The parameter `c` does not affect shortest paths or involvement. It is applied
afterward in the endpoint significance formula:

```text
S_ij = (1 - I_ij) ** ((k_i - 1) ** c)
```

where `k_i` is the source degree and `c` controls local adaptivity. Degree-one
endpoints do not define a local GLANB significance contribution; the undirected
edge statistic uses the lower available endpoint significance, or `1.0` when
neither endpoint contributes.

## Output

- `glanb_weight`
- `glanb_distance`
- `glanb_source_involvement`
- `glanb_target_involvement`
- `glanb_source_significance`
- `glanb_target_significance`
- `glanb_significance`

## Reference

Zhang, X. et al. (2014). Globally and Locally Adaptive Network Backbone. PLoS
ONE 9(6): e100428. DOI: `10.1371/journal.pone.0100428`.
