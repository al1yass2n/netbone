import type { MethodSpec } from "./types";

// Goals describe the method's preferred direction and recommended extraction.
const methodGoals = {
  disparity: ["Keep unusually strong ties around each node", "Edges that account for an unusually large share of weight at an endpoint under Disparity’s null model."],
  doubly_stochastic: ["Keep strong ties after balancing node activity", "Edges that remain relatively strong after balancing the weight distribution across nodes."],
  edge_betweenness: ["Keep edges that carry many shortest routes between pairs of nodes", "Edges that lie on a large share of shortest routes between node pairs."],
  edge_weight: ["Keep the edges with the largest weights", "Edges with large original weights, using the cutoff or fraction you choose."],
  glanb: ["Keep edges that carry more shortest paths than expected locally", "Edges that appear unusually often on shortest paths from an endpoint, accounting for that endpoint’s number of connections."],
  gspar: ["Keep ties between nodes that share many neighbors", "Edges whose endpoints have high neighborhood overlap relative to their combined neighborhoods."],
  h_backbone: ["Keep strong ties and bridges between parts of the network", "Edges selected for their strength or their role in connecting otherwise separated parts of the network."],
  lans: ["Keep ties that stand out in each node’s observed weight distribution", "Edges whose share of weight is unusually large compared with the observed shares of an endpoint’s other edges."],
  link_prediction: ["Keep existing ties supported by the surrounding network", "In high-similarity mode, existing edges with strong structural support under the chosen similarity measure. Low-similarity mode favors weakly supported edges."],
  link_prediction_iforest: ["Keep edges with unusual similarity patterns", "Edges whose similarity values are unusual compared with other edges. The values can be high, low, or unusual in combination."],
  link_salience: ["Keep edges used in shortest-path trees from many starting nodes", "Edges that appear in shortest-path trees rooted at many different nodes."],
  marginal_likelihood: ["Keep ties with more activity than expected from their endpoints’ totals", "Edges carrying more activity than expected given the total activity at their endpoints."],
  noise_corrected: ["Keep unexpectedly strong ties after accounting for uncertainty", "Edges whose excess interaction counts stand out relative to their estimated uncertainty."],
  maximum_spanning_forest: ["Preserve connectivity without redundant cycles", "The strongest available links that form a cycle-free skeleton of each original connected component, with the recommended filter."],
  multiple_linkage: ["Keep several of each node’s strongest ties", "Edges included in the locally strongest set of at least one endpoint, as determined by the method’s settings."],
  node_betweenness: ["Keep nodes that lie on many shortest routes between other nodes", "Nodes that lie on a large share of shortest routes between other node pairs."],
  node_degree: ["Find nodes with the most connections", "Nodes with many direct connections in the original network."],
  node_strength: ["Keep nodes with the greatest total weight across their ties", "Nodes with high total weight across their direct connections in the original network."],
  planar_maximally_filtered_graph: ["Keep strong ties in a network that can be drawn without crossings", "High-weight edges accepted while the retained graph can still be drawn without crossings, with the recommended filter."],
  primary_linkage: ["Keep each node’s strongest tie", "Edges chosen as the strongest tie by at least one endpoint. Each node chooses one edge, with ties broken in a stable order."],
} as const;

export function methodGoalDetails(method: MethodSpec) {
  if (!Object.hasOwn(methodGoals, method.name)) return undefined;
  const [goal, retained] = methodGoals[method.name as keyof typeof methodGoals];
  return method.target === "node"
    ? { goal, nodes: retained, edges: "All original edges between retained nodes, with their original weights." }
    : { goal, edges: retained, nodes: "Endpoints of retained edges. Other original nodes remain as isolates unless the filter drops isolated nodes." };
}
