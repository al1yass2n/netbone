# Doubly Stochastic

`doubly_stochastic` computes edge scores from a Sinkhorn-normalized weighted
adjacency matrix.

## Summary

- **Name:** `doubly_stochastic`
- **Target:** edge
- **Output type:** `score`
- **Primary statistic:** `doubly_stochastic_score`
- **Preferred direction:** `higher`
- **Weighted input:** required
- **Positive weights:** required
- **Default filter:** threshold on `doubly_stochastic_connected_selected`

## Definition

Netbone builds a symmetric weighted adjacency matrix, adds a small positive
`epsilon`, and alternates row and column normalization until row and column sums
are within `tolerance` or `max_iterations` is reached. For disconnected graphs,
the normalization is applied independently to each connected component. Each
original edge gets the average normalized matrix value in both directions.

By default, `epsilon` is scale-relative:

```python
effective_epsilon = epsilon * mean_positive_component_weight
```

This keeps the score stable when all weights are multiplied by a constant. Pass
`epsilon_mode="absolute"` to use `epsilon` directly.

For default extraction, Netbone also records a deterministic connected-prefix
selection: edges are sorted from highest to lowest `doubly_stochastic_score`,
with stable `edge_id` tie-breaking, and added one after another until all nodes
inside each connected component are connected. Isolated nodes do not require
selected edges. Users can still apply ordinary `threshold` or `fraction`
filters to `doubly_stochastic_score`.

Ties in the default connected-prefix selection are broken by stable `edge_id`.
This tie policy is deterministic and currently not user-configurable.

## Parameters

- `weight`: edge attribute containing positive numeric weights. Default:
  `"weight"`.
- `epsilon`: positive smoothing parameter. Default: `1e-4`.
- `epsilon_mode`: `"relative"` or `"absolute"`. Default: `"relative"`.
- `tolerance`: row/column sum convergence tolerance. Default: `1e-12`.
- `max_iterations`: maximum Sinkhorn iterations per component. Default:
  `1000`.

## Output

- `doubly_stochastic_weight`
- `doubly_stochastic_score`
- `doubly_stochastic_connected_order`
- `doubly_stochastic_connected_selected`

## Reference

PNAS doubly stochastic transformation/filter. DOI: `10.1073/pnas.0904725106`.
