# Reproducible Configuration Workflow

Save a registered pipeline configuration to rerun the same analysis later.

## Load A GraphML Network

```python
import netbone as nb

network = nb.from_graphml("network.graphml")
```

GraphML input is normalized into the same `Network` type as CSV edge lists and
direct NetworkX graphs. Directed GraphML topology is preserved and can be used
with methods that declare directed support. Multigraphs, multidigraphs, and
self-loops are rejected by the shared validation path.

## Save A Registered Pipeline

```python
pipeline = (
    nb.pipeline()
    .score("disparity", weight="weight", pvalue_aggregation="min")
    .filter("significance", alpha=0.05, drop_isolates=False)
)

pipeline.to_json("pipeline.json")
```

The saved configuration records a pipeline schema version, the package version,
registered method and filter names, and their parameters. The JSON file is
deterministic enough to review in version control and can be loaded later with
the same package API.

## Restore And Rerun

```python
restored = nb.Pipeline.from_json("pipeline.json")
result = restored.run(network)
```

`Pipeline.from_json(...)` validates registered method and filter names using
the same registries as `.score(...)` and `.filter(...)`. For workflows that
already manage JSON themselves, `pipeline.to_dict()` and
`Pipeline.from_dict(...)` provide the same round-trip without file I/O.
Older dictionaries without schema metadata still load; newly saved
configurations include the current schema metadata when written back out.

## Custom Callable Filters

Custom filter callables are supported for live Python workflows, but they are
not saved or deserialized as reproducible configuration:

```python
pipeline.to_json("pipeline.json")
```

If the pipeline contains a custom callable filter, this raises
`ConfigurationError`. `Pipeline.from_dict(...)` and `Pipeline.from_json(...)`
also reject custom callable config records. Recreate the callable in Python and
attach it with `.filter(callable, ...)` instead.
