# Temporal Aggregation

Netbone converts repeated temporal interactions into a weighted static network
before an ordinary backbone method runs. Temporal weighting and backbone
scoring remain separate decisions, so one aggregated network can feed any
compatible static method.

## Event Input

Each row represents one interaction occurrence:

```csv
source,target,time,magnitude
alice,bob,0,2
bob,alice,1,3
alice,carol,2,1
```

```python
import netbone as nb

temporal = nb.from_temporal_edgelist(
    "events.csv",
    source="source",
    target="target",
    time="time",
    event_weight="magnitude",
)
```

Input is undirected by default. Rows for `(alice, bob)` and `(bob, alice)`
therefore contribute to the same edge. Set `directed=True` when source-to-target
order has meaning:

```python
temporal = nb.from_temporal_edgelist(
    "events.csv",
    time="time",
    event_weight="magnitude",
    directed=True,
)
network = nb.aggregate_temporal(temporal, weighting="baseline")
```

The result is then a directed static `Network`: repeated `alice -> bob` events
are summed together, while `bob -> alice` remains a separate reciprocal arc.
Temporal weighting is otherwise identical in directed and undirected mode.
Only methods whose registry metadata declares directed support can score that
result. Use `nb.to_undirected(...)` explicitly when an undirected projection is
scientifically appropriate.

Repeated events are not deduplicated. Self-interactions are removed while their
node labels remain available. Event magnitudes are optional, default to `1.0`,
and must be finite and non-negative.

Only events at or before `evaluation_time` are included. An omitted evaluation
time resolves to the latest observed event time. Later events are ignored with
a warning.

## Timing Models

The weighting registry contains two explicit timing models. Netbone never
applies min-max, z-score, or data-range normalization to time.

### Snapshot Age

`baseline` and `asf` retain the existing discrete snapshot behavior. Integer
numeric times can be used directly as snapshot ids. Other numeric timestamps
can be binned using `snapshot_size` and an optional `snapshot_origin`:

```python
network = nb.aggregate_temporal(
    temporal,
    weighting="asf",
    evaluation_time=400,
    snapshot_size=40,
    snapshot_origin=0,
    p=3,
    q=0,
    a=5,
)
```

Datetime snapshot input requires a duration such as `"40s"`, `"5min"`, or
`"1h"`. When binning and `snapshot_origin` is omitted, the earliest observed
time becomes the first snapshot boundary.

### Exact Elapsed Time

Persistent-memory kernels use exact event age instead of snapshot bins:

```text
tau = (evaluation_time - event_time) / time_unit
```

For numeric timestamps, omitting `time_unit` uses their native unit. A positive
numeric `time_unit` rescales the difference; for example, timestamps in seconds
can use `time_unit=86400` to express age in days. Datetime input requires an
explicit duration such as `"1h"` or `"1D"`. Fractional ages are preserved.

`snapshot_size` and `snapshot_origin` are rejected for persistent-memory
weightings because binning would change the framework's elapsed-time equations.

## Weighting Functions

Use the registry helpers to inspect the available definitions:

```python
nb.list_temporal_weightings()
nb.describe_temporal_weighting("persistent_weibull")
```

| Name | Age basis | Event relevance |
| --- | --- | --- |
| `baseline` | Snapshot | `1` |
| `asf` | Snapshot | `(1 / (1 + exp(x / p - a)) + q) / (q + 1)` |
| `persistent_exponential` | Exact elapsed | `r + (1-r) * exp(-rate * tau)` |
| `persistent_weibull` | Exact elapsed | `r + (1-r) * exp(-(tau/scale)^shape)` |
| `persistent_log_logistic` | Exact elapsed | `r + (1-r) / (1 + (tau/scale)^shape)` |

Persistent-memory parameters have no package defaults and must be supplied:

- `persistent_level` represents `r` and must be between `0` and `1`, inclusive;
- `decay_rate` is required and non-negative for persistent exponential;
- `scale` and `shape` are required and positive for Weibull and log-logistic.

For example:

```python
network = nb.aggregate_temporal(
    temporal,
    weighting="persistent_weibull",
    evaluation_time=100,
    time_unit=1,
    persistent_level=0.15,
    scale=20,
    shape=2,
)
```

Every event contributes its optional magnitude multiplied by temporal
relevance. Contributions from repeated undirected pairs or repeated directed
arcs are summed. Setting `persistent_level=0` gives complete long-term
forgetting, while `persistent_level=1` gives non-decaying aggregation.

## Output And Provenance

The result is a standard `Network` whose canonical edge or arc `weight`
contains the final temporally aggregated value. For example, LANS supports
both directed and undirected aggregates:

```python
result = (
    nb.pipeline()
    .score("lans", weight="weight")
    .filter("significance", alpha=0.05)
    .run(network)
)
```

Every aggregate edge or arc records `temporal_event_count`,
`temporal_event_weight_sum`, `temporal_first_time`, and `temporal_last_time`.
Persistent-memory outputs additionally record:

- `temporal_persistent_contribution`;
- `temporal_transient_contribution`.

Their sum equals the canonical aggregate `weight` apart from ordinary
floating-point rounding. Resolved timing, weighting parameters, exclusions,
and zero-edge counts are stored under
`network.metadata["temporal_aggregation"]`.

Aggregate zero-weight edges or arcs are dropped by default because many
weighted backbone methods require positive weights. Use
`zero_weight_policy="keep"` when the next method supports zero weights and
retaining them is useful.

## Reproducible Configuration

Temporal configuration is serialized independently from the scoring and
filtering pipeline:

```python
config = nb.TemporalAggregationConfig(
    weighting="persistent_log_logistic",
    parameters={
        "persistent_level": 0.15,
        "scale": 20,
        "shape": 2,
    },
    evaluation_time=100,
    time_unit=1,
)
config.to_json("temporal-aggregation.json")

restored = nb.TemporalAggregationConfig.from_json("temporal-aggregation.json")
network = nb.aggregate_temporal(temporal, config=restored)
```

`nb.save_experiment(...)` saves the resolved temporal configuration alongside
`pipeline.json` and `network_metadata.json`, reproducing both processing
stages.
