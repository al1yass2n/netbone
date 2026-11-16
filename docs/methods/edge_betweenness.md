# Edge Betweenness

`edge_betweenness` scores edges by shortest-path betweenness centrality. It is a
structural ranking method rather than a statistical p-value method.

## Summary

- **Name:** `edge_betweenness`
- **Target:** edge
- **Output type:** `score`
- **Primary statistic:** `edge_betweenness`
- **Preferred direction:** `higher`
- **Supported graphs:** simple undirected NetworkX graphs
- **Weighted input:** optional
- **Default weight attribute:** `None`
- **Default distance transform:** `inverse` when a weight is provided
- **Default filter:** `fraction`, `fraction=0.1`
- **Multigraph support:** no
- **Directed graph support:** no

## Definition

Edge betweenness centrality measures how often an edge lies on shortest paths
between node pairs:

```text
edge_betweenness(e) = sum over node pairs of
    shortest paths between the pair that use e
    /
    all shortest paths between the pair
```

Netbone delegates the centrality computation to NetworkX and then normalizes
the result into the standard `MethodResult` table.

## Parameters

- `weight`: optional edge attribute name. Defaults to `None`, which computes
  unweighted shortest-path betweenness.
- `distance_transform`: `inverse` or `identity`. The default `inverse` treats
  configured edge weights as strengths and uses `1 / weight` as distance. Use
  `identity` when edge weights already represent distances.
- `normalized`: boolean. Defaults to `True`.

When `weight=None`, all edges are treated as unit distance and
`distance_transform` does not change the result.

## Output

`edge_betweenness` returns one row per edge:

- `edge_id`
- `source_id`
- `target_id`
- `source`
- `target`
- `edge_betweenness_weight`
- `edge_betweenness_distance`
- `edge_betweenness`

## Validation

The method raises `ValidationError` when a configured weight attribute is
missing, non-numeric, boolean, infinite, or NaN. Weighted shortest-path
distances must be positive.

## Interpretation

Higher values indicate edges used by more shortest paths. This often highlights
bridges between dense regions, but it is not a statistical significance test
and can be expensive on large graphs. The default filter keeps the top retained
fraction as a practical starting point; users should inspect the score
distribution and compare against other methods.

## References

- NetworkX `edge_betweenness_centrality` documentation:
  https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.centrality.edge_betweenness_centrality.html
- Brandes, U. (2001). A Faster Algorithm for Betweenness Centrality.
  DOI: `10.1080/0022250X.2001.9990249`.
- Girvan, M. and Newman, M. E. J. (2002). Community structure in social and
  biological networks. PNAS 99(12): 7821-7826.
  DOI: `10.1073/pnas.122653799`.
