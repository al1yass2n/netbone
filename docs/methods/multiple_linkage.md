# Multiple Linkage Analysis

`multiple_linkage` marks a locally chosen prefix of each node's strongest
incident edges. It generalizes primary linkage by allowing more than one edge
from a node when the local weight distribution supports it.

## Summary

- **Name:** `multiple_linkage`
- **Target:** edge
- **Output type:** `score`
- **Primary statistic:** `multiple_linkage_selected`
- **Preferred direction:** `higher`
- **Weighted input:** required
- **Non-negative weights:** required
- **Default filter:** `threshold`, `value=1.0`, `operator="equal"`
- **Tie policy:** stable internal `edge_id`

## Definition

For each node:

1. Exclude zero-weight incident edges from the local flow distribution.
2. Normalize remaining positive incident edge weights into percentages.
3. Sort incident edges by descending normalized weight, then stable `edge_id`.
4. Compare the observed distribution to every ideal top-`k` equal-share
   distribution using squared correlation.
5. Select the prefix with the globally largest coefficient of determination.

An edge is selected when at least one endpoint selects it. Zero-weight edges are
reported in the statistics table for graph alignment, but they are not included
in local MLAM distributions and cannot be selected.

## Output

- `multiple_linkage_weight`
- `multiple_linkage_endpoint_count`
- `multiple_linkage_selected`

## Reference

Nocaj, A., Ortmann, M., and Brandes, U. (2009). DOI:
`10.1111/j.1467-9663.2009.00547.x`.
