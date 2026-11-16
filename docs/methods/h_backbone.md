# H-Backbone

`h_backbone` marks edges whose weight or bridge score passes an h-index style
threshold.

## Summary

- **Name:** `h_backbone`
- **Target:** edge
- **Output type:** `score`
- **Primary statistic:** `h_backbone_selected`
- **Preferred direction:** `higher`
- **Weighted input:** required
- **Positive weights:** required
- **Default filter:** `threshold`, `value=1.0`, `operator="equal"`
- **Default distance transform:** `inverse`

## Definition

Netbone computes:

- an h-strength threshold from edge weights;
- edge betweenness centrality divided by node count as `h_backbone_bridge`;
- an h-bridge threshold from bridge values.

An edge is selected when it passes either positive threshold. The
`distance_transform` parameter controls how weights are interpreted for shortest
paths: `inverse` treats weights as strengths, while `identity` treats them as
distances.

## Output

- `h_backbone_weight`
- `h_backbone_bridge`
- `h_backbone_h_strength`
- `h_backbone_h_bridge`
- `h_backbone_selected`

## Reference

Zhang, R. J., Stanley, H. E., and Ye, F. Y. (2018). DOI:
`10.1038/s41598-018-32430-1`.
