# Planar Maximally Filtered Graph

`planar_maximally_filtered_graph` marks edges selected by the Planar Maximally
Filtered Graph procedure.

## Summary

- **Name:** `planar_maximally_filtered_graph`
- **Target:** edge
- **Output type:** `score`
- **Primary statistic:** `pmfg_selected`
- **Preferred direction:** `higher`
- **Weighted input:** optional
- **Default filter:** `threshold`, `value=1.0`, `operator="equal"`
- **Tie policy:** stable internal `edge_id`

## Definition

Edges are considered by descending weight. Each edge is kept if adding it to
the growing backbone preserves planarity. The process stops when no more input
edges remain or when the planar graph reaches `3 * (n - 2)` edges for `n >= 3`.

## Output

- `pmfg_weight`
- `pmfg_order`
- `pmfg_selected`

## Reference

Tumminello, M., Aste, T., Di Matteo, T., and Mantegna, R. N. (2005). A tool for
filtering information in complex systems. DOI: `10.1073/pnas.0500298102`.
