import type { ExtractionResponse, JsonRecord, SavedResult } from "./types";

const methodAbbreviations: Record<string, string> = {
  disparity: "DF",
  doubly_stochastic: "DS",
  edge_betweenness: "EB",
  edge_weight: "EW",
  glanb: "GLANB",
  gspar: "GSPAR",
  h_backbone: "HB",
  lans: "LANS",
  link_prediction: "LP",
  link_prediction_iforest: "LP-IF",
  link_salience: "LS",
  marginal_likelihood: "ML",
  noise_corrected: "NC",
  maximum_spanning_forest: "MSF",
  multiple_linkage: "MultiL",
  node_betweenness: "NB",
  node_degree: "ND",
  node_strength: "NS",
  planar_maximally_filtered_graph: "PMFG",
  primary_linkage: "PL",
};

export function shortBackboneLabel(result: ExtractionResponse): string {
  const { method, filter } = result.extraction;
  const parameters = result.extraction.filter_parameters as JsonRecord | undefined;
  const prefix = typeof method === "string" ? methodAbbreviations[method] ?? method.slice(0, 6).toUpperCase() : "Backbone";
  if (filter === "fraction" && typeof parameters?.fraction === "number") {
    return `${prefix} ${Number((parameters.fraction * 100).toPrecision(3))}%`;
  }
  if (filter === "significance" && typeof parameters?.alpha === "number") {
    return `${prefix} α${Number(parameters.alpha.toPrecision(3))}`;
  }
  if (filter === "threshold" && typeof parameters?.value === "number") {
    return `${prefix} cut ${Number(parameters.value.toPrecision(3))}`;
  }
  return prefix;
}

export function uniqueResultLabel(label: string, saved: SavedResult[], resultId: string): string {
  const existing = new Set(saved.filter((item) => item.resultId !== resultId).map((item) => item.label.toLowerCase()));
  let candidate = label;
  for (let suffix = 2; existing.has(candidate.toLowerCase()); suffix += 1) {
    const ending = ` (${suffix})`;
    candidate = `${label.slice(0, 120 - ending.length).trimEnd()}${ending}`;
  }
  return candidate;
}

export function moveSavedBackbone(saved: SavedResult[], resultId: string, destination: number): SavedResult[] {
  const index = saved.findIndex((item) => item.resultId === resultId);
  const item = saved[index];
  if (!item || index === destination || destination < 0 || destination >= saved.length) return saved;
  const reordered = [...saved];
  reordered.splice(index, 1);
  reordered.splice(destination, 0, item);
  return reordered;
}
