# Link Salience

`link_salience` implements the link-salience scoring method from Grady,
Thiemann, and Brockmann, "Robust classification of salient links in complex
networks", Nature Communications 3, 864 (2012).

## Summary

- **Name:** `link_salience`
- **Target:** edge
- **Output type:** `score`
- **Primary statistic:** `link_salience`
- **Preferred direction:** `higher`
- **Supported graphs:** simple undirected and directed NetworkX graphs
- **Weighted input:** optional
- **Default weight attribute:** `weight`
- **Default distance transform:** `inverse`
- **Default filter:** `threshold`, `value=0.5`, `operator="greater_equal"`
- **Multigraph support:** no
- **Directed graph support:** yes, outgoing shortest paths

## Definition

For each root node, Netbone computes shortest-path distances to every reachable
node. An edge receives one count for that root if it lies on at least one
shortest path from the root. The link salience of edge `e` is:

```text
link_salience(e) = count(e) / number_of_nodes
```

The implementation includes all equal-length shortest-path ties for a root,
so tied shortest-path alternatives can all contribute to salience.

This is root participation, not a count of every source-target shortest path.
Each root contributes at most one count to an edge when that edge appears
anywhere in the root's shortest-path tree or tied shortest-path DAG. Edge
betweenness uses the different all-pairs path-participation definition.

For directed graphs, Netbone follows arc direction and computes outgoing
shortest paths from every root. An arc `u -> v` contributes for a root only
when `distance(root, u) + distance(u, v) = distance(root, v)`. Salience is
still divided by the total number of nodes, so a root that cannot reach an arc
contributes zero. A graph that is not strongly connected therefore produces an
interpretation warning. This is Netbone's directed extension of the registered
method semantics: the same at-most-once participation count is used for each
root, but only outgoing paths and correctly oriented arcs qualify. The graph is
not silently symmetrized.

## Parameters

- `weight`: edge attribute name. Defaults to `"weight"`. Pass `None` to compute
  unweighted unit-distance salience.
- `distance_transform`: `inverse` or `identity`. The default `inverse` treats
  edge weights as strengths and uses `1 / weight` as the shortest-path
  distance. Use `identity` when edge weights already represent distances.

## Output

`link_salience` returns one row per edge:

- `edge_id`
- `source_id`
- `target_id`
- `source`
- `target`
- `link_salience_weight`
- `link_salience_distance`
- `link_salience_count`
- `link_salience`

## Validation

The method raises `ValidationError` when a configured weight attribute is
missing, non-numeric, boolean, infinite, or NaN. With
`distance_transform="inverse"`, weights must be positive. With
`distance_transform="identity"`, weights must be non-negative.

## Interpretation

Higher `link_salience` values indicate edges that occur in shortest-path trees
from many roots. The default threshold filter at `0.5` extracts a high-salience
skeleton, but users should inspect the salience distribution before treating
that threshold as definitive.

Reference: https://www.nature.com/articles/ncomms1847
