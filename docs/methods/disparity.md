# Disparity

`disparity` implements the weighted disparity backbone scoring method. It
computes edge-level p-values from local incident-weight distributions for
undirected networks and separate outgoing/incoming distributions for directed
networks.

## Summary

- **Name:** `disparity`
- **Target:** edge
- **Output type:** `pvalue`
- **Primary statistic:** `disparity_pvalue`
- **Preferred direction:** `lower`
- **Supported graphs:** simple directed or undirected NetworkX graphs
- **Weighted input:** required
- **Positive weights:** required
- **Default filter:** `significance`
- **Default p-value aggregation:** `min`
- **Default leaf policy:** `ignore`
- **Multigraph support:** no
- **Directed graph support:** yes

## Definition

For each endpoint `i` of edge `(i, j)`, when `k_i > 1`, the method computes:

```text
p_ij = w_ij / s_i
alpha_ij = (1 - p_ij) ** (k_i - 1)
```

where `w_ij` is the edge weight, `s_i` is node `i`'s strength, and `k_i` is
node `i`'s degree.

For undirected graphs, Netbone stores both endpoint p-values and combines them
into the method-specific primary statistic:

```text
disparity_pvalue
```

For a directed arc `i -> j`, the two local tests use distinct distributions:

```text
p_source = w_ij / s_out_i
alpha_source = (1 - p_source) ** (k_out_i - 1)

p_target = w_ij / s_in_j
alpha_target = (1 - p_target) ** (k_in_j - 1)
```

The source statistic therefore asks whether the arc is unusually large among
the source node's outgoing weights. The target statistic asks whether it is
unusually large among the target node's incoming weights. This follows the
paper's directed treatment of incoming and outgoing distributions separately.
The configured `pvalue_aggregation` combines these two directional endpoint
p-values.

The `pvalue_aggregation` parameter controls how endpoint p-values are combined:

- `min`: keep an edge if either endpoint is significant under a significance
  threshold;
- `max`: keep an edge only when both endpoints are significant under a
  significance threshold;
- `average`: use the mean endpoint p-value.

The `leaf_policy` parameter controls degree-one endpoints. For directed arcs,
this means source out-degree and target in-degree:

- `ignore`: ignore degree-one endpoint p-values during aggregation when the
  other endpoint has degree greater than 1. If both endpoints are leaves, the
  aggregate p-value is `1.0`.
- `zero`: assign degree-one endpoint p-values as `0.0`.

## Parameters

- `weight`: edge attribute name containing finite positive weights. Defaults to
  `"weight"` when omitted.
- `pvalue_aggregation`: `min`, `max`, or `average`. Defaults to `min`.
- `leaf_policy`: `ignore` or `zero`. Defaults to `ignore`.

## Output

`disparity` returns one row per edge:

- `edge_id`
- `source_id`
- `target_id`
- `source`
- `target`
- `disparity_weight`
- `disparity_source_fraction`
- `disparity_target_fraction`
- `disparity_source_pvalue`
- `disparity_target_pvalue`
- `disparity_pvalue`

## Validation

The method raises `ValidationError` when a configured weight attribute is
missing, non-numeric, boolean, infinite, NaN, zero, or negative.

## Interpretation

Lower `disparity_pvalue` values indicate edges that are unexpectedly large
relative to the configured endpoint aggregation rule. The default filter is
`significance`, which selects edges whose primary p-values are below a
configured alpha level.

## Reference

Serrano, Boguna, and Vespignani, "Extracting the multiscale backbone of complex
weighted networks," *PNAS* 106(16), 2009.
[doi:10.1073/pnas.0808904106](https://doi.org/10.1073/pnas.0808904106)
