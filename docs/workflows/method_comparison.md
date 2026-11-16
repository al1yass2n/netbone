# Method Comparison Workflow

Netbone produces comparison tables for named backbone results.

```python
comparison = nb.compare(
    {
        "strict": strict_result,
        "loose": loose_result,
    }
)

single_metrics = comparison.table(
    metrics=[
        "edge_retention",
        "weight_retention",
        "connected_component_count",
    ]
)

pairwise_metrics = comparison.pairwise(
    metrics=[
        "edge_overlap",
        "edge_jaccard",
        "edge_overlap_coefficient",
    ]
)
```

## Single-Result Metrics

Single-result metric rows use this shape:

- `result`
- `metric`
- `value`
- `status`
- `explanation`

Initial registered single-result metrics include:

- `node_count`
- `edge_count`
- `node_retention`
- `edge_retention`
- `weight_retention`
- `connected_component_count`
- `isolated_node_count`

`connected_component_count` is intentionally undirected. Directed results can
request `weakly_connected_component_count` and
`strongly_connected_component_count`; metric failures remain explicit invalid
rows instead of being silently reinterpreted.

`weight_retention` uses the method's explicit `weight` parameter when one was
declared, such as `weight="strength"`. If a method was configured without an
explicit weight attribute, the metric falls back to the graph's `weight`
attribute when present or treats missing weights as `1.0`. Non-numeric,
non-finite, or negative weights produce an invalid metric row with an
explanation.

## Pairwise Metrics

Pairwise metric rows use this shape:

- `result_a`
- `result_b`
- `metric`
- `value`
- `status`
- `explanation`
- `same_original_graph`
- `same_original_topology`
- `same_target`

Initial registered pairwise metrics include:

- `node_overlap`
- `edge_overlap`
- `node_jaccard`
- `edge_jaccard`
- `node_overlap_coefficient`
- `edge_overlap_coefficient`
- `score_spearman`

Pairwise graph-overlap metrics require results from the same original graph
topology, but they can compare results produced by methods with different
targets because they compare the final backbone graphs. The
`same_original_topology` column records the topology check. The
`same_original_graph` column records whether original graph attributes also
match. The `same_target` column records target differences instead of rejecting
overlap rows. When a metric is invalid or undefined, the row remains in the
table with a non-`ok` status and an explanation.

## Score Alignment

Compatible method outputs can be aligned by graph identity:

```python
alignment = comparison.score_alignment("strict", "loose")
spearman = comparison.spearman()
```

Score alignment requires the same attributed original graph and target. Edge
statistics are aligned by original endpoint identity, while each side's
internal `edge_id` is kept in diagnostic columns. It reports each method's raw
values, output type, preferred direction, and derived importance ranks.
Spearman uses those importance ranks, so score-score, p-value-p-value, and
score-p-value comparisons can all be valid when the aligned statistics are
finite numeric values. Incompatible or undefined Spearman comparisons are
reported as invalid or undefined rows rather than silently omitted.
