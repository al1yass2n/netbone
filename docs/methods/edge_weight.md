# Edge Weight

`edge_weight` is the first baseline scoring method in Netbone. It is not a
published backbone extraction algorithm. Its purpose is to prove the package
workflow: load a graph, compute edge-level values, inspect them, apply a
filter, and extract a backbone graph.

## Summary

- **Name:** `edge_weight`
- **Target:** edge
- **Output type:** `score`
- **Primary statistic:** `score`
- **Preferred direction:** `higher`
- **Supported graphs:** simple undirected NetworkX graphs
- **Weighted input:** optional
- **Multigraph support:** no
- **Directed graph support:** no

## Definition

For each edge `e`, `edge_weight` returns:

```text
score(e) = edge attribute value
```

When no weight attribute is configured, each edge receives:

```text
score(e) = 1.0
```

## Parameters

- `weight`: optional edge attribute name. If provided, every edge must have a
  finite numeric value for this attribute.

CSV edge-list loading stores any configured input weight column under the
canonical edge attribute `weight`. For example, `from_edgelist(...,
weight="strength")` records edge values as `weight` while preserving
`"strength"` in `network.metadata["edge_weight_original_column"]`.

## Output

`edge_weight` returns a `MethodResult` whose value table has one row per edge:

- `edge_id`: internal integer edge id
- `source_id`: internal integer source node id
- `target_id`: internal integer target node id
- `source`: original source node id
- `target`: original target node id
- `score`: numeric edge score

The primary statistic is `score`, and larger scores are preferred by
convention for this method.

## Validation

The method raises `ValidationError` when a configured weight attribute is
missing, non-numeric, boolean, infinite, or NaN.

## Interpretation

`edge_weight` keeps the semantics of the original edge weights. A high score
means only that the original edge attribute is large. It does not test
statistical significance, correct for node degree, compare against a null
model, or prove that an edge is structurally important.

Use it as a transparent baseline and as a way to validate the score/filter
pipeline before adding published backbone methods.
