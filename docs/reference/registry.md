# Registry and helpers

Use the top-level registry functions to discover available methods and filters
and inspect their metadata. For direct calls, the helpers shown below operate
on normalized networks or computed method results. Most workflows can use
`netbone.score()`, `netbone.filter_scores()`, or a pipeline.

::: netbone.list_methods
::: netbone.describe_method
::: netbone.list_filters
::: netbone.describe_filter

## Method references

`describe_method(name)` names the papers behind each method. `reference` and
`doi` describe the paper that defines the method, and `references` lists every
paper with its `citation`, `doi`, `url`, and `bibtex`. A
[report](measurement.md) copies the list into its method section. Edge Weight
is a baseline, so its list is empty and `reference_note` explains why.
`describe_temporal_weighting(name)` returns the same keys for the
[temporal weightings](../python/temporal.md#references).

```python
for paper in nb.describe_method("node_betweenness")["references"]:
    print(paper["citation"], paper["url"])
```

## Scorers exported by netbone.methods

[`nb.score(graph, name, **parameters)`](pipelines.md) runs any of the 20
registered methods, checks its parameters, and resolves `weight="auto"`, so
use it as the entry point. `netbone.methods` also exports four scorers for
direct calls on a normalized `Network`. They skip the weight resolution, so
pass `weight` explicitly.

::: netbone.methods.compute_disparity
::: netbone.methods.compute_edge_weight
::: netbone.methods.compute_lans
::: netbone.methods.compute_link_salience

## Filters exported by netbone.filters

::: netbone.filters.apply_threshold
::: netbone.filters.apply_fraction
::: netbone.filters.apply_significance

## Version

Read `netbone.__version__` to record the imported package version.
