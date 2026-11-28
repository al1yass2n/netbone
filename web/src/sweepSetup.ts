import type { ControlSpec, ControlValue, FilterName, JsonRecord, JsonValue, UiSchema, WeightSign } from "./types";
import { formatPercent } from "./utils";

export type SettingKind = "method" | "filter";

export interface SweepSetting extends ControlSpec {
  kind: SettingKind;
  key: string;
}

export interface SweepVariation {
  id: number;
  key: string;
  /** Comma-separated values. In range mode it is written from the range. */
  text: string;
  /** Numeric settings start as a From/To/Step range; "list" takes typed values. */
  mode?: "range" | "list";
  range?: SweepRange;
}

/** A range as typed. A retained fraction is typed in percent. */
export interface SweepRange {
  from: string;
  to: string;
  step: string;
}

export const SWEEP_RUN_LIMIT = 100;

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

/** Disable options that only make sense on directed graphs, such as outgoing-only aggregation. */
export function withDirectedOnlyOptions(control: ControlSpec, directed: boolean): ControlSpec {
  if (directed || !control.options?.some((option) => option.directed_only)) return control;
  return { ...control, options: control.options.map((option) => option.directed_only ? { ...option, disabled: true } : option) };
}

/** Whether a control's `shown_when` conditions hold, reading other controls through `valueOf`. */
export function isControlShown(control: ControlSpec, valueOf: (name: string) => ControlValue | undefined): boolean {
  return !control.shown_when
    || Object.entries(control.shown_when).every(([name, expected]) => String(valueOf(name) ?? "") === String(expected));
}

export function sweepSettings(draft: SweepDraft, schema: UiSchema, { directed, weighted }: SweepEnvironment): SweepSetting[] {
  const method = schema.methods.find((item) => item.name === draft.method);
  const methodControls = (schema.controls.methods[draft.method] || []).filter(
    (control) => !control.disabled && control.control !== "notice"
      && !(directed && control.ignored_when_directed)
      && !(!directed && control.ignored_when_undirected)
      && !(control.name === "distance_transform" && !weighted)
      && control.name !== "link_prediction_mode" && !control.name.startsWith("iforest_similarity_"),
  ).map((control) => withDirectedOnlyOptions(control, directed));
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
  }).filter((control, _index, controls) => isControlShown(control, (name) => {
    // A varied setting can take the value that needs this control, so keep it.
    const key = "filter." + name;
    if (draft.variations.some((variation) => variation.key === key)) return control.shown_when?.[name];
    const other = controls.find((item) => item.name === name);
    return draft.fixed[key] ?? (draft.initialFilterParameters?.[name] as ControlValue | undefined) ?? other?.default ?? undefined;
  }));
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

/** A retained fraction is entered and shown in percent. */
export function isPercentSetting(setting: Pick<SweepSetting, "kind" | "name">): boolean {
  return setting.kind === "filter" && setting.name === "fraction";
}

export function isNumericSetting(setting: SweepSetting): boolean {
  return settingChoices(setting).length === 0;
}

/** The values a range makes, or why it makes none. */
export function rangeValues(range: SweepRange): { values: number[]; error: string } {
  const texts = [range.from, range.to, range.step];
  const [from, to, step] = texts.map(Number) as [number, number, number];
  if (texts.some((text) => !text.trim()) || ![from, to, step].every(Number.isFinite)) {
    return { values: [], error: "Enter a number for From, To and Step." };
  }
  if (step <= 0) return { values: [], error: "Step must be more than 0." };
  if (to < from) return { values: [], error: "To must be at least From." };
  const count = Math.floor((to - from) / step + 1e-9) + 1;
  if (count > SWEEP_RUN_LIMIT) return { values: [], error: `This range makes more than ${SWEEP_RUN_LIMIT} values.` };
  return { values: Array.from({ length: count }, (_, index) => Number((from + index * step).toPrecision(12))), error: "" };
}

export function rangeText(range: SweepRange, setting: Pick<SweepSetting, "kind" | "name">): string {
  return rangeValues(range).values.map((value) => isPercentSetting(setting) ? `${value}%` : String(value)).join(", ");
}

/** A range checked against the setting's limits, in the units it is typed in. */
export function settingRange(range: SweepRange, setting: SweepSetting): { values: number[]; text: string; error: string } {
  const { values, error } = rangeValues(range);
  if (error) return { values: [], text: "", error };
  const percent = isPercentSetting(setting);
  const unit = percent ? "%" : "";
  const scale = (value: number | undefined) => value === undefined ? undefined : Number((value * (percent ? 100 : 1)).toPrecision(12));
  const min = scale(setting.min);
  const max = scale(setting.max);
  const first = values[0] ?? 0;
  const last = values.at(-1) ?? 0;
  if ((min !== undefined && first < min) || (max !== undefined && last > max)) {
    const limits = min !== undefined && max !== undefined ? `from ${min}${unit} to ${max}${unit}`
      : min !== undefined ? `of ${min}${unit} or more` : `of ${max}${unit} or less`;
    return { values: [], text: "", error: `Use values ${limits}.` };
  }
  if (setting.step === 1 && values.some((value) => !Number.isInteger(value))) return { values: [], text: "", error: "Use whole numbers." };
  if (values.length < 2) return { values, text: "", error: "This range makes only one value." };
  return { values, text: rangeText(range, setting), error: "" };
}

/** A starting range: the whole scale for shares, common levels for alpha, five steps from the current value otherwise. */
export function defaultRange(setting: SweepSetting, current: string): SweepRange {
  if (isPercentSetting(setting)) return { from: "10", to: "90", step: "20" };
  if (setting.kind === "filter" && setting.name === "alpha") return { from: "0.01", to: "0.05", step: "0.01" };
  const integer = setting.step === 1;
  const { min, max } = setting;
  if (min !== undefined && max !== undefined && max > min) {
    const step = integer ? Math.max(1, Math.round((max - min) / 5)) : niceNumber((max - min) / 5);
    const from = integer ? Math.min(max, min + Math.floor(step / 2)) : Number((min + step / 2).toPrecision(12));
    return { from: String(from), to: String(Number((from + Math.floor((max - from) / step) * step).toPrecision(12))), step: String(step) };
  }
  const value = Number(current);
  const start = Number.isFinite(value) && current.trim() ? value : min ?? 0;
  // Most scores fall between 0 and 1, so a setting that starts at 0 steps by a quarter.
  const step = integer ? Math.max(1, Math.round(niceNumber(Math.abs(start) / 4))) : start ? niceNumber(Math.abs(start) / 4) : 0.25;
  const end = Number((start + 4 * step).toPrecision(12));
  return { from: String(start), to: String(max === undefined ? end : Math.min(max, end)), step: String(step) };
}

function niceNumber(value: number): number {
  if (!(value > 0)) return 1;
  const power = 10 ** Math.floor(Math.log10(value));
  return Number((([1, 2, 2.5, 5, 10].find((factor) => factor * power >= value) ?? 10) * power).toPrecision(6));
}

/** The variation a setting starts with: a range for numbers, the current choice for options. */
export function variationFor(draft: SweepDraft, setting: SweepSetting, id: number): SweepVariation {
  const current = fixedText(draft, setting);
  if (!isNumericSetting(setting)) return { id, key: setting.key, text: current };
  const range = defaultRange(setting, current);
  return { id, key: setting.key, text: rangeText(range, setting), mode: "range", range };
}

/** A value as the person reads it: option labels and percentages. */
export function formatSweepValue(setting: SweepSetting, value: ControlValue): string {
  const choice = settingChoices(setting).find((item) => item.value === String(value));
  if (choice) return choice.label;
  if (isPercentSetting(setting) && typeof value === "number") return formatPercent(value);
  return String(value);
}

/** One line for each run a sweep will make, in the order the server runs them. */
export function plannedRuns(drafts: SweepDraft[], schema: UiSchema, environment: SweepEnvironment): string[] {
  return drafts.flatMap((draft) => {
    const settings = sweepSettings(draft, schema, environment);
    let runs: string[][] = [[]];
    for (const variation of draft.variations) {
      const setting = settings.find((item) => item.key === variation.key);
      if (!setting) continue;
      const values = splitSweepValues(variation.text).map((text) => parseSetting(text, setting)).filter((value) => value !== undefined);
      runs = runs.flatMap((run) => values.map((value) => [...run, `${setting.label}: ${formatSweepValue(setting, value)}`]));
    }
    return runs.map((run) => [...(drafts.length > 1 ? [draft.name.trim()] : []), ...run].join(" · ") || draft.name.trim());
  });
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
  return setting ? [variationFor(draft, setting, 1)] : [];
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
    name: initialFilterParameters ? "Current settings" : "Setup " + id,
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
    const rangeError = variation.mode === "range" && variation.range ? settingRange(variation.range, setting).error : "";
    if (rangeError) return { count: 0, error: setting.label + ": " + rangeError } as const;
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
    // With one setup its name adds nothing to the message.
    if (!compiled.configuration) return { configurations: [], count: 0, error: (drafts.length > 1 ? name + ": " : "") + compiled.error };
    configurations.push(compiled.configuration);
    count += compiled.count;
  }
  return { configurations, count, error: "" };
}
