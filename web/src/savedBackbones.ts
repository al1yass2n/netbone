import { sentenceCase } from "./labels";
import type { ExtractionResponse, JsonRecord, SavedResult } from "./types";
import { formatPercent } from "./utils";

/** A readable name for a saved backbone, such as "Edge Weight · 10%". */
export function backboneLabel(result: Pick<ExtractionResponse, "extraction">, methodLabel?: string): string {
  const { method, filter } = result.extraction;
  const parameters = result.extraction.filter_parameters as JsonRecord | undefined;
  const name = methodLabel || (typeof method === "string" ? sentenceCase(method) : "Backbone");
  if (filter === "fraction" && typeof parameters?.fraction === "number") {
    return `${name} · ${formatPercent(parameters.fraction)}`;
  }
  if (filter === "significance" && typeof parameters?.alpha === "number") {
    return `${name} · p < ${Number(parameters.alpha.toPrecision(3))}`;
  }
  if (filter === "threshold" && typeof parameters?.value === "number") {
    return `${name} · cutoff ${Number(parameters.value.toPrecision(3))}`;
  }
  return name;
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
