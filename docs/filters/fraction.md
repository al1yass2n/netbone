# Fraction Filter

`fraction` selects the top retained fraction of a method result using the
method's declared preferred direction, unless an explicit ranking direction is
provided.

## Summary

- **Name:** `fraction`
- **Input:** `MethodResult`
- **Output:** `Selection`
- **Default statistic:** method `primary_statistic`
- **Default tie policy:** `include_all_ties`
- **Default isolate behavior:** keep isolates

## Parameters

- `fraction`: requested retained fraction from `0` to `1`.
- `statistic`: optional statistic column. Defaults to the method result's
  primary statistic.
- `direction`: optional ranking override, either `higher` or `lower`. When
  omitted, the method result's preferred direction is used.
- `tie_policy`: tie handling at the cutoff.
- `random_seed`: required integer seed when `tie_policy="random_seeded"`.
- `drop_isolates`: whether isolated nodes should be removed after edge
  filtering. Defaults to `False`.

## Tie Policies

- `include_all_ties`: include every item tied at the cutoff and report the
  actual retained count.
- `exact_stable`: keep exactly the requested count, breaking ties by stable
  node or edge id and warning when ties are truncated.
- `raise_on_tie`: raise `ConfigurationError` when ties affect the cutoff.
- `random_seeded`: keep exactly the requested count by choosing among cutoff
  ties with a reproducible random seed. The selection records the seed and
  affected tied ids.

## Behavior

For methods where higher values are preferred, such as `edge_weight`, the
filter keeps the largest values. For methods where lower values are preferred,
such as p-value methods, the filter keeps the smallest values.

Some neutral similarity methods require an explicit `direction` because the
same score can define different backbone semantics. For example,
`link_prediction` uses `direction="higher"` for high-similarity backbones and
`direction="lower"` for low-similarity backbones.
