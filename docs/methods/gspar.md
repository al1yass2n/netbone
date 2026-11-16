# GSPAR

`gspar` scores each edge by the Jaccard similarity of its endpoints' open
neighborhoods. The name follows the GSPAR/global-sparsification convention, but
the output column names make the Jaccard statistic explicit.

## Summary

- **Name:** `gspar`
- **Target:** edge
- **Output type:** `score`
- **Primary statistic:** `gspar_jaccard_similarity`
- **Preferred direction:** `higher`
- **Weighted input:** not required
- **Default filter:** `fraction`, `fraction=0.1`

## Definition

For edge `(i, j)`, Netbone computes:

```text
gspar_jaccard_similarity = |N(i) intersection N(j)| / |N(i) union N(j)|
```

where `N(i)` is the open neighborhood containing the neighbors of node `i`.

## Output

The method returns one row per edge with `edge_id`, endpoint identifiers, and
`gspar_jaccard_similarity`.

## Reference

Satuluri, V., Parthasarathy, S., and Ruan, Y. (2011). Local graph sparsification
for scalable clustering. DOI: `10.1145/1989323.1989399`.
