# Extract your first backbone

You have a network of collaboration counts between teams. Keep the links
supported by at least three collaborations, then check how much of the network
survived. This tutorial uses a temporary CSV and runs after a
[core installation](install.md).

Save and run this as a Python script.

```python
from pathlib import Path
from tempfile import TemporaryDirectory

import netbone as nb

with TemporaryDirectory() as directory:
    path = Path(directory) / "collaborations.csv"
    path.write_text(
        "source,target,collaborations\n"
        "design,engineering,8\n"
        "design,research,2\n"
        "engineering,research,5\n"
        "research,support,1\n",
        encoding="utf-8",
    )
    network = nb.from_edgelist(path, weight="collaborations")

scores = nb.score(network, "edge_weight", weight="weight")
result = nb.filter_scores(
    network, scores, "threshold", value=3, operator="greater_equal"
)

print(scores.statistics[["source", "target", "score"]].to_string(index=False))
print(f"Retained {result.edge_fraction:.0%} of the edges.")
print(
    "Isolates:", sorted(node for node, degree in result.graph.degree() if degree == 0)
)

assert result.graph.number_of_edges() == 2
assert result.original_graph.number_of_edges() == 4
```

The score table contains four rows. The two retained links are
`design–engineering` and `engineering–research`, so edge retention is 50%.
`support` remains in the result as an isolated node. The CSV column named
`collaborations` becomes the edge attribute `weight` when loaded.

## Save the choices as a pipeline

Use a pipeline when you want to run the same method and filter again.
The following uses `network` from the first example.

```python
pipeline = (
    nb.pipeline()
    .score("edge_weight", weight="weight")
    .filter("threshold", value=3, operator="greater_equal", drop_isolates=True)
)
result = pipeline.run(network)
assert "support" not in result.graph
```

`compute(network)` runs only the method. `run(network)` also applies the filter
and constructs the resulting graph. For further exploration, see
[how to reuse a score table](../python/select.md#reuse-an-existing-score-table)
or [compare two backbone configurations](../python/compare.md).
