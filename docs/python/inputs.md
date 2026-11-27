# Prepare network inputs

A `Network` is Netbone's validated representation of a simple graph. Its
internal integer identifiers link graph elements to statistics rows. Use
`network.to_original_graph()` or `result.graph` when you need the original
node labels and input attributes. The input graph stays available as
`result.original_graph`.

## Choose a loader

| Input | Python entry point | How weights and direction are handled |
| --- | --- | --- |
| CSV or TSV edge list | `nb.from_edgelist(path)` | Selected weight column becomes `weight`. Set `weight=None` for files without a weight column and `delimiter="\t"` for TSV. |
| GraphML | `nb.from_graphml(path)` | Direction and node and edge attributes come from the file. Pass the chosen numeric attribute to the scoring method. |
| NetworkX | `nb.from_graph(graph)` | A simple `Graph` or `DiGraph` is normalized. Scoring and pipeline execution also accept NetworkX graphs directly. |
| Time-stamped rows | `nb.from_temporal_edgelist(path)` | [Aggregate events into a weighted graph](temporal.md) before running a pipeline. |

By default, static edge lists expect `source`, `target`, and `weight` columns.
Pass their actual names as keyword arguments. A static file needs one row per
edge. With `directed=False`, reverse rows belong to the same undirected edge and
are rejected as duplicates. Node ids are read as written: a column of plain
integers such as `1, 2, 10` becomes Python ints, and anything else, including
`007`, `NA`, or `None`, stays a string label. Spaces after the delimiter are
ignored, and so is a trailing delimiter at the end of each row. A row with more
non-empty values than the header has columns is rejected with its row number,
because its columns would not line up. Weights must be finite numbers, and a self-loop row is rejected with
its row number. GraphML or a NetworkX graph can represent isolated nodes
explicitly.

## Preserve or project directed links

Use `directed=True` for a CSV containing source-to-target arcs. A directed
file can contain both `A → B` and `B → A`. Check the
[method catalog](../reference/methods.md) for directed support. If orientation
can be discarded for your question, project explicitly and record the merge
rule for reciprocal weights.

```python
import networkx as nx
import netbone as nb

flows = nx.DiGraph()
flows.add_weighted_edges_from([("north", "south", 4), ("south", "north", 3)])
projected = nb.to_undirected(flows, weight="weight", reciprocal_merge="sum")
assert projected.to_original_graph()["north"]["south"]["weight"] == 7
```

The merge choices are `sum`, `mean`, `max`, and `min`. Use
`weight=None, reciprocal_merge=None` for unweighted projection. Reciprocal
attribute conflicts are recorded as directional provenance.

Parallel edges are unsupported. Most methods reject self-loops, so check
compatibility before scoring data with loops. The
[input API reference](../reference/networks.md) contains the loader signatures.
