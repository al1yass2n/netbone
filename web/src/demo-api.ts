import type { ComparisonResponse, ExtractionResponse, FilterPreview, JsonRecord, JsonValue, PreviewResponse, ScoreResponse, UiSchema } from "./types";

export const demoMode = import.meta.env.MODE === "demo";

interface DemoRun {
  preview: FilterPreview;
  result: ExtractionResponse;
}

interface DemoData {
  schema: UiSchema;
  graphml: string;
  preview: PreviewResponse;
  scores: Record<string, ScoreResponse>;
  runs: Record<string, DemoRun>;
  baseline: string[];
  comparisons: string[];
}

let data: Promise<DemoData> | undefined;

export function loadDemo(): Promise<DemoData> {
  return data ??= staticJson<DemoData>("snapshot.json");
}

async function staticJson<T>(path: string): Promise<T> {
  const response = await fetch(demoAsset(path));
  if (!response.ok) throw new Error("The Netbone demo files could not be loaded.");
  return response.json() as Promise<T>;
}

function demoAsset(path: string): URL {
  return new URL(`data/${path}`, document.baseURI);
}

function record(value: JsonValue | undefined): JsonRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

export async function demoResponse(path: string, payload?: JsonRecord): Promise<unknown> {
  const snapshot = await loadDemo();
  const guided = record(payload?.guided);
  switch (path) {
    case "/api/ui-schema":
      return snapshot.schema;
    case "/api/preview":
      return snapshot.preview;
    case "/api/score": {
      const score = snapshot.scores[String(guided.method)];
      if (score) return score;
      break;
    }
    case "/api/filter-preview":
    case "/api/filter": {
      const fraction = Number(record(guided.controls).fraction);
      const run = snapshot.runs[`${guided.method}:${fraction}`];
      if (run && guided.filter === "fraction" && run.result.score_id === payload?.score_id) {
        return path === "/api/filter" ? run.result : run.preview;
      }
      break;
    }
    case "/api/compare": {
      const entries = payload?.results;
      if (!Array.isArray(entries)) break;
      const key = entries.map((entry) => String(record(entry).result_id)).sort().join("_");
      if (snapshot.comparisons.includes(key)) return staticJson<ComparisonResponse>(`compare/${key}.json`);
      break;
    }
  }
  throw new Error("Choose one of the precomputed settings in the demo.");
}

export async function demoAttachment(path: string, payload: JsonRecord): Promise<Response> {
  const snapshot = await loadDemo();
  const resultId = payload.result_id;
  const experimentId = payload.experiment_id;
  if (path === "/api/export-experiment" && typeof experimentId === "string" && snapshot.comparisons.includes(experimentId)) {
    return fetch(demoAsset(`compare/${experimentId}.zip`));
  }
  if (typeof resultId === "string" && Object.values(snapshot.runs).some((run) => run.result.result_id === resultId)) {
    if (path === "/api/export-result") return fetch(demoAsset(`runs/${resultId}/experiment.zip`));
    if (path === "/api/export") {
      const { format, scope } = record(payload.export);
      if ((scope === "annotated" || scope === "backbone") && (format === "graphml" || format === "gexf")) {
        return fetch(demoAsset(`runs/${resultId}/${scope}.${format}`));
      }
    }
  }
  throw new Error("This download is unavailable for the demo configuration.");
}
