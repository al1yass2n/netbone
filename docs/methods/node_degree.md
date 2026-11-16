# Node Degree

`node_degree` scores nodes by unweighted degree.

## Summary

- **Name:** `node_degree`
- **Target:** node
- **Output type:** `score`
- **Primary statistic:** `node_degree`
- **Preferred direction:** `higher`
- **Supported graphs:** simple undirected NetworkX graphs
- **Weighted input:** ignored
- **Default filter:** `fraction`, `fraction=0.1`
- **Multigraph support:** no
- **Directed graph support:** no

## Definition

For each node `i`, Netbone computes:

```text
node_degree(i) = number of incident edges
```

## Parameters

`node_degree` has no method parameters.

## Output

`node_degree` returns one row per node:

- `node_id`
- `node`
- `node_degree`

## Interpretation

Higher values indicate nodes with more incident edges. Filtering a node method
returns the node-induced subgraph on selected nodes, so edges between selected
nodes are retained and edges touching rejected nodes are removed.
