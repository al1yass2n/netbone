# Release notes

## 0.3.0 (unreleased)

Netbone 0.3.0 is a new codebase. It replaces the
[0.2.3 PyPI release](https://pypi.org/project/netbone/0.2.3/), which came
from the earlier GitLab project, so code written for 0.2.3 needs to be
ported. It adds:

- A pipeline API that scores a network, filters the scores, and returns a
  backbone with its tables. See [Extract your first backbone](start/first-backbone.md).
- 20 scoring methods, each with a page that names its source papers. See the
  [method catalog](reference/methods.md).
- Threshold, fraction, significance, and method-default
  [filters](filters/threshold.md), with explicit tie policies.
- [Comparison](python/compare.md) metrics, [parameter sweeps](python/sweep.md),
  and [saved experiments and reports](python/reproduce.md).
- [Temporal aggregation](python/temporal.md) of time-stamped interactions.
- A [local web app](browser/launch.md) that ships with the package and runs
  the same analysis engine.

### Changes since the 0.3.0 source tree was first published

!!! warning "Results can change"
    If you installed Netbone from the repository before this release, these
    changes can alter your results.

**Scores that change**

- Every method that can read weights defaults to `weight="auto"`. A graph
  whose edges all carry `weight` is scored as weighted, and a graph without
  weights is scored as unweighted. Edge Weight, Edge Betweenness, Node
  Betweenness, GLANB, Link Prediction, and Link Prediction Isolation Forest
  used to ignore weights by default, so their scores on weighted graphs
  change. Pass `weight=None` for the old behaviour. See
  [How weights are chosen](reference/methods.md#how-weights-are-chosen).
- Directed LANS compares each arc with the source's outgoing and the target's
  incoming distribution, as Disparity does.
- Disparity defaults to `leaf_policy="zero"`, the same as LANS. Pass
  `leaf_policy="ignore"` for the old behaviour.
- The fraction filter no longer keeps an extra item because of
  floating-point rounding. A fraction of 0.07 of 100 rows keeps 7.
- Multiple Linkage breaks ties the same way at every weight scale.

**New options**

- Disparity and LANS accept `pvalue_aggregation="out"` or `"in"` on directed
  graphs. See [Combining the two ends](methods/disparity.md#combining-the-two-ends).
- Node Strength and Edge Weight support directed graphs. Node Strength takes
  `direction="total"`, `"in"`, or `"out"`.
- `to_undirected` defaults to `weight="auto"` and sums reciprocal weights.
- `describe_method()` returns a `references` list, and reports copy it.
- The web app offers the Holm correction, the seeded random tie policy, and a
  link to each method's paper. `netbone-web --max-upload-mb` sets the largest
  accepted upload.

**Stricter input checks**

- Edge lists must be UTF-8, must have at least one edge row, and may not have
  rows with more values than the header. A trailing delimiter on every row is
  accepted.
- `true`/`false` weights, `inf` weights, and repeated edges are rejected with
  the row numbers involved. Node ids stay as written, so `007` and `7` are two
  nodes.
- A temporal time column must hold only numbers or only dates.

**Fixes**

- Marginal Likelihood and GLANB no longer overflow on very large counts or
  exponents.
- Saving the same sweep twice gives identical bundles, and
  `save_experiment(overwrite=True)` only replaces empty folders or earlier
  Netbone bundles.
- The local web server rejects cross-origin requests, rebound host names, and
  oversized uploads.

See [Troubleshooting](help.md) for the new error messages and what to do
about each.
