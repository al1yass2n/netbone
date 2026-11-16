# Reproducible Experiment Bundle Workflow

Use `nb.save_experiment(...)` to save deterministic analysis
artifacts to a directory. Bundles are meant for inspection, sharing, and later
rerunning registered pipeline configurations.

## Save A Backbone Result

```python
import netbone as nb

result = (
    nb.pipeline()
    .score("edge_weight", weight="weight")
    .filter("threshold", value=2.0, operator="greater_equal")
    .run(graph)
)

bundle_path = nb.save_experiment(result, "experiments/backbone")
```

The bundle includes:

- `manifest.json`
- `report.md`
- `report.json`
- `result.json`
- `pipeline.json`
- `network_metadata.json`
- method statistics and selection CSV tables
- original and backbone graph node/edge CSV tables
- `graphs/original_annotated.graphml`
- `graphs/backbone.graphml`
- `graphs/original_annotated.gexf`
- `graphs/backbone.gexf`

For a result produced from temporal aggregation, the bundle also includes the
resolved `temporal_aggregation.json`. It records the fixed evaluation time,
elapsed-time or snapshot settings, weighting, and weighting parameters
separately from the static `pipeline.json`.

The annotated graph exports use method-and-pipeline-hash-prefixed columns so
multiple analyses can be compared later without ambiguous names. The short hash
is deterministic from the saved method/filter configuration. Annotations are
written only on the method target: edge-target methods annotate edges, and
node-target methods annotate nodes. For example, an `edge_weight` result writes
edge columns such as:

- `netbone_edge_weight_<hash>_selected`
- `netbone_edge_weight_<hash>_role`
- `netbone_edge_weight_<hash>_color`
- `netbone_edge_weight_<hash>_target`
- `netbone_edge_weight_<hash>_score`

Every computed method-statistics column is attached to its target with the same
prefix. Internal edge, node, and endpoint identity columns are omitted. For
example, Link Salience exports `netbone_link_salience_<hash>_link_salience`,
while Disparity exports its weight, endpoint fractions, endpoint p-values, and
combined p-value. The statistic attributes are present in annotated-original
and backbone-only GraphML and GEXF files.

Only the GraphML/GEXF annotation columns use this hash. The rest of the bundle
keeps the normal files and table names, and the full pipeline remains saved in
`pipeline.json`.

The default visualization palette is colorblind-safe and paper-friendly:

- selected target items: blue `#0072B2`
- rejected target items: light gray `#D9D9D9`

The GEXF files also include Gephi-readable numeric method statistics plus `viz`
color and size/thickness metadata on the annotated target elements.

The saved `pipeline.json` can be restored with:

```python
pipeline = nb.Pipeline.from_json("experiments/backbone/pipeline.json")
reproduced = pipeline.run(graph)
```

## Save Comparisons And Sweeps

`nb.save_experiment(...)` also accepts `Comparison` and `SweepResult` objects:

```python
comparison_path = nb.save_experiment(comparison, "experiments/comparison")
sweep_path = nb.save_experiment(sweep_result, "experiments/sweep")
```

Comparison bundles include single-metric, pairwise-metric, and Spearman CSV
tables plus per-result pipeline and summary JSON files.

Sweep bundles include run, metric, and failure CSV tables, generated pipeline
JSON files, and summary JSON files for successful runs.

## Overwrite Policy

Existing directories are refused by default:

```python
nb.save_experiment(result, "experiments/backbone")
```

Pass `overwrite=True` to replace an existing bundle directory:

```python
nb.save_experiment(result, "experiments/backbone", overwrite=True)
```
