# Save and reproduce an analysis

Keep the input data and its loading choices with the pipeline settings. The
pipeline document describes scoring and filtering. Column mapping, direction
conversion, and temporal aggregation happen before the pipeline runs.

## Export a self-contained record of the result

This example saves a report, configuration and graph files in a temporary
bundle. To keep the files, replace the temporary destination with a new
directory of your choice.

```python
from pathlib import Path
from tempfile import TemporaryDirectory

import networkx as nx
import netbone as nb

graph = nx.Graph()
graph.add_weighted_edges_from([("A", "B", 8), ("B", "C", 5), ("C", "D", 2)])
pipeline = (
    nb.pipeline()
    .score("edge_weight", weight="weight")
    .filter("threshold", value=5, operator="greater_equal")
)
result = pipeline.run(graph)

with TemporaryDirectory() as directory:
    bundle = nb.save_experiment(result, Path(directory) / "collaboration-backbone")
    restored = nb.Pipeline.from_json(bundle / "pipeline.json").run(graph)
    assert set(restored.graph.edges()) == set(result.graph.edges())
    print((bundle / "manifest.json").read_text(encoding="utf-8"))
```

The manifest lists the bundle schema, package and Python versions, subject
type, and relative paths. Read `report.md` for the human-readable summary
or `report.json` for a machine-readable report. For a report on its own, use
`nb.report(result).write_markdown("report.md")`. `report()` also accepts a
`Comparison` or `SweepResult`.

| Subject | Files to inspect first |
| --- | --- |
| Extraction | `pipeline.json`, `network_metadata.json`, `tables/method_statistics.csv`, `tables/selection.csv`, and `graphs/` |
| Comparison | `pipelines/`, `results/`, `tables/single_metrics.csv`, `tables/pairwise_metrics.csv`, and `tables/spearman.csv` |
| Sweep | `pipelines/index.json`, per-run pipeline files, and the runs, metrics and failures tables |

Extraction bundles include GraphML, GEXF, and CSV for the original and
backbone graphs. Annotation columns and graph attributes indicate whether a
method's target was selected. A temporal extraction can include
`temporal_aggregation.json`. Review the bundle before sharing it because
labels, attributes, or supplied analysis context may be present.

`save_experiment()` requires a new destination by default. With
`overwrite=True` it replaces an empty directory or an earlier Netbone bundle,
and refuses to delete any other existing directory.

## Store settings without the outputs

Call `pipeline.to_json("pipeline.json")` for a registered pipeline.
The document contains `schema_version`, package provenance, and
`method` and `filter` objects with a `name` and `parameters`. Use
`Pipeline.from_json()` for files and `Pipeline.from_dict()` for mappings.
Use JSON-compatible parameter values and keep the Python code for any custom
filter callable. See the [pipeline API](../reference/pipelines.md) for
serialization methods and errors.
