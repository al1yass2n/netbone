# Node Strength

`node_strength` scores nodes by weighted degree, also called strength.

## Summary

- **Name:** `node_strength`
- **Target:** node
- **Output type:** `score`
- **Primary statistic:** `node_strength`
- **Preferred direction:** `higher`
- **Supported graphs:** simple undirected NetworkX graphs
- **Weighted input:** required
- **Default weight attribute:** `weight`
- **Default filter:** `fraction`, `fraction=0.1`
- **Multigraph support:** no
- **Directed graph support:** no

## Definition

For each node `i`, Netbone computes:

```text
node_strength(i) = sum of weights on edges incident to i
```

## Parameters

- `weight`: edge attribute name containing finite numeric weights. Defaults to
  `"weight"`.

## Output

`node_strength` returns one row per node:

- `node_id`
- `node`
- `node_strength`

## Validation

The method raises `ValidationError` when a configured weight attribute is
missing, non-numeric, boolean, infinite, or NaN.

## Interpretation

Higher values indicate nodes with greater total incident edge weight. Filtering
a node method returns the node-induced subgraph on selected nodes.
