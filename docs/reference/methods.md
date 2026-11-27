# Method catalog

Choose a method by the structure it measures and by the data it requires.
All entries support simple undirected graphs subject to their attribute
requirements. Directed support is shown below. A node method produces an
induced subgraph after filtering. The other methods select edges.

## Baselines

| Method | Weights | Directed | Suggested selection | Source |
| --- | --- | --- | --- | --- |
| [Edge Weight](../methods/edge_weight.md) | Finite numeric or unit weights | Yes | Threshold or fraction | Baseline |

## Paths and neighborhoods

| Method | Weights | Directed | Suggested selection | Source |
| --- | --- | --- | --- | --- |
| [Edge Betweenness](../methods/edge_betweenness.md) | Positive when weighted | No | 10% fraction | [Girvan & Newman 2002](https://doi.org/10.1073/pnas.122653799) |
| [Link Salience](../methods/link_salience.md) | Positive or unit weights | Yes | Score ≥ 0.5 | [Grady et al. 2012](https://doi.org/10.1038/ncomms1847) |
| [Link Prediction](../methods/link_prediction.md) | Positive when weighted | Yes | 10% fraction with explicit direction | [Yassin et al. 2025](https://doi.org/10.1007/s41109-025-00705-y) |
| [Link Prediction Isolation Forest](../methods/link_prediction_iforest.md) | Positive when weighted | Yes | 10% fraction | [Yassin et al. 2025](https://doi.org/10.1007/978-3-031-92898-7_13) |
| [GSPAR](../methods/gspar.md) | Weights ignored | No | 10% fraction | [Satuluri et al. 2011](https://doi.org/10.1145/1989323.1989399) |

## Statistical methods

| Method | Weights | Directed | Suggested selection | Source |
| --- | --- | --- | --- | --- |
| [Disparity](../methods/disparity.md) | Positive | Yes | Significance | [Serrano et al. 2009](https://doi.org/10.1073/pnas.0808904106) |
| [Locally Adaptive Network Sparsification](../methods/lans.md) | Positive | Yes | Significance | [Foti et al. 2011](https://doi.org/10.1371/journal.pone.0016431) |
| [Marginal Likelihood](../methods/marginal_likelihood.md) | Positive integer counts | No | Significance | [Dianati 2016](https://doi.org/10.1103/PhysRevE.93.012304) |
| [Noise Corrected](../methods/noise_corrected.md) | Positive integer counts | Yes | Score > 1.64 | [Coscia & Neffke 2017](https://doi.org/10.1109/ICDE.2017.100) |
| [Globally and Locally Adaptive Network Backbone](../methods/glanb.md) | Positive when weighted | No | Significance | [Zhang et al. 2014](https://doi.org/10.1371/journal.pone.0100428) |

## Structural selections

| Method | Weights | Directed | Suggested selection | Source |
| --- | --- | --- | --- | --- |
| [Maximum Spanning Forest](../methods/maximum_spanning_forest.md) | Finite numeric or unit weights | No | Selection flag = 1 | [Kruskal 1956](https://doi.org/10.1090/S0002-9939-1956-0078686-7) |
| [Primary Linkage](../methods/primary_linkage.md) | Finite numeric | No | Selection flag = 1 | [Nystuen & Dacey 1961](https://doi.org/10.1111/j.1435-5597.1961.tb01769.x) |
| [Multiple Linkage](../methods/multiple_linkage.md) | Non-negative | No | Selection flag = 1 | [Van Nuffel 2007](https://doi.org/10.1080/00343400701281808) |
| [Planar Maximally Filtered Graph](../methods/planar_maximally_filtered_graph.md) | Finite numeric or unit weights | No | Selection flag = 1 | [Tumminello et al. 2005](https://doi.org/10.1073/pnas.0500298102) |
| [H-Backbone](../methods/h_backbone.md) | Positive | No | Selection flag = 1 | [Zhang et al. 2018](https://doi.org/10.1038/s41598-018-32430-1) |
| [Doubly Stochastic](../methods/doubly_stochastic.md) | Positive | No | Connected-selection flag = 1 | [Slater 2009](https://doi.org/10.1073/pnas.0904725106) |

## Node measures

| Method | Weights | Directed | Suggested selection | Source |
| --- | --- | --- | --- | --- |
| [Node Degree](../methods/node_degree.md) | Weights ignored | No | 10% fraction | [Freeman 1978](https://doi.org/10.1016/0378-8733(78)90021-7) |
| [Node Strength](../methods/node_strength.md) | Finite numeric | Yes | 10% fraction | [Barrat et al. 2004](https://doi.org/10.1073/pnas.0400087101) |
| [Node Betweenness](../methods/node_betweenness.md) | Positive when weighted | No | 10% fraction | [Freeman 1977](https://doi.org/10.2307/3033543) |

## How weights are chosen

Every method that can read weights defaults to `weight="auto"`:

- If every edge has a `weight` attribute, the method uses it.
- If no edge has one, methods that can run unweighted use hop counts or equal
  weights, and methods that need weights raise an error that says so.
- If only some edges have it, the method raises an error instead of guessing.
  Fill in the missing values, pass `weight=None`, or name an attribute.

Pass `weight=None` to ignore weights, or `weight="duration"` to use another
attribute. The resolved value is recorded in `result.parameters["weight"]`, so
saved results show what was used. When auto picks weights for a shortest-path
method, a warning reminds you that `distance_transform="inverse"` reads larger
weights as stronger, closer ties. Pass `distance_transform="identity"` if
larger weights mean longer or costlier links. `nb.describe_method(name)` reports
`weight_mode` as `"required"`, `"optional"`, or `"ignored"`. Methods that
ignore weights, such as GSPAR and Node Degree, still accept `weight=None` and
`weight="auto"`, so one loop can pass the same weight to every method. Naming
an attribute there records a warning in `result.warnings` that it has no
effect.

The 10% defaults use [fraction filtering](../filters/fraction.md), which
can retain more when scores tie. Significance defaults use alpha 0.05 with
correction set to `"none"`. Check the individual method page before choosing
a cutoff or reporting a statistical claim.

## Try a method

The reference examples use this simple weighted graph. Run this block first,
then run the block on a method page.

```python
import networkx as nx
import netbone as nb

graph = nx.Graph()
graph.add_weighted_edges_from(
    [("A", "B", 8), ("A", "C", 3), ("B", "C", 5), ("C", "D", 2)]
)
```

Use `nb.list_methods()` to list registered names and
`nb.describe_method(name)` to inspect metadata in Python.
