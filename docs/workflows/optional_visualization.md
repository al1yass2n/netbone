# Optional Visualization Workflow

Netbone provides plotting helpers for comparison and sweep tables.
Plotting is optional: `import netbone` does not
import Matplotlib, and users who only need tables do not need plotting
dependencies.

Install the visualization extra when plots are needed:

```bash
pip install netbone[viz]
```

In a local development checkout:

```bash
pip install -e .[dev,viz]
```

## Comparison Plots

```python
import netbone as nb
from netbone import viz

comparison = nb.compare(
    {
        "strict": strict_result,
        "loose": loose_result,
    }
)

viz.plot_comparison_metric(comparison, "edge_retention")
viz.plot_pairwise_metric(comparison, "edge_jaccard")
```

`plot_comparison_metric(...)` uses `Comparison.metric(...)`.
`plot_pairwise_metric(...)` uses `Comparison.pairwise(...)`. Rows with
`status != "ok"` or non-finite metric values are not plotted.

## Sweep Plots

```python
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

By default, sweep plots use `parameter_value` on the x-axis and group lines by
`method`. Pass `x=...` or `group_by=...` to use another column from
`SweepResult.table()`.

## No-Matplotlib Behavior

Calling a plotting helper without Matplotlib installed raises a
`ConfigurationError` explaining that `netbone[viz]` is required. The
deterministic `plot_data` tables remain available without Matplotlib:

```python
comparison.plot_data
sweep_result.plot_data
```

The repository also includes `examples/optional_visualization.py`. The example
always returns plot-ready tables and creates figures only when Matplotlib is
installed.
