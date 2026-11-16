# LANS

`lans` implements Locally Adaptive Network Sparsification from Foti, Hughes,
and Rockmore. It computes edge-level empirical p-values from each node's local
distribution of incident fractional edge weights.

## Summary

- **Name:** `lans`
- **Target:** edge
- **Output type:** `pvalue`
- **Primary statistic:** `lans_pvalue`
- **Preferred direction:** `lower`
- **Supported graphs:** simple undirected and directed NetworkX graphs
- **Weighted input:** required
- **Positive weights:** required
- **Default filter:** `significance`
- **Default p-value aggregation:** `min`
- **Default leaf policy:** `zero`
- **Multigraph support:** no
- **Directed graph support:** yes, source-outgoing local distributions

## Definition

For each endpoint `i` of edge `(i, j)`, the method computes the fractional
weight:

```text
p_ij = w_ij / s_i
```

where `w_ij` is the edge weight and `s_i` is node `i`'s strength. It then
compares that value to the empirical distribution of fractional weights around
node `i`:

```text
F_i(p_ij) = fraction of incident edges with fractional weight <= p_ij
lans_endpoint_pvalue = 1 - F_i(p_ij)
```

Lower endpoint p-values indicate edges with unusually large fractional weight
for that endpoint. Ties are handled by the empirical CDF, so tied largest local
fractions receive endpoint p-value `0.0`.

For undirected graphs, Netbone stores both endpoint p-values and combines them
into the method-specific primary statistic:

```text
lans_pvalue
```

The `pvalue_aggregation` parameter controls how endpoint p-values are combined:

- `min`: keep an edge if either endpoint is significant under a significance
  threshold;
- `max`: keep an edge only when both endpoints are significant under a
  significance threshold;
- `average`: use the mean endpoint p-value.

The `leaf_policy` parameter controls degree-one endpoints:

- `zero`: assign degree-one endpoint p-values as `0.0`.
- `ignore`: ignore degree-one endpoint p-values during aggregation when the
  other endpoint has degree greater than 1. If both endpoints are leaves, the
  aggregate p-value is `1.0`.

For a directed arc `i -> j`, Netbone computes `s_i` from node `i`'s outgoing
weights and compares the arc only with the other outgoing arcs from `i`.
`lans_source_fraction` and `lans_source_pvalue` are populated,
`lans_target_fraction` and `lans_target_pvalue` are missing, and the source
p-value becomes `lans_pvalue`. The leaf policy therefore uses source
out-degree. `pvalue_aggregation` has no effect for directed graphs because
there is only one evaluated endpoint; a non-default value produces a warning.

## Parameters

- `weight`: edge attribute name containing finite positive weights. Defaults to
  `"weight"` when omitted.
- `pvalue_aggregation`: `min`, `max`, or `average`. Defaults to `min` and
  applies only to undirected graphs.
- `leaf_policy`: `ignore` or `zero`. Defaults to `zero`.

## Output

`lans` returns one row per edge:

- `edge_id`
- `source_id`
- `target_id`
- `source`
- `target`
- `lans_weight`
- `lans_source_fraction`
- `lans_target_fraction`
- `lans_source_pvalue`
- `lans_target_pvalue`
- `lans_pvalue`

## Validation

The method raises `ValidationError` when a configured weight attribute is
missing, non-numeric, boolean, infinite, NaN, zero, or negative.

## Interpretation

Lower `lans_pvalue` values indicate edges that are locally large according to a
nonparametric empirical distribution around at least one endpoint under the
default aggregation rule. The default filter is `significance`, which selects
edges whose primary p-values are below a configured alpha level.

## Reference

Foti, N. J., Hughes, J. M., and Rockmore, D. N. (2011). Nonparametric
Sparsification of Complex Multiscale Networks. PLoS ONE 6(2): e16431.
DOI: `10.1371/journal.pone.0016431`.
