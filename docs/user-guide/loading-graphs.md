# Loading Graphs

Netbone accepts NetworkX graphs directly and provides convenience loaders for
CSV edge lists, temporal event lists, and GraphML files.

## NetworkX Graphs

```python
import networkx as nx
import netbone as nb

graph = nx.Graph()
graph.add_edge("alice", "bob", weight=4.0)

network = nb.from_graph(graph)
```

Simple directed graphs use `nx.DiGraph`. Arc orientation and reciprocal arcs
are preserved, but the selected scoring method must declare directed support.
The directed-capable built-ins are `disparity`, `lans`, `link_salience`,
`link_prediction`, `link_prediction_iforest`, and `noise_corrected`.

You can also pass a NetworkX graph directly to `nb.score(...)`,
`nb.pipeline().run(...)`, or `nb.sweep(...)`. Netbone normalizes it internally
without mutating the input graph.

## CSV Edge Lists

```python
network = nb.from_edgelist(
    "network.csv",
    source="source",
    target="target",
    weight="strength",
    directed=True,
)
```

Set `directed=True` when source-to-target order defines an arc. With the
default `directed=False`, reversed rows are duplicate undirected edges. The
input weight column is normalized to the canonical edge attribute `weight`.
If the original column was named differently, Netbone records that in
`network.metadata["edge_weight_original_column"]`.

## GraphML

```python
network = nb.from_graphml("network.graphml")
```

GraphML input follows the same normalization and validation rules as direct
NetworkX input. Its directed or undirected declaration is detected from the
file and preserved.

## Directed To Undirected Projection

Use an explicit projection when an analysis should intentionally ignore arc
direction:

```python
directed = nb.from_graphml("directed-network.graphml")
network = nb.to_undirected(
    directed,
    weight="strength",
    reciprocal_merge="sum",
)
```

One-way arcs become undirected edges with their attributes unchanged. When
both `a -> b` and `b -> a` exist, Netbone combines the selected finite numeric
weight with the selected `sum`, `mean`, `max`, or `min` rule. Equal other
attributes are retained. Conflicting or direction-specific values are
preserved in the projected edge's
`netbone_directional_conflicts` provenance attribute.

For an unweighted projection, pass `weight=None` and
`reciprocal_merge=None`. Numeric attributes other than the selected weight are
not aggregated because their meaning may differ from the weight semantics.

The operation does not mutate the directed input. Conversion counts, the merge
rule, and an interpretation warning are recorded in `network.metadata`. Choose
the rule from the meaning of the selected weight: `sum` preserves total
directed volume, `mean` preserves the numeric scale, and `max` or `min`
preserves an extreme. Once projected, arc direction cannot be recovered from
the undirected topology.

## Temporal Event Lists

Repeated interactions can be loaded separately and aggregated into a weighted
static network:

```python
temporal = nb.from_temporal_edgelist(
    "events.csv",
    time="timestamp",
    event_weight="magnitude",
    directed=True,
)
network = nb.aggregate_temporal(
    temporal,
    weighting="asf",
    snapshot_size="40s",
)
```

Omit `directed=True` to aggregate reciprocal event rows into the same
undirected edge. With it enabled, repeated ordered events are aggregated per
arc and reciprocal arcs remain distinct. The resulting static directed network
can be used by methods that declare directed support or explicitly projected
with `nb.to_undirected(...)`.

See [Temporal aggregation](temporal-aggregation.md) for snapshot and exact
elapsed-time semantics, weighting functions, metadata, and reproducible
configuration.

## Supported Graph Scope

Netbone supports simple undirected graphs. Directed inputs work with
`disparity`, `lans`, `link_salience`, `link_prediction`,
`link_prediction_iforest`, and `noise_corrected`. To use other methods on a
directed graph, project it with `nb.to_undirected(...)` before scoring.
Directed result summaries report weakly and strongly connected component counts
instead of an ambiguous generic component count.

Temporal event lists can aggregate into an undirected or directed static graph.
Self-loops, multigraphs, multidigraphs, native temporal graph algorithms,
multilayer networks, and alternate graph backends remain unsupported.

## Node And Edge Identifiers

Internally, Netbone assigns deterministic integer node and edge ids. Method
statistics include both internal ids and original node labels:

- `edge_id`
- `source_id`
- `target_id`
- `source`
- `target`

Backbone result graphs are returned with original node labels by default.
