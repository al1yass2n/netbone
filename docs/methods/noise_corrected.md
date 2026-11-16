# Noise Corrected

`noise_corrected` scores edges using the Noise Corrected backbone of
Michele Coscia and Frank M. H. Neffke.

- **Target:** edges in a simple directed or undirected graph.
- **Input:** positive integer interaction counts in the selected weight
  attribute. Remove zero-weight edges before scoring.
- **Primary statistic:** `noise_corrected_z`, the transformed lift divided
  by its estimated standard deviation. Higher is stronger.
- **Default filter:** keep edges with `noise_corrected_z > 1.64`.

```python
import netbone as nb

result = (
    nb.pipeline().score("noise_corrected", weight="count").filter("default").run(graph)
)
```

To use another threshold, replace `.filter("default")` with
`.filter("threshold", value=2.32, operator="greater")`. The cutoff is the
number of standard deviations above the null expectation, in the same units
as the paper's δ. It is applied strictly.

The null expectation combines the source's outgoing and the target's
incoming totals. An undirected edge contributes its weight in both
directions when calculating these totals, as in the authors' symmetric input
table. Netbone emits one result row per undirected edge. It preserves
reciprocal arcs as separate rows for directed input.

The other output columns are `noise_corrected_score` (transformed lift) and
`noise_corrected_stddev` (estimated standard deviation). When a single source
or target accounts for every interaction, the reference has undefined
uncertainty. Netbone reports missing uncertainty and a warning, and assigns
those edges a standardized score of zero so the default filter excludes
them. A nonzero lift with exactly zero estimated deviation is represented by
the extreme finite score of the corresponding sign.

The default follows the authors' Python 3 implementation of the Bayesian
variance and delta method, including the beta-prior expression and the use of
the global count in the derivative of κ. Those two expressions differ from
their printed counterparts in the preprint. The authors' separate binomial
CDF option is outside this implementation. The standardized score does not
represent a p-value.

[ICDE paper](https://doi.org/10.1109/ICDE.2017.100) ·
[Open preprint](https://arxiv.org/abs/1701.07336) ·
[Authors' code](https://www.michelecoscia.com/?page_id=287)
