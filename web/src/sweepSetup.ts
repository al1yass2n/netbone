import type { ControlSpec, ControlValue, FilterName, JsonRecord, JsonValue, UiSchema, WeightSign } from "./types";

export type SettingKind = "method" | "filter";

export interface SweepSetting extends ControlSpec {
  kind: SettingKind;
  key: string;
}

export interface SweepVariation {
  id: number;
  key: string;
  text: string;
}

export interface SweepDraft {
  id: number;
  name: string;
  method: string;
  filter: FilterName;
  fixed: Record<string, string>;
  variations: SweepVariation[];
  initialMethodParameters?: JsonRecord;
  initialFilterParameters?: JsonRecord;
}

export interface SweepEnvironment {
  directed: boolean;
  weighted: boolean;
  positiveIntegerWeights?: boolean;
  weightSign?: WeightSign | null;
}

export function record(value: JsonValue | undefined): JsonRecord | undefined {
  return value && typeof value === "object" && !Array.isArray(value) ? value : undefined;
}

export function sweepSettings(draft: SweepDraft, schema: UiSchema, { directed, weighted }: SweepEnvironment): SweepSetting[] {
  const method = schema.methods.find((item) => item.name === draft.method);
  const methodControls = (schema.controls.methods[draft.method] || []).filter(
    (control) => !control.disabled && control.control !== "notice"
      && !(directed && control.ignored_when_directed)
      && !(!directed && control.ignored_when_undirected)
      && !(control.name === "distance_transform" && !weighted)
      && control.name !== "link_prediction_mode" && !control.name.startsWith("iforest_similarity_"),
  );
  const filterControls = (schema.controls.filters[draft.filter] || []).filter(
    (control) => !control.disabled && control.control !== "notice"
      && control.name !== "statistic" && !(control.name === "drop_isolates" && method?.target === "node"),
  ).map((control) => {
    // Cutoffs use the method's score units, so there is no generic 0–1 bound.
    if (control.name === "threshold_value") {
      return { ...control, name: "value", min: undefined, max: undefined, step: undefined,
        ...(draft.method === "noise_corrected" ? { label: "Standard deviation cutoff", default: method?.default_filter_parameters?.value } : {}) };
    }
    if (control.name === "operator" && draft.filter === "threshold" && draft.method === "noise_corrected") {
      return { ...control, default: method?.default_filter_parameters?.operator };
    }
    if (control.name === "operator" && method?.preferred_direction === "lower") {
      return { ...control, default: "less_equal" };
    }
    return control;
  });
  if (draft.method === "link_prediction" && (draft.filter === "default" || draft.filter === "fraction")) {
    filterControls.push({
      name: "direction",
      label: "Similarity to keep",
      control: "select",
      default: "higher",
      options: [
        { value: "higher", label: "High similarity" },
        { value: "lower", label: "Low similarity" },
      ],
    });
  }

  return [
    ...filterControls.map((control) => ({ ...control, kind: "filter" as const, key: "filter." + control.name })),
    ...methodControls.map((control) => ({ ...control, kind: "method" as const, key: "method." + control.name })),
  ];
}

export function settingChoices(setting: SweepSetting): Array<{ value: string; label: string }> {
  if (setting.control === "checkbox") return [{ value: "false", label: "No" }, { value: "true", label: "Yes" }];
  return setting.options?.filter((option) => !option.disabled).map(({ value, label }) => ({ value: String(value), label })) || [];
}

export function splitSweepValues(text: string): string[] {
  return text.split(",").map((value) => value.trim()).filter(Boolean);
}

export function fixedText(draft: SweepDraft, setting: SweepSetting): string {
  const initial = setting.kind === "method" ? draft.initialMethodParameters : draft.initialFilterParameters;
  return draft.fixed[setting.key] ?? String(initial?.[setting.name] ?? setting.default ?? "");
}

export function initialVariation(draft: SweepDraft, settings: SweepSetting[]): SweepVariation[] {
  const preferred = { fraction: "fraction", significance: "alpha", threshold: "value", default: "" }[draft.filter];
  const setting = settings.find((item) => item.kind === "filter" && item.name === preferred)
    ?? settings.find((item) => item.kind === "method" && !item.advanced)
    ?? settings[0];
  return setting ? [{ id: 1, key: setting.key, text: fixedText(draft, setting) }] : [];
}

export function newSweepDraft(
  id: number,
  method: string,
  filter: FilterName,
  schema: UiSchema,
  environment: SweepEnvironment,
  configuration?: JsonRecord | null,
): SweepDraft {
  const pipeline = record(configuration?.pipeline) ?? configuration;
  const methodConfig = record(pipeline?.method);
  const filterConfig = record(pipeline?.filter);
  const initialMethodParameters = methodConfig?.name === method ? record(methodConfig.parameters) : undefined;
  const initialFilterParameters = methodConfig?.name === method && filterConfig?.name === filter ? record(filterConfig.parameters) : undefined;
  const draft = {
    id,
    name: initialFilterParameters ? "Current extraction" : "Setup " + id,
    method,
    filter,
    fixed: {},
    variations: [],
    initialMethodParameters,
    initialFilterParameters,
  };
  return { ...draft, variations: initialVariation(draft, sweepSettings(draft, schema, environment)) };
}

function parseSetting(text: string, setting: SweepSetting): ControlValue | undefined {
  if (setting.control === "checkbox") {
    return text === "true" ? true : text === "false" ? false : undefined;
  }
  if (setting.control === "select") {
    return settingChoices(setting).some((choice) => choice.value === text) ? text : undefined;
  }
  const percent = setting.kind === "filter" && setting.name === "fraction" && text.endsWith("%");
  const numericText = percent ? text.slice(0, -1).trim() : text;
  if (!/^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(numericText)) return undefined;
  const value = Number(numericText) / (percent ? 100 : 1);
  if (!Number.isFinite(value) || (setting.control === "number" && setting.step === 1 && !Number.isInteger(value))) return undefined;
  if ((setting.min !== undefined && value < setting.min) || (setting.max !== undefined && value > setting.max)) return undefined;
  return value;
}

function fixedGrid(initial?: JsonRecord): JsonRecord {
  // The package expands arrays as grids. Wrap a resolved list in one grid slot
  // so settings such as the selected similarities stay fixed in every run.
  return Object.fromEntries(
    Object.entries(initial || {}).map(([name, value]) => [name, Array.isArray(value) ? [value] : value]),
  );
}

export function compileSweepDraft(draft: SweepDraft, settings: SweepSetting[]) {
  const methodParameters = fixedGrid(draft.initialMethodParameters);
  const filterParameters = fixedGrid(draft.initialFilterParameters);
  const seen = new Set<string>();
  let count = 1;
  for (const variation of draft.variations) {
    const setting = settings.find((item) => item.key === variation.key);
    if (!setting) return { count: 0, error: "Choose which setting to vary." } as const;
    if (seen.has(setting.key)) return { count: 0, error: "Choose each varying setting only once." } as const;
    seen.add(setting.key);
    const parsed = splitSweepValues(variation.text).map((text) => parseSetting(text, setting));
    if (parsed.some((value) => value === undefined)) {
      return { count: 0, error: "Enter valid values for " + setting.label.toLowerCase() + "." } as const;
    }
    const values = parsed.filter((value) => value !== undefined);
    if (new Set(values).size < 2) {
      return { count: 0, error: "Choose two or more different values for " + setting.label.toLowerCase() + "." } as const;
    }
    const parameters = setting.kind === "method" ? methodParameters : filterParameters;
    parameters[setting.name] = values;
    count *= values.length;
  }
  for (const setting of settings) {
    if (seen.has(setting.key)) continue;
    const initial = setting.kind === "method" ? draft.initialMethodParameters : draft.initialFilterParameters;
    if (initial && !(setting.key in draft.fixed)) continue;
    const text = fixedText(draft, setting).trim() || String(setting.default ?? "");
    const parameters = setting.kind === "method" ? methodParameters : filterParameters;
    if (!text) {
      delete parameters[setting.name];
      continue;
    }
    const parsed = parseSetting(text, setting);
    if (parsed === undefined) return { count: 0, error: "Enter a valid fixed value for " + setting.label.toLowerCase() + "." } as const;
    parameters[setting.name] = parsed;
  }
  const configuration: JsonRecord = {
    name: draft.name.trim(),
    method: { name: draft.method, parameters: methodParameters },
    filter: { name: draft.filter, parameters: filterParameters },
  };
  return { count, configuration, error: "" } as const;
}

export function compileSweep(drafts: SweepDraft[], schema: UiSchema, environment: SweepEnvironment) {
  const configurations: JsonRecord[] = [];
  const names = new Set<string>();
  let count = 0;
  for (const draft of drafts) {
    const name = draft.name.trim();
    if (!name) return { configurations: [], count: 0, error: "Give each setup a name." };
    if (names.has(name)) return { configurations: [], count: 0, error: "Give each setup a different name." };
    names.add(name);
    const compiled = compileSweepDraft(draft, sweepSettings(draft, schema, environment));
    if (!compiled.configuration) return { configurations: [], count: 0, error: name + ": " + compiled.error };
    configurations.push(compiled.configuration);
    count += compiled.count;
  }
  return { configurations, count, error: "" };
}
