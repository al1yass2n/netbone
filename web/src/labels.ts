import type { ControlSpec, FilterName, JsonRecord, JsonValue, UiSchema } from "./types";
import { formatPercent, formatValue } from "./utils";

/*
 * One name for each idea. Every screen takes its filter, setting and metric
 * names from here, so the same thing is never called two different names.
 */

const FILTER_LABELS: Record<FilterName, string> = {
  default: "Method default",
  fraction: "Keep a fraction",
  significance: "Significance",
  threshold: "Score cutoff",
};

export function filterLabel(name: string): string {
  return FILTER_LABELS[name as FilterName] ?? sentenceCase(name);
}

export function sentenceCase(value: string): string {
  const text = value.replaceAll("_", " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

const METRICS: Record<string, { label: string; description: string }> = {
  connected_component_count: {
    label: "Connected components",
    description: "Groups of linked nodes in each backbone. Each isolated node counts as its own group.",
  },
  edge_count: { label: "Backbone edges", description: "Edges kept in each backbone." },
  edge_retention: { label: "Edge retention", description: "Share of the original edges kept." },
  isolated_node_count: { label: "Isolated nodes", description: "Nodes left without a backbone edge." },
  node_count: { label: "Output nodes", description: "Nodes in each backbone, including isolated ones." },
  node_retention: { label: "Node retention", description: "Share of the original nodes kept." },
  strongly_connected_component_count: { label: "Strong components", description: "Groups in a directed backbone where every node can reach every other." },
  weakly_connected_component_count: { label: "Weak components", description: "Connected groups after ignoring direction." },
  weight_retention: { label: "Weight retention", description: "Share of the total original edge weight kept." },
  edge_jaccard: { label: "Shared-edge similarity", description: "Shared edges divided by all distinct backbone edges." },
  edge_overlap: { label: "Shared edges", description: "Backbone edges the two results have in common." },
  edge_overlap_coefficient: { label: "Edge overlap coefficient", description: "Shared edges relative to the smaller backbone." },
  node_jaccard: { label: "Shared-node similarity", description: "Shared nodes divided by all distinct output nodes." },
  node_overlap: { label: "Shared nodes", description: "Output nodes the two results have in common." },
  node_overlap_coefficient: { label: "Node overlap coefficient", description: "Shared nodes relative to the smaller backbone." },
  score_spearman: { label: "Importance-rank agreement", description: "How closely the two importance rankings agree, from -1 to 1." },
};

export function metricLabel(name: string): string {
  return METRICS[name]?.label ?? sentenceCase(name);
}

export function metricDescription(name: string): string {
  return METRICS[name]?.description ?? "Backbone measurement.";
}

export function isRatioMetric(name: string): boolean {
  return name.includes("retention") || name.includes("jaccard") || name.includes("coefficient");
}

/** Plain value for a measurement: percentages for shares, two decimals for agreement, whole numbers for counts. */
export function formatMetric(name: string, value: unknown): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  if (isRatioMetric(name)) return formatPercent(value);
  if (name === "score_spearman") return value.toFixed(2);
  return Number.isInteger(value) ? String(value) : String(Number(value.toPrecision(3)));
}

export interface SettingRow {
  label: string;
  value: string;
}

const PARAMETER_LABELS: Record<string, string> = {
  weight: "Weight column",
  value: "Cutoff",
  fraction: "Retained fraction",
};

/** Settings in plain words: the control's own label, option labels, Yes/No and percentages. */
export function settingRows(parameters: JsonValue | undefined, controls: ControlSpec[] = []): SettingRow[] {
  const entries = parameters && typeof parameters === "object" && !Array.isArray(parameters) ? Object.entries(parameters) : [];
  return entries.map(([key, value]) => {
    const control = controls.find((item) => item.name === key || (key === "value" && item.name === "threshold_value"));
    const label = key === "value" ? PARAMETER_LABELS.value! : control?.label ?? PARAMETER_LABELS[key] ?? sentenceCase(key);
    return { label, value: settingValue(key, value, control) };
  });
}

function settingValue(key: string, value: JsonValue, control?: ControlSpec): string {
  if (Array.isArray(value)) return value.map((item) => settingValue(key, item, control)).join(", ");
  const option = control?.options?.find((item) => item.value === String(value));
  if (option) return sentenceCase(option.label);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (value === null) return "None";
  if (key === "fraction" && typeof value === "number") return formatPercent(value);
  if (typeof value === "number") return formatValue(value);
  if (typeof value === "string") return value;
  return Object.entries(value).map(([name, item]) => `${sentenceCase(name)} ${settingValue(name, item)}`).join(", ");
}

/** The method, filter and their settings of a resolved pipeline, ready to show. */
export function describeConfiguration(config: JsonRecord | undefined, schema: UiSchema) {
  // Temporal or direction-converted runs keep the pipeline one level down.
  const pipeline = asRecord(config?.pipeline) ?? config;
  const method = asRecord(pipeline?.method);
  const filter = asRecord(pipeline?.filter);
  const methodName = String(method?.name ?? "");
  const filterName = String(filter?.name ?? "");
  return {
    method: schema.methods.find((item) => item.name === methodName)?.label ?? sentenceCase(methodName || "method"),
    filter: filterLabel(filterName || "default"),
    methodSettings: settingRows(method?.parameters, schema.controls.methods[methodName]),
    filterSettings: settingRows(filter?.parameters, schema.controls.filters[filterName as FilterName]),
    extra: [
      { title: "Temporal weighting", rows: settingRows(config?.temporal_aggregation) },
      { title: "Direction conversion", rows: settingRows(config?.direction_conversion) },
    ].filter((section) => section.rows.length > 0),
  };
}

export type ConfigurationDescription = ReturnType<typeof describeConfiguration>;

/** Runs of one setup described once. A setting that changes lists every value it took, in run order. */
export function mergeDescriptions(descriptions: ConfigurationDescription[]): ConfigurationDescription {
  const distinct = (values: string[]) => [...new Set(values)].join(", ");
  const mergeRows = (groups: SettingRow[][]): SettingRow[] => {
    const values = new Map<string, string[]>();
    for (const row of groups.flat()) values.set(row.label, [...(values.get(row.label) ?? []), row.value]);
    return [...values].map(([label, list]) => ({ label, value: distinct(list) }));
  };
  const titles = [...new Set(descriptions.flatMap((description) => description.extra.map((section) => section.title)))];
  return {
    method: distinct(descriptions.map((description) => description.method)),
    filter: distinct(descriptions.map((description) => description.filter)),
    methodSettings: mergeRows(descriptions.map((description) => description.methodSettings)),
    filterSettings: mergeRows(descriptions.map((description) => description.filterSettings)),
    extra: titles.map((title) => ({
      title,
      rows: mergeRows(descriptions.map((description) => description.extra.find((section) => section.title === title)?.rows ?? [])),
    })),
  };
}

function asRecord(value: JsonValue | undefined): JsonRecord | undefined {
  return value && typeof value === "object" && !Array.isArray(value) ? value : undefined;
}
