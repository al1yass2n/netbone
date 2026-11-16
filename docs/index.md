# Netbone Documentation

Netbone is a deterministic Python package for extracting, filtering,
measuring, comparing, visualizing, reporting, and saving network backbones.

The package installs and imports as `netbone`. It uses NetworkX for graphs and
pandas DataFrames for method statistics and metric tables. The local web app
provides a browser interface for extraction, comparison, and parameter sweeps.

## Start Here

- [Installation](getting-started/installation.md)
- [Quickstart](getting-started/quickstart.md)
- [Choosing methods](user-guide/choosing-methods.md)
- [Basic extraction workflow](workflows/basic_extraction.md)

## Common Tasks

- Load CSV edge lists or GraphML files: [Loading graphs](user-guide/loading-graphs.md)
- Aggregate temporal event lists before extraction:
  [Temporal aggregation](user-guide/temporal-aggregation.md)
- Select edges or nodes from method statistics: [Filtering](user-guide/filtering.md)
- Compare backbone results: [Method comparison](workflows/method_comparison.md)
- Sweep thresholds, fractions, and method parameters:
  [Parameter sweeps](workflows/parameter_sweeps.md)
- Generate deterministic Markdown summaries:
  [Reports](workflows/deterministic_reporting.md)
- Save reproducible folders with reports, tables, configuration, and graph
  exports: [Experiment bundles](workflows/experiment_bundles.md)
- Run the first extraction workflow in a browser:
  [Local web app](workflows/web_app.md)
- Plot comparison and sweep tables with optional Matplotlib helpers:
  [Optional visualization](workflows/optional_visualization.md)

## Reference

- [Method reference](methods/edge_weight.md)
- [Filter reference](filters/threshold.md)
- [Public API reference](api/public.md)

## Citation

If you use or adapt Netbone in published work, please cite the journal article:

> Yassin, A., Haidar, A., Cherifi, H., Seba, H., & Togni, O. (2023).
> [An evaluation tool for backbone extraction techniques in weighted complex networks](https://doi.org/10.1038/s41598-023-42076-3).
> *Scientific Reports*, 13, Article 17000.
