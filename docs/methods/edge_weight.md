# Edge Weight

Keeps the links with the largest observed weights. It is the baseline the
other methods are compared against.
{: .lede }

<dl class="method-facts">
<div><dt>Registered name</dt><dd><code>edge_weight</code></dd></div>
<div><dt>Scores</dt><dd>Edges</dd></div>
<div><dt>Statistic</dt><dd><code>score</code>, higher is stronger</dd></div>
<div><dt>Directed graphs</dt><dd>Supported</dd></div>
<div><dt>Weights</dt><dd>Optional, finite numbers</dd></div>
<div><dt>Suggested filter</dt><dd>Threshold or fraction</dd></div>
</dl>

## How it works

The score of an edge is the value of its weight attribute. Directed arcs
keep their own weights. On an unweighted graph, or with `weight=None`, every
edge scores 1.0, so the ranking reduces to tie handling.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `weight` | `"auto"` | Edge attribute to read. `"auto"` uses `weight` when every edge has it and runs unweighted otherwise; `None` always runs unweighted. See [how weights are chosen](../reference/methods.md#how-weights-are-chosen). |

## Output columns

| Column | Meaning |
| --- | --- |
| `score` | The edge weight, or 1.0 when unweighted. |

Every row also has `edge_id`, `source`, and `target`, plus Netbone's internal
`source_id` and `target_id`.

## Cost

Linear in the number of edges.

## Run the method

Use the [sample graph](../reference/methods.md#try-a-method) or substitute a
compatible graph of your own.

```python
pipeline = nb.pipeline().score("edge_weight", weight="weight")
backbone = pipeline.filter("threshold", value=5, operator="greater_equal").run(graph)
print(backbone.summary())
```

## References

Edge Weight is a baseline that ranks edges by their own weight, so it has no
single source paper.
