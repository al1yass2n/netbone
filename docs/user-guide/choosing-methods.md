# Choosing Methods

No backbone method is universally best. Choose a method by matching its
assumptions to your network, edge weights, and analysis question. Netbone makes
this explicit by storing method metadata, statistic semantics, and warnings.

Use discovery helpers while exploring:

```python
nb.list_methods()
nb.describe_method("disparity")
```

## Good Starting Points

### Weighted Edge Strength

Use `edge_weight` as a transparent baseline when edge weights already have a
direct interpretation and you want to compare other methods against a simple
threshold or fraction.

Useful filters:

- `threshold`
- `fraction`

### Local Statistical Significance

Use `disparity`, `lans`, or `marginal_likelihood` when you want p-value style
edge statistics and a significance threshold.

Useful filters:

- `significance`
- `fraction` for exploratory ranking

These methods have different null assumptions. Read the method reference before
using p-values as evidence of domain importance.

### Connectivity-Preserving Or Structural Baselines

Use `maximum_spanning_forest`, `primary_linkage`, `multiple_linkage`,
`planar_maximally_filtered_graph`, `h_backbone`, or `gspar` when the workflow
needs a structural or connectivity-oriented backbone.

Useful filters:

- `default`
- `threshold`
- `fraction`, depending on method output semantics

### Shortest-Path And Salience Structure

Use `link_salience`, `edge_betweenness`, or `node_betweenness` when shortest
paths or central bridging positions are relevant to the analysis.

For weighted shortest-path methods, check whether weights represent connection
strengths or distances and choose the method's `distance_transform`
accordingly.

### Node-Target Backbones

Use `node_degree`, `node_strength`, or `node_betweenness` when the target of
selection is nodes rather than edges. Node selections return node-induced
subgraphs.

## Similarity-Based Link Prediction

The `link_prediction` method computes similarity scores on existing edges after
temporarily removing the edge. High-similarity and low-similarity extraction are
filter choices:

```python
high_similarity = (
    nb.pipeline()
    .score("link_prediction", similarity="preferential_attachment")
    .filter("default", direction="higher")
    .run(graph)
)

low_similarity = (
    nb.pipeline()
    .score("link_prediction", similarity="preferential_attachment")
    .filter("default", direction="lower")
    .run(graph)
)
```

On a directed graph, reciprocal arcs are scored separately. Preferential
Attachment uses source outgoing and target incoming connectivity, while
Shortest Path and Local Path use forward source-to-target replacement paths.
See the [Link Prediction method reference](../methods/link_prediction.md) for
the exact directed formulas.

Use `link_prediction_iforest` when the goal is to retain edges whose similarity
profiles are unusual in either direction. It can fit one similarity or combine
several as features, then exposes an anomaly score for ordinary fraction or
threshold filtering. This method requires the optional `ml` extra.

## Compare Before Deciding

A good workflow is to run multiple plausible methods and compare their
retention, connectivity, overlap, and score alignment:

```python
comparison = nb.compare(
    {
        "baseline": baseline_result,
        "disparity": disparity_result,
    }
)

comparison.table()
comparison.pairwise()
comparison.spearman()
```

Sparse output is not automatically better. Treat the backbone as a modeling
choice and report the assumptions, parameters, and structural effects.
