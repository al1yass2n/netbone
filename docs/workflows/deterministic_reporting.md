# Deterministic Reporting Workflow

Netbone generates deterministic reports for extraction results, comparisons,
and sweeps. Reports use computed values, metadata, warnings, and
pipeline configuration. They do not require LLM or web dependencies.

## Backbone Result Report

```python
result = (
    nb.pipeline()
    .score("edge_weight", weight="weight")
    .filter("threshold", value=2.0, operator="greater_equal")
    .run(network)
)

report = nb.report(result)
markdown = report.to_markdown()
payload = report.to_dict()
report.write_markdown("reports/backbone_report.md")
```

The report includes:

- retention and connectivity summary values;
- method metadata and parameters;
- filter metadata and parameters;
- selection counts;
- warning and limitation sections;
- reproducibility details, including the pipeline configuration.

## Comparison Report

```python
comparison = nb.compare(
    {
        "strict": strict_result,
        "loose": loose_result,
    }
)

report = nb.report(comparison)
```

The comparison report includes default single-result and pairwise metric
tables. Invalid or undefined rows remain visible with explicit status and
explanation values.

## Sweep Report

```python
sweep_result = (
    nb.sweep(network)
    .score("edge_weight", weight="weight")
    .filter("threshold", operator="greater_equal")
    .vary_filter(value=[1.0, 2.0, 4.0])
    .measure(["edge_retention", "connected_component_count"])
    .run()
)

report = nb.report(sweep_result)
```

The sweep report includes run rows, metric rows, failure rows, and score-cache
hit/miss counts.

## Markdown And Dict Output

`Report.to_markdown()` is intended for readable deterministic summaries.
`Report.to_dict()` returns a JSON-compatible payload for tests, notebooks,
saved artifacts, or later rendering layers.
`Report.write_markdown(...)` writes the Markdown rendering to a UTF-8 file,
creates parent directories when needed, and can protect existing files with
`overwrite=False`.
