import { demoAttachment, demoMode, demoResponse } from "./demo-api";
import type {
  ComparisonResponse,
  ExtractionResponse,
  FilterPreview,
  JsonRecord,
  PreviewResponse,
  ScoreResponse,
  SweepResponse,
  UiSchema,
} from "./types";

async function requestJson<T>(path: string, body?: JsonRecord): Promise<T> {
  if (demoMode) return demoResponse(path, body) as Promise<T>;
  const response = await fetch(path, body === undefined
    ? undefined
    : {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
  const payload = await response.json() as T & { message?: string };
  if (!response.ok) {
    throw new Error(payload.message || `Request failed with status ${response.status}.`);
  }
  return payload;
}

export const api = {
  schema: () => requestJson<UiSchema>("/api/ui-schema"),
  preview: (payload: JsonRecord) => requestJson<PreviewResponse>("/api/preview", payload),
  score: (payload: JsonRecord) => requestJson<ScoreResponse>("/api/score", payload),
  filter: (payload: JsonRecord) => requestJson<ExtractionResponse>("/api/filter", payload),
  filterPreview: (payload: JsonRecord) =>
    requestJson<FilterPreview>("/api/filter-preview", payload),
  compare: (payload: JsonRecord) =>
    requestJson<ComparisonResponse>("/api/compare", payload),
  sweep: (payload: JsonRecord) =>
    requestJson<SweepResponse>("/api/sweep", payload),
};

export async function downloadGraph(
  resultId: string,
  format: "gexf" | "graphml",
  scope: "annotated" | "backbone",
): Promise<void> {
  return downloadAttachment("/api/export", { result_id: resultId, export: { format, scope } }, `netbone-backbone.${format}`);
}

export async function downloadExperiment(resultId: string): Promise<void> {
  return downloadAttachment("/api/export-result", { result_id: resultId, format: "zip" }, "netbone-experiment.zip");
}

export function downloadWorkspaceExperiment(experimentId: string): Promise<void> {
  return downloadAttachment("/api/export-experiment", { experiment_id: experimentId }, "netbone-experiment.zip");
}

async function downloadAttachment(path: string, payload: JsonRecord, fallbackFilename: string): Promise<void> {
  const response = demoMode ? await demoAttachment(path, payload) : await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({})) as { message?: string };
    throw new Error(error.message || `Download failed with status ${response.status}.`);
  }
  const disposition = response.headers.get("Content-Disposition") || "";
  const filename = disposition.match(/filename="([^"]+)"/)?.[1]
    || fallbackFilename;
  triggerDownload(await response.blob(), filename);
}

export function downloadJson(value: unknown, filename: string): void {
  triggerDownload(
    new Blob([`${JSON.stringify(value, null, 2)}\n`], { type: "application/json" }),
    filename,
  );
}

export function downloadCsv(
  records: Array<Record<string, unknown>>,
  filename: string,
  columns = [...new Set(records.flatMap((record) => Object.keys(record)))],
): void {
  const escape = (value: unknown) => {
    const text = value === null || value === undefined ? "" : String(value);
    return /[",\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  };
  const rows = [
    columns.map(escape).join(","),
    ...records.map((record) => columns.map((column) => escape(record[column])).join(",")),
  ];
  triggerDownload(new Blob([`${rows.join("\n")}\n`], { type: "text/csv" }), filename);
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
