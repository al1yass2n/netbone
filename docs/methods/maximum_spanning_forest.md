# Maximum Spanning Forest

`maximum_spanning_forest` marks the edges selected by a deterministic maximum
spanning forest. It is a connectivity-preserving baseline rather than a
statistical p-value method.

## Summary

- **Name:** `maximum_spanning_forest`
- **Target:** edge
- **Output type:** `score`
- **Primary statistic:** `maximum_spanning_forest_selected`
- **Preferred direction:** `higher`
- **Supported graphs:** simple undirected NetworkX graphs
- **Weighted input:** optional
- **Default weight attribute:** `weight`
- **Default tie policy:** stable internal `edge_id` order
- **Default filter:** `threshold`, `value=1.0`, `operator="equal"`
- **Multigraph support:** no
- **Directed graph support:** no

## Definition

The method applies Kruskal-style maximum spanning forest selection:

```text
1. Sort edges by descending weight.
2. Break equal-weight ties by stable internal edge_id.
3. Keep an edge if it connects two previously disconnected components.
4. Reject an edge if it would create a cycle.
```

For disconnected input graphs, the result is a maximum spanning tree inside
each connected component.

## Parameters

- `weight`: edge attribute name containing finite numeric weights. Defaults to
  `"weight"`. Pass `None` to treat every edge as weight `1.0`.

## Output

`maximum_spanning_forest` returns one row per edge:

- `edge_id`
- `source_id`
- `target_id`
- `source`
- `target`
- `maximum_spanning_forest_weight`
- `maximum_spanning_forest_order`
- `maximum_spanning_forest_selected`

`maximum_spanning_forest_selected` is `1.0` for selected forest edges and
`0.0` for rejected edges. `maximum_spanning_forest_order` records the order in
which selected edges entered the forest and is missing for rejected edges.

## Validation

The method raises `ValidationError` when a configured weight attribute is
missing, non-numeric, boolean, infinite, or NaN. Negative weights are allowed
because maximum spanning forests are still well-defined for finite signed
weights.

## Interpretation

The extracted forest preserves component-level connectivity with as few edges
as possible. This can be useful as a deterministic baseline, but it deliberately
removes all cycle-forming edges, including edges that may be meaningful under
local or shortest-path-based methods.

If tied weights affect which edges are kept, Netbone emits a warning and breaks
ties by stable internal `edge_id` order.
