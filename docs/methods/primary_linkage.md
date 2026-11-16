# Primary Linkage Analysis

`primary_linkage` marks the strongest incident edge of each node and keeps the
union of those choices.

## Summary

- **Name:** `primary_linkage`
- **Target:** edge
- **Output type:** `score`
- **Primary statistic:** `primary_linkage_selected`
- **Preferred direction:** `higher`
- **Weighted input:** required
- **Default filter:** `threshold`, `value=1.0`, `operator="equal"`
- **Tie policy:** stable internal `edge_id`

## Definition

For every node, incident edges are sorted by descending weight. If multiple
edges tie for the maximum, the stable internal `edge_id` breaks the tie. An edge
is selected when at least one endpoint chooses it.

## Output

- `primary_linkage_weight`
- `primary_linkage_endpoint_count`
- `primary_linkage_selected`

## Reference

Nocaj, A., Ortmann, M., and Brandes, U. (2009). Untangling the hairballs of
multi-centered, small-world online social media networks. DOI:
`10.1111/j.1467-9663.2009.00547.x`.
