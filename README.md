# Netbone

Netbone is a Python package and local web app for extracting, inspecting, and
comparing network backbones. The package installs and imports as `netbone`.

Source for `0.3.0` is maintained at [al1yass2n/netbone on GitHub](https://github.com/al1yass2n/netbone).
The [published `0.2.3` release](https://pypi.org/project/netbone/0.2.3/) points to the
[original GitLab repository](https://gitlab.liris.cnrs.fr/coregraphie/netbone).

Netbone supports the following workflows:

- NetworkX is the only supported graph backend.
- Simple undirected graphs are supported across the package. Simple directed
  graphs are supported by Disparity, LANS, Link Salience, Link Prediction,
  Link Prediction Isolation Forest, and Noise Corrected, with orientation preserved.
- CSV edge-list loading, GraphML loading, and direct NetworkX input are
  supported.
- Repeated temporal event lists can be aggregated into weighted static
  networks with registered temporal weighting functions.
- Method statistics are stored as pandas `DataFrame` objects.
- Built-in scorers include `edge_weight`, `disparity`, `lans`,
  `link_salience`, `edge_betweenness`, `maximum_spanning_forest`,
  `primary_linkage`, `multiple_linkage`, `planar_maximally_filtered_graph`,
  `h_backbone`, `gspar`, `doubly_stochastic`, `marginal_likelihood`, `glanb`,
  `link_prediction`, `link_prediction_iforest`, `node_degree`, `node_strength`, `noise_corrected`,
  and `node_betweenness`.
- Built-in filters include `threshold`, `fraction`, `significance`, and
  `default`.
- Custom filter callables are supported.
- Named backbone results can be compared with tidy metric tables.
- Threshold, retained-fraction, method-parameter, and method-filter grid sweeps
  can be run with score reuse and failure isolation.
- Registered pipeline configurations can be serialized and restored.
- Deterministic Markdown reports can be generated without LLM dependencies.
- Optional plotting helpers are available through the `viz` extra.
- Reproducible experiment bundles can be saved as Markdown, JSON, and CSV
  artifacts.

## Install

See the full [installation guide](docs/getting-started/installation.md) for
user, visualization, development, and documentation installs.

```bash
pip install .
```

Optional plotting helpers use Matplotlib and can be installed separately:

```bash
pip install .[viz]
```

Isolation-Forest link-prediction scoring uses optional scikit-learn support:

```bash
pip install .[ml]
```

## Basic Usage

See the [quickstart](docs/getting-started/quickstart.md) and
[basic extraction workflow](docs/workflows/basic_extraction.md) for a fuller
walkthrough.

```python
import netbone as nb

network = nb.from_edgelist(
    "network.csv",
    source="source",
    target="target",
    weight="weight",
)

pipeline = (
    nb.pipeline()
    .score("edge_weight", weight="weight")
    .filter(
        "threshold",
        value=2.0,
        operator="greater_equal",
        drop_isolates=False,
    )
)

method_result = pipeline.compute(network)
result = pipeline.run(network)

result.graph  # NetworkX graph using original node ids
result.statistics  # pandas DataFrame with edge statistics
result.summary()
```

## Temporal Aggregation

Repeated temporal interactions can be weighted and aggregated before applying
any compatible backbone pipeline:

```python
temporal = nb.from_temporal_edgelist(
    "events.csv",
    time="time",
    event_weight="magnitude",
)

network = nb.aggregate_temporal(
    temporal,
    weighting="asf",
    evaluation_time=100,
    p=3,
    q=0,
    a=5,
)

result = (
    nb.pipeline()
    .score("disparity", weight="weight")
    .filter("significance", alpha=0.05)
    .run(network)
)
```

Pass `directed=True` to `from_temporal_edgelist(...)` when event orientation
matters. Repeated ordered events then aggregate per arc, and reciprocal arcs
remain separate for backbone methods that support directed networks.

Available temporal weightings are `baseline`, `asf`,
`persistent_exponential`, `persistent_weibull`, and
`persistent_log_logistic`. Baseline and ASF use discrete snapshot timing;
persistent-memory kernels use exact elapsed time and require their parameters
explicitly. Netbone does not apply data-range normalization. See the
[temporal aggregation guide](docs/user-guide/temporal-aggregation.md) for
timing, future-event behavior, component provenance, and saved configuration.

## Local Web App

Start the local web app to extract and compare backbones in your browser:

```bash
python -m netbone.webapp
```

The installed command is also available:

```bash
netbone-web
```

Open an example or import a CSV, TSV, temporal event list, or GraphML file.
Review the network settings, choose a scoring method and filter, then inspect
the resulting graph and statistics. You can save backbones for comparison, sweep
method and filter settings, and export graphs, tables, and experiment bundles.
See the [local web app guide](docs/workflows/web_app.md) for the full workflow.

GraphML files can be loaded through the same normalized `Network` contract:

```python
network = nb.from_graphml("network.graphml")
```

GraphML direction is detected automatically. Directed CSV edge lists are
explicit:

```python
network = nb.from_edgelist("arcs.csv", directed=True)
result = nb.pipeline().score("lans").filter("significance").run(network)
```

Registered pipeline configurations can be saved and restored:

```python
pipeline.to_json("pipeline.json")
restored = nb.Pipeline.from_json("pipeline.json")
result = restored.run(network)
```

Saved pipeline files include a schema version and package version so they can
be reviewed and rerun as reproducible artifacts.

Custom filter callables are intentionally not deserialized from saved
configuration. Recreate those callables in Python and attach them with
`.filter(callable, ...)`.

## Identifier Policy

Netbone normalizes input graphs into an internal NetworkX graph with integer
node and edge identifiers. Original node ids and edge attributes are preserved.
Method statistics expose both internal ids and original node ids:

- `edge_id`
- `source_id`
- `target_id`
- `source`
- `target`
- `score`

Backbone result graphs are returned with the original node ids by default.

CSV edge-list weights are stored under the canonical edge attribute `weight`.
If a different input column is used, such as `strength`, the original column
name is retained in `network.metadata["edge_weight_original_column"]`.

## Edge Filtering

The `threshold` filter selects method statistics using an explicit operator.
The `fraction` filter selects a retained fraction using the method's preferred
direction or an explicit `direction="higher"|"lower"` override. It also
supports explicit tie policies, including reproducible seeded tie-breaking.
The `significance` filter selects p-value method results using an alpha
threshold and optional correction.

For edge selections, isolated nodes are kept by default. Pass
`drop_isolates=True` to remove nodes that have no retained incident edges.
For node selections, the backbone graph is the node-induced subgraph on
selected nodes.

Use `nb.list_methods()`, `nb.describe_method(...)`, `nb.list_filters()`,
`nb.describe_filter(...)`, `nb.list_metrics()`, and `nb.describe_metric(...)`
to inspect registered built-ins.

See [Choosing Methods](docs/user-guide/choosing-methods.md) for guidance on
matching methods to analysis goals and assumptions.

Similarity-based link-prediction backbones compute neutral scores first, then
choose high-similarity or low-similarity extraction in the filter:

```python
high_similarity = (
    nb.pipeline()
    .score("link_prediction", similarity="preferential_attachment")
    .filter("default", direction="higher")
    .run(network)
)

low_similarity = (
    nb.pipeline()
    .score("link_prediction", similarity="preferential_attachment")
    .filter("default", direction="lower")
    .run(network)
)
```

Pass `weight="weight"` to use positive numeric edge weights in the
link-prediction similarity. `weight_alpha` controls how strongly weights affect
the effective weighted topology. `distance_transform="inverse"` treats weights
as connection strengths; `distance_transform="identity"` treats weights as
path distances:

```python
weighted_similarity = (
    nb.pipeline()
    .score(
        "link_prediction",
        similarity="local_path",
        weight="weight",
        weight_alpha=1.0,
        distance_transform="inverse",
    )
    .filter("default", direction="higher")
    .run(network)
)
```

Isolation Forest can combine one or more link-prediction similarities and then
leave retention to the ordinary fraction or threshold filters:

```python
anomalous_links = (
    nb.pipeline()
    .score(
        "link_prediction_iforest",
        similarities=["preferential_attachment", "shortest_path"],
        random_state=0,
    )
    .filter("fraction", fraction=0.1)
    .run(network)
)
```

## Comparison

Use `nb.compare(...)` to compare named backbone results:

```python
comparison = nb.compare({"strict": result_a, "loose": result_b})
comparison.table(metrics=["edge_retention", "connected_component_count"])
comparison.pairwise(metrics=["edge_jaccard", "edge_overlap_coefficient"])
comparison.spearman()
```

Invalid or undefined metric and comparison cases are returned as table rows
with `status` and `explanation` values.

Pairwise overlap metrics require the same original graph topology. Score
alignment and Spearman require the same attributed original graph so scores
computed from different weights are not silently aligned.

## Parameter Sweeps

Use `nb.sweep(...)` to explore pipeline configurations:

```python
sweep_result = (
    nb.sweep(network)
    .score("edge_weight", weight="weight")
    .filter("threshold", operator="greater_equal")
    .vary_filter(value=[1.0, 2.0, 4.0])
    .measure(["edge_count", "edge_retention"])
    .run()
)

sweep_result.table()
sweep_result.runs
sweep_result.failures
```

Full grids cross method configurations with filter configurations. Use a single
filter entry when you want the same filter across methods:

```python
sweep_result = (
    nb.sweep(network)
    .grid(
        methods={
            "edge_weight": {"weight": "weight"},
            "disparity": {
                "weight": "weight",
                "pvalue_aggregation": ["min", "max"],
            },
            "link_salience": {"weight": "weight"},
        },
        filters={
            "fraction": {"fraction": 0.10},
        },
    )
    .measure(["edge_retention", "connected_component_count"])
    .run()
)
```

## Deterministic Reports

Use `nb.report(...)` to generate deterministic summaries for extraction
results, comparisons, and sweeps:

```python
report = nb.report(result)
markdown = report.to_markdown()
payload = report.to_dict()
report.write_markdown("backbone_report.md")
```

Reports are built from computed values, result metadata, warnings, and pipeline
configuration. They do not require LLM or web dependencies. `to_markdown()`
returns a string for notebooks and tests; `write_markdown(...)` writes a UTF-8
Markdown file for reproducible artifacts.

## Experiment Bundles

Use `nb.save_experiment(...)` to save a deterministic folder for an extraction
result, comparison, or sweep:

```python
bundle_path = nb.save_experiment(result, "experiments/backbone")
```

Bundles include `manifest.json`, `report.md`, `report.json`, JSON summaries,
pipeline configuration files, CSV tables, and GraphML/GEXF graph exports.
Backbone result graph exports include method-and-pipeline-hash-prefixed
annotation attributes such as `netbone_edge_weight_<hash>_selected`,
`netbone_edge_weight_<hash>_role`, and
`netbone_edge_weight_<hash>_color`. These annotations are written only on the
method target: edges for edge-target methods and nodes for node-target methods.
Existing directories are refused by default; pass `overwrite=True` to replace an
existing bundle directory.

## Optional Visualization

Plotting is optional. The core package exposes plot-ready tables without
requiring Matplotlib; install the `viz` extra to use plotting helpers:

```python
from netbone import viz

comparison = nb.compare({"strict": strict_result, "loose": loose_result})
viz.plot_comparison_metric(comparison, "edge_retention")
viz.plot_pairwise_metric(comparison, "edge_jaccard")

sweep_result = (
    nb.sweep(network)
    .score("edge_weight", weight="weight")
    .filter("threshold", operator="greater_equal")
    .vary_filter(value=[1.0, 2.0, 3.0])
    .measure(["edge_count"])
    .run()
)
viz.plot_sweep_metric(sweep_result, "edge_count")
```

## Method And Filter Documentation

- [Documentation Home](docs/index.md)
- [Installation](docs/getting-started/installation.md)
- [Quickstart](docs/getting-started/quickstart.md)
- [Choosing Methods](docs/user-guide/choosing-methods.md)
- [Loading Graphs](docs/user-guide/loading-graphs.md)
- [Temporal Aggregation](docs/user-guide/temporal-aggregation.md)
- [Filtering](docs/user-guide/filtering.md)
- [Edge Weight](docs/methods/edge_weight.md)
- [Disparity](docs/methods/disparity.md)
- [Edge Betweenness](docs/methods/edge_betweenness.md)
- [LANS](docs/methods/lans.md)
- [Link Salience](docs/methods/link_salience.md)
- [Link Prediction Backbone Framework](docs/methods/link_prediction.md)
- [Maximum Spanning Forest](docs/methods/maximum_spanning_forest.md)
- [Primary Linkage Analysis](docs/methods/primary_linkage.md)
- [Multiple Linkage Analysis](docs/methods/multiple_linkage.md)
- [Planar Maximally Filtered Graph](docs/methods/planar_maximally_filtered_graph.md)
- [H-Backbone](docs/methods/h_backbone.md)
- [GSPAR](docs/methods/gspar.md)
- [Doubly Stochastic](docs/methods/doubly_stochastic.md)
- [Marginal Likelihood](docs/methods/marginal_likelihood.md)
- [Noise Corrected](docs/methods/noise_corrected.md)
- [GLANB](docs/methods/glanb.md)
- [Node Degree](docs/methods/node_degree.md)
- [Node Strength](docs/methods/node_strength.md)
- [Node Betweenness](docs/methods/node_betweenness.md)
- [Threshold Filter](docs/filters/threshold.md)
- [Fraction Filter](docs/filters/fraction.md)
- [Significance Filter](docs/filters/significance.md)
- [Default Filter](docs/filters/default.md)
- [Basic Extraction Workflow](docs/workflows/basic_extraction.md)
- [Local Web App Workflow](docs/workflows/web_app.md)
- [Method Comparison Workflow](docs/workflows/method_comparison.md)
- [Parameter Sweep Workflow](docs/workflows/parameter_sweeps.md)
- [Reproducible Configuration Workflow](docs/workflows/reproducible_configs.md)
- [Reproducible Experiment Bundle Workflow](docs/workflows/experiment_bundles.md)
- [Deterministic Reporting Workflow](docs/workflows/deterministic_reporting.md)
- [Optional Visualization Workflow](docs/workflows/optional_visualization.md)
- [Public API Reference](docs/api/public.md)

## Examples

Run executable workflow examples from the repository root:

```bash
python examples/basic_extraction.py
python examples/method_comparison.py
python examples/parameter_sweep.py
python examples/deterministic_reporting.py
python examples/optional_visualization.py
python examples/experiment_bundle.py
python examples/temporal_aggregation.py
```

## Development

Run these checks before contributing changes:

```bash
pytest
ruff check .
ruff format --check .
mypy src
python -m build
```

Core dependencies are limited to NetworkX and pandas. pandas is used because
the public method-statistics contract is tabular and inspectable.

## Credits and license

The [0.2.3 PyPI release](https://pypi.org/project/netbone/0.2.3/) credits Ali Yassin
as the software author and lists Abbas Haidar (`AbbasH`) and Ali Yassin (`aliyassin`)
as maintainers. Netbone is distributed under the [MIT License](LICENSE).

## Citation

If you use or adapt Netbone in published work, please cite the journal article:

> Yassin, A., Haidar, A., Cherifi, H., Seba, H., & Togni, O. (2023).
> [An evaluation tool for backbone extraction techniques in weighted complex networks](https://doi.org/10.1038/s41598-023-42076-3).
> *Scientific Reports*, 13, Article 17000.
