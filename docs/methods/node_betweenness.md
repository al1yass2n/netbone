# Node Betweenness

`node_betweenness` scores nodes by shortest-path betweenness centrality. It is
a structural ranking method rather than a statistical p-value method.

## Summary

- **Name:** `node_betweenness`
- **Target:** node
- **Output type:** `score`
- **Primary statistic:** `node_betweenness`
- **Preferred direction:** `higher`
- **Supported graphs:** simple undirected NetworkX graphs
- **Weighted input:** optional
- **Default weight attribute:** `None`
- **Default distance transform:** `inverse` when a weight is provided
- **Default normalized:** `True`
- **Default endpoints:** `False`
- **Default filter:** `fraction`, `fraction=0.1`
- **Multigraph support:** no
- **Directed graph support:** no

## Definition

Node betweenness centrality measures how often a node lies on shortest paths
between other node pairs:

```text
node_betweenness(v) = sum over node pairs s,t of
    shortest paths from s to t that pass through v
    /
    all shortest paths from s to t
```

Netbone delegates the centrality computation to NetworkX and normalizes the
result into the standard `MethodResult` table.

## Parameters

- `weight`: optional edge attribute name. Defaults to `None`, which computes
  unweighted shortest-path betweenness.
- `distance_transform`: `inverse` or `identity`. The default `inverse` treats
  configured edge weights as strengths and uses `1 / weight` as distance. Use
  `identity` when edge weights already represent distances.
- `normalized`: boolean. Defaults to `True`.
- `endpoints`: boolean. Defaults to `False`.

When `weight=None`, all edges are treated as unit distance and
`distance_transform` does not change the result.

## Output

`node_betweenness` returns one row per node:

- `node_id`
- `node`
- `node_betweenness`

## Validation

The method raises `ValidationError` when a configured weight attribute is
missing, non-numeric, boolean, infinite, or NaN. Weighted shortest-path
distances must be positive.

## Interpretation

Higher values indicate nodes that bridge more shortest paths. Filtering this
method returns the node-induced subgraph on selected nodes. High betweenness can
identify brokers or bridges, but it does not test statistical significance and
can be expensive on large graphs.

## References

- NetworkX `betweenness_centrality` documentation:
  https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.centrality.betweenness_centrality.html
- Brandes, U. (2001). A Faster Algorithm for Betweenness Centrality.
  DOI: `10.1080/0022250X.2001.9990249`.
