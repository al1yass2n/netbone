import type { JsonRecord, SweepResponse } from "./types";

export interface SweepPlotRow {
  runId: number;
  name: string;
  runLabel: string;
  setup: string;
  series: string;
  x: number | null;
  y: number | null;
  status: string;
  explanation: string;
}

function sweepSetupName(result: SweepResponse, run: JsonRecord): string {
  const name = String(run.pipeline_name ?? "");
  return (result.setup_names[name] ?? name) || `Run ${run.run_id}`;
}

function runSettings(run: JsonRecord): Array<[string, string, unknown]> {
  const varied = run.varied_parameters;
  if (!varied || typeof varied !== "object" || Array.isArray(varied)) return [];
  return ["method", "filter"].flatMap((scope) => {
    const group = varied[`${scope}_parameters`];
    if (!group || typeof group !== "object" || Array.isArray(group)) return [];
    return Object.entries(group).map(([name, value]): [string, string, unknown] => [scope, name, value]);
  });
}

const fractionFormat = new Intl.NumberFormat("en", { style: "percent", maximumSignificantDigits: 16 });

export function sweepRunLabels(result: SweepResponse): Map<number, string> {
  const runs = result.runs.map((run) => ({ id: Number(run.run_id), setup: sweepSetupName(result, run), settings: runSettings(run) }));
  const options = new Map<string, Set<string>>();
  const optionKey = (setup: string, scope: string, name: string) => JSON.stringify([setup, scope, name]);
  for (const { setup, settings } of runs) {
    for (const [scope, name, value] of settings) {
      const key = optionKey(setup, scope, name);
      const values = options.get(key) ?? new Set<string>();
      values.add(JSON.stringify(value));
      options.set(key, values);
    }
  }
  return new Map(runs.map(({ id, setup, settings }) => {
    const changing = settings.filter(([scope, name]) => (options.get(optionKey(setup, scope, name))?.size ?? 0) > 1);
    const suffix = changing.map(([scope, name, value]) => {
      const fraction = scope === "filter" && name === "fraction";
      const label = fraction ? "retained fraction"
        : name === "pvalue_aggregation" ? "endpoint p-value"
          : name.replaceAll("_", " ");
      const ambiguous = changing.some(([otherScope, otherName]) => otherScope !== scope && otherName === name);
      const formatted = fraction && typeof value === "number" ? fractionFormat.format(value)
        : typeof value === "string" ? value : JSON.stringify(value);
      return `${ambiguous ? `${scope} ` : ""}${label} = ${formatted}`;
    });
    return [id, [setup, ...suffix].join(" · ")];
  }));
}

export function numericSweepParameters(runs: JsonRecord[]): string[] {
  const values = new Map<string, Set<number>>();
  for (const run of runs) {
    for (const [name, value] of Object.entries(parameters(run))) {
      if (!values.has(name)) values.set(name, new Set());
      values.get(name)?.add(value);
    }
  }
  return [...values].filter(([, options]) => options.size > 1).map(([name]) => name);
}

export function trajectoryRows(result: SweepResponse, parameter: string, metric: string, setup = "all"): SweepPlotRow[] {
  const metrics = metricLookup(result.metrics);
  const labels = sweepRunLabels(result);
  return result.runs.flatMap((run) => {
    const runId = Number(run.run_id);
    const name = String(run.pipeline_name);
    const setupName = result.setup_names[name] || name;
    const values = parameters(run);
    const x = values[parameter];
    if ((setup !== "all" && setup !== setupName) || x === undefined) return [];
    const metricRow = metrics.get(`${runId}\u0000${metric}`);
    const y = validMetric(metricRow);
    const other = Object.entries(values).filter(([key]) => key !== parameter);
    const context = other.map(([key, value]) => `${key}=${value}`).join(", ");
    const series = context ? `${setupName} · ${context}` : setupName;
    return [{
      runId, name, runLabel: labels.get(runId) ?? setupName, setup: setupName, series, x, y,
      status: y === null && metricRow?.status === "ok" ? "undefined" : String(metricRow?.status || (run.status === "failed" ? "failed" : "undefined")),
      explanation: String(metricRow?.explanation || run.explanation || (y === null ? "Metric unavailable for this run." : "")),
    }];
  });
}

export function tradeoffRows(result: SweepResponse, xMetric: string, yMetric: string, setup = "all"): SweepPlotRow[] {
  const metrics = metricLookup(result.metrics);
  const labels = sweepRunLabels(result);
  return result.runs.flatMap((run) => {
    const runId = Number(run.run_id);
    const name = String(run.pipeline_name);
    const setupName = result.setup_names[name] || name;
    if (setup !== "all" && setup !== setupName) return [];
    const xRow = metrics.get(`${runId}\u0000${xMetric}`);
    const yRow = metrics.get(`${runId}\u0000${yMetric}`);
    const x = validMetric(xRow);
    const y = validMetric(yRow);
    const unavailable = [xRow, yRow].filter((row) => !row || validMetric(row) === null);
    return [{
      runId, name, runLabel: labels.get(runId) ?? setupName, setup: setupName, series: setupName, x, y,
      status: unavailable.length ? unavailable.map((row) => String(row?.status || "unavailable")).join(" / ") : "ok",
      explanation: unavailable.map((row) => String(row?.explanation || "Metric unavailable.")).join("; "),
    }];
  });
}

function parameters(run: JsonRecord): Record<string, number> {
  const varied = run.varied_parameters;
  if (!varied || typeof varied !== "object" || Array.isArray(varied)) return {};
  const result: Record<string, number> = {};
  for (const kind of ["method_parameters", "filter_parameters"]) {
    const group = varied[kind];
    if (!group || typeof group !== "object" || Array.isArray(group)) continue;
    for (const [name, value] of Object.entries(group)) {
      if (typeof value === "number" && Number.isFinite(value)) {
        result[`${kind === "method_parameters" ? "method" : "filter"}.${name}`] = value;
      }
    }
  }
  return result;
}

function metricLookup(rows: JsonRecord[]): Map<string, JsonRecord> {
  return new Map(rows.filter((row) => row.metric !== null).map((row) => [`${row.run_id}\u0000${row.metric}`, row]));
}

function validMetric(row: JsonRecord | undefined): number | null {
  return row?.status === "ok" && typeof row.value === "number" && Number.isFinite(row.value)
    ? row.value : null;
}
