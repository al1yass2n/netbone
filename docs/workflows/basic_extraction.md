# Basic Extraction Workflow

This workflow demonstrates the core deterministic extraction path:

```text
CSV edge list -> Network -> MethodResult -> Selection -> BackboneResult
```

It uses the baseline `edge_weight` scorer and the `threshold` filter. This is
intended to validate the package workflow, not to claim that edge weights alone
are a complete backbone extraction method.

## Load

```python
import netbone as nb

network = nb.from_edgelist(
    "network.csv",
    source="source",
    target="target",
    weight="strength",
)
```

The CSV column `strength` is stored internally as the canonical edge attribute
`weight`. The original column name is preserved in
`network.metadata["edge_weight_original_column"]`.

## Configure

```python
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
```

Scoring and filtering are configured separately because users should be able
to inspect method output before deciding how to filter it.

## Compute Scores

```python
method_result = pipeline.compute(network)
method_result.statistics
```

The current `edge_weight` output table contains:

- `edge_id`
- `source_id`
- `target_id`
- `source`
- `target`
- `score`

## Run Extraction

```python
result = pipeline.run(network)

result.graph
result.summary()
```

The returned graph uses original node ids. The summary includes explicit
retention and connectivity values, including node fraction, edge fraction,
isolated-node count, and connected-component count.

## Runnable Example

Run the same workflow from the repository root:

```bash
python examples/basic_extraction.py
```
