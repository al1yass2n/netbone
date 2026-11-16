# Registry discovery and lower-level helpers

Use the top-level registry functions to discover available methods and filters
and inspect their metadata. For direct calls, the helpers shown below operate
on normalized networks or computed method results. Most workflows can use
`netbone.score()`, `netbone.filter_scores()`, or a pipeline.

::: netbone.list_methods
::: netbone.describe_method
::: netbone.list_filters
::: netbone.describe_filter

## Scorers exported by netbone.methods

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
