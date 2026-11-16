# Method catalog

Choose a method by the structure it measures and by the data it requires.
All entries support simple undirected graphs subject to their attribute
requirements. Directed support is shown below. A node method produces an
induced subgraph after filtering. The other methods select edges.

## Baselines

| Method | Weights | Directed | Suggested selection |
| --- | --- | --- | --- |
| [Edge Weight](../methods/edge_weight.md) | Finite numeric or unit weights | No | Threshold or fraction |

## Paths and neighborhoods

| Method | Weights | Directed | Suggested selection |
| --- | --- | --- | --- |
| [Edge Betweenness](../methods/edge_betweenness.md) | Positive when weighted | No | 10% fraction |
| [Link Salience](../methods/link_salience.md) | Positive or unit weights | Yes | Score ≥ 0.5 |
| [Link Prediction](../methods/link_prediction.md) | Positive when weighted | Yes | 10% fraction with explicit direction |
| [Link Prediction Isolation Forest](../methods/link_prediction_iforest.md) | Positive when weighted | Yes | 10% fraction |
| [GSPAR](../methods/gspar.md) | Weights ignored | No | 10% fraction |

## Statistical methods

| Method | Weights | Directed | Suggested selection |
| --- | --- | --- | --- |
| [Disparity](../methods/disparity.md) | Positive | Yes | Significance |
| [Locally Adaptive Network Sparsification](../methods/lans.md) | Positive | Yes | Significance |
| [Marginal Likelihood](../methods/marginal_likelihood.md) | Positive integer counts | No | Significance |
| [Noise Corrected](../methods/noise_corrected.md) | Positive integer counts | Yes | Score > 1.64 |
| [Globally and Locally Adaptive Network Backbone](../methods/glanb.md) | Positive when weighted | No | Significance |

## Structural selections

| Method | Weights | Directed | Suggested selection |
| --- | --- | --- | --- |
| [Maximum Spanning Forest](../methods/maximum_spanning_forest.md) | Finite numeric or unit weights | No | Selection flag = 1 |
| [Primary Linkage](../methods/primary_linkage.md) | Finite numeric | No | Selection flag = 1 |
| [Multiple Linkage](../methods/multiple_linkage.md) | Non-negative | No | Selection flag = 1 |
| [Planar Maximally Filtered Graph](../methods/planar_maximally_filtered_graph.md) | Finite numeric or unit weights | No | Selection flag = 1 |
| [H-Backbone](../methods/h_backbone.md) | Positive | No | Selection flag = 1 |
| [Doubly Stochastic](../methods/doubly_stochastic.md) | Positive | No | Connected-selection flag = 1 |

## Node measures

| Method | Weights | Directed | Suggested selection |
| --- | --- | --- | --- |
| [Node Degree](../methods/node_degree.md) | Weights ignored | No | 10% fraction |
| [Node Strength](../methods/node_strength.md) | Finite numeric | No | 10% fraction |
| [Node Betweenness](../methods/node_betweenness.md) | Positive when weighted | No | 10% fraction |

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
