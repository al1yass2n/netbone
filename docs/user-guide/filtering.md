# Filtering

Backbone extraction has two steps:

1. A method computes node or edge statistics.
2. A filter converts those statistics into selected and rejected ids.

This separation is important because method values do not all mean the same
thing. Some methods produce high-is-important scores. Others produce
low-is-important p-values.

## Threshold Filter

Use `threshold` when you already know the statistic value you want to keep:

```python
result = (
    nb.pipeline()
    .score("edge_weight", weight="weight")
    .filter("threshold", value=2.0, operator="greater_equal")
    .run(graph)
)
```

Supported operators include `greater`, `greater_equal`, `less`, `less_equal`,
`equal`, and `not_equal`.

## Fraction Filter

Use `fraction` when you want to keep a retained fraction of ranked items:

```python
result = (
    nb.pipeline()
    .score("edge_weight", weight="weight")
    .filter("fraction", fraction=0.10)
    .run(graph)
)
```

The filter uses the method's preferred direction unless you explicitly pass
`direction="higher"` or `direction="lower"`.

Tie behavior is explicit:

- `include_all_ties` keeps every item tied at the cutoff;
- `exact_stable` keeps exactly the requested count using stable ids;
- `raise_on_tie` fails if cutoff ties would affect the result;
- `random_seeded` uses a required seed to sample cutoff ties.

## Significance Filter

Use `significance` for p-value methods:

```python
result = (
    nb.pipeline()
    .score("disparity", weight="weight")
    .filter("significance", alpha=0.05, correction="fdr_bh")
    .run(graph)
)
```

The significance filter is strict: it selects p-values `< alpha`, not `<=`.
When `statistic` is omitted, it uses the method result's primary statistic.

## Default Filter

Use `default` when you want the method's registered default filter:

```python
result = (
    nb.pipeline()
    .score("disparity", weight="weight")
    .filter("default", alpha=0.05)
    .run(graph)
)
```

The resolved filter behavior is recorded in the result metadata.

## Edge And Node Targets

Edge-target methods select edges. Isolated nodes are kept by default; pass
`drop_isolates=True` to remove nodes with no retained incident edges.

Node-target methods select nodes. The output graph is the node-induced subgraph
on selected nodes.
