# Link Prediction Backbone Framework

`link_prediction` implements the 2025 link-prediction perspective on backbone
extraction as a neutral edge-similarity scorer. High-similarity and
low-similarity backbones are selected by the filter, not by the scoring method.

## Summary

- **Name:** `link_prediction`
- **Target:** edge
- **Output type:** `score`
- **Primary statistic:** `link_prediction_similarity`
- **Preferred direction:** `higher`
- **Directed input:** supported with ordered, forward-path semantics
- **Weighted input:** optional through `weight="..."`; omitted weights keep the
  unweighted formulas
- **Default filter:** `fraction`, `fraction=0.1`, explicit `direction` required
- **Supported similarities:** `preferential_attachment`, `shortest_path`,
  `local_path`
- **Weight exponent:** `weight_alpha`, default `1.0`
- **Distance transform:** `distance_transform`, default `inverse`

## Definition

For each existing edge `(u, v)`, Netbone temporarily removes the edge, computes
the requested similarity between `u` and `v`, then restores the edge in the
working copy. The original graph is not mutated.

When `weight` is omitted, every edge has unit weight and the formulas below are
topological. When `weight` is provided, weights must be finite positive numeric
values. Netbone uses the effective weight `weight ** weight_alpha`; setting
`weight_alpha=0.0` makes every positive configured weight contribute as `1.0`.

`distance_transform` defines how weighted values are interpreted:

- `inverse`: weights are connection strengths. Netbone uses
  `weight ** weight_alpha` as the connection strength and its reciprocal as the
  path distance.
- `identity`: weights are already path distances. Netbone uses
  `weight ** weight_alpha` as the path distance and its reciprocal as the
  connection strength.

Preferential Attachment and Local Path use connection strengths. Shortest Path
uses path distances. This keeps distance-valued weights from being treated as
large similarities in Local Path.

Preferential Attachment:

```text
similarity(u, v) = degree(u) * degree(v)
```

With `weight`, degree is replaced by the endpoint strength in the edge-removed
graph:

```text
similarity(u, v) = strength(u) * strength(v)
```

Shortest Path:

```text
similarity(u, v) = 1 / shortest_path_length(u, v)
```

With `weight`, shortest paths use the path distances implied by
`distance_transform`.

If removing the edge disconnects `u` and `v`, the shortest-path similarity is
`0.0` and `link_prediction_disconnected` is `True`.

Local Path:

```text
similarity(u, v) = paths_len_2(u, v) + epsilon * paths_len_3(u, v)
```

where `epsilon` defaults to `1.0`.

With `weight`, the length-2 and length-3 terms are connection-strength path
products, equivalent to using powers of the derived weighted adjacency matrix.

## Directed Graphs

For a directed arc `u -> v`, Netbone removes only that ordered arc. A reciprocal
arc `v -> u` remains in the working graph and receives its own independent
score. The directed definitions are:

```text
preferential_attachment(u -> v) = out_degree(u) * in_degree(v)
shortest_path(u -> v) = 1 / forward_shortest_path_length(u, v)
local_path(u -> v) = forward_paths_len_2(u, v)
                     + epsilon * forward_paths_len_3(u, v)
```

The weighted Preferential Attachment variant uses source out-strength times
target in-strength. Directed Shortest Path follows arc orientation from source
to target. Directed Local Path counts only sequences `u -> x -> v` and
`u -> x -> y -> v`; the weighted terms multiply connection strengths along
those same ordered paths.

These orientation-specific rules are Netbone's explicit directed extension of
the published framework. They answer whether the rest of the directed network
supports the observed arc in its own direction. The result includes an
interpretation warning so saved reports and exports retain that distinction.

## Weighted Usage

```python
weighted_high_similarity = (
    nb.pipeline()
    .score(
        "link_prediction",
        similarity="local_path",
        weight="weight",
        weight_alpha=1.0,
        distance_transform="inverse",
    )
    .filter("default", direction="higher")
)
```

Use `distance_transform="identity"` when the configured edge attribute is
already a path distance:

```python
weighted_distance_similarity = (
    nb.pipeline()
    .score(
        "link_prediction",
        similarity="shortest_path",
        weight="distance",
        distance_transform="identity",
    )
    .filter("default", direction="higher")
)
```

## Extraction

Use the `fraction` filter's `direction` parameter to choose the backbone type:

```python
high_similarity = (
    nb.pipeline()
    .score("link_prediction", similarity="preferential_attachment")
    .filter("default", direction="higher")
)

low_similarity = (
    nb.pipeline()
    .score("link_prediction", similarity="preferential_attachment")
    .filter("default", direction="lower")
)
```

In the guided web app, **high similarity** and **low similarity** define this
extraction direction without changing the computed similarity scores. A
fraction filter consequently keeps the highest or lowest requested fraction.
For a threshold filter, high similarity permits only `>` and `>=`, while low
similarity permits only `<` and `<=`. The web control presents these as strict
or inclusive cutoff choices. Changing the backbone direction does not require
the similarity scores to be computed again.

The default filter keeps retained fraction `0.1`. Calling `.filter("default")`
without `direction` raises `ConfigurationError` for this method.

## Output

- `link_prediction_similarity_method`
- `link_prediction_edge_weight`
- `link_prediction_edge_effective_weight`
- `link_prediction_edge_strength`
- `link_prediction_edge_distance`
- `link_prediction_similarity`
- `link_prediction_source_degree`
- `link_prediction_target_degree`
- `link_prediction_source_strength`
- `link_prediction_target_strength`
- `link_prediction_shortest_path_length`
- `link_prediction_disconnected`
- `link_prediction_paths_length_2`
- `link_prediction_paths_length_3`
- `link_prediction_weighted_paths_length_2`
- `link_prediction_weighted_paths_length_3`

For directed Preferential Attachment,
`link_prediction_source_degree`/`source_strength` mean outgoing connectivity,
while `link_prediction_target_degree`/`target_strength` mean incoming
connectivity.

## Reference

Link prediction perspective on network backbone extraction. Applied Network
Science (2025). DOI: `10.1007/s41109-025-00705-y`.
