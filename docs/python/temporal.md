# Aggregate temporal interactions

Use a temporal edge list when rows are events rather than already aggregated
edges. Repeated events for a pair are combined at an evaluation time. Each
resulting edge weight is the sum of included event magnitudes multiplied by
their temporal relevance. Apply a standard backbone method to the resulting
static network.

## Choose the time scale

| Weighting | Clock | Parameters |
| --- | --- | --- |
| `baseline` | Snapshots | None. Sum event magnitudes. |
| `asf` | Snapshots | `p=3.0` sets the age scale, `q=0.0` the long-run floor through `q/(q+1)`, and `a=5.0` the sigmoid offset. |
| `persistent_exponential` | Elapsed time | `persistent_level` in [0, 1] and non-negative `decay_rate` |
| `persistent_weibull` | Elapsed time | `persistent_level` in [0, 1], positive `scale` and `shape` |
| `persistent_log_logistic` | Elapsed time | `persistent_level` in [0, 1], positive `scale` and `shape` |

Use `nb.describe_temporal_weighting(name)` to see a weighting's formula
and parameter constraints. Snapshot modes accept integer numeric snapshots.
For raw numeric or datetime timestamps, bin with `snapshot_size` and optionally
`snapshot_origin`. Datetime input requires a duration such as `"1h"` for
snapshot size. Elapsed modes use exact age and accept `time_unit` to define its
scale. With numeric time, the unit defaults to 1. For datetime input supply a
duration such as `"1d"`. Persistent kernels take all their shape and decay
parameters explicitly.

## Run a temporal analysis

The example measures communications as of time 4. The late event at time 6
is excluded. Each reciprocal direction is aggregated independently.

```python
from pathlib import Path
from tempfile import TemporaryDirectory

import netbone as nb

with TemporaryDirectory() as directory:
    path = Path(directory) / "events.csv"
    path.write_text(
        "source,target,time,magnitude\nA,B,0,2\nA,B,2,1\nB,A,2,3\nB,C,3,2\nA,C,6,1\n",
        encoding="utf-8",
    )
    events = nb.from_temporal_edgelist(path, event_weight="magnitude", directed=True)
    static = nb.aggregate_temporal(
        events,
        weighting="persistent_exponential",
        evaluation_time=4,
        persistent_level=0.2,
        decay_rate=0.5,
    )

graph = static.to_original_graph()
assert graph.has_edge("A", "B") and graph.has_edge("B", "A")
assert not graph.has_edge("A", "C")

result = nb.pipeline().score("lans").filter("significance", alpha=0.25).run(static)
print(result.summary())
```

The evaluation time defaults to the latest event. Omit the magnitude mapping
to count each event with magnitude one. Self-interactions are removed, with
their node labels retained. Aggregate zero-weight edges are dropped by default.
Check `network.metadata["temporal_aggregation"]` on an aggregated network
for resolved timing, event counts and the configuration. Persistent weightings
also record persistent and transient contributions on the edges.

Save aggregation settings via `TemporalAggregationConfig.to_json()`, then
load them with `TemporalAggregationConfig.from_json()` and pass the config to
`aggregate_temporal(events, config)`. Use the same events, column mapping,
direction, and evaluation settings when rerunning the analysis.
