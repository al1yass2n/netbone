import type {
  ControlSpec,
  ControlValue,
  DataDraft,
  FilterName,
  JsonRecord,
  MethodSpec,
  NetworkContext,
  WeightSign,
} from "./types";

export function parseHeaders(text: string, delimiter: string): string[] {
  const firstLine = text.split(/\r?\n/).find((line) => line.trim().length > 0);
  if (!firstLine) return [];
  const values: string[] = [];
  let value = "";
  let quoted = false;
  for (let index = 0; index < firstLine.length; index += 1) {
    const character = firstLine[index];
    const next = firstLine[index + 1];
    if (character === '"' && quoted && next === '"') {
      value += '"';
      index += 1;
    } else if (character === '"') {
      quoted = !quoted;
    } else if (!quoted && (delimiter === " " ? /\s/.test(character ?? "") : character === delimiter)) {
      values.push(value.trim());
      value = "";
    } else {
      value += character;
    }
  }
  values.push(value.trim());
  return values.filter(Boolean);
}

export function detectDelimiter(filename: string, text: string): string {
  if (/\.tsv$/i.test(filename)) return "\t";
  const firstLine = text.split(/\r?\n/).find((line) => line.trim().length > 0) || "";
  const candidates = [",", "\t", ";"];
  const best = candidates.reduce((best, candidate) => {
    const count = firstLine.split(candidate).length;
    const bestCount = firstLine.split(best).length;
    return count > bestCount ? candidate : best;
  }, ",");
  // A header such as "source target weight" has no comma, tab or semicolon.
  if (firstLine.split(best).length === 1 && firstLine.trim().split(/\s+/).length > 1) return " ";
  return best;
}

export function guessColumn(
  headers: string[],
  candidates: string[],
  fallback: number | null,
): string {
  const normalized = new Map(headers.map((header) => [header.toLowerCase(), header]));
  for (const candidate of candidates) {
    const match = normalized.get(candidate);
    if (match) return match;
  }
  return fallback === null ? "" : headers[fallback] || "";
}

export function contextSummary(
  data: DataDraft,
  context: NetworkContext,
  effectiveDirected: boolean,
): string {
  const parts = [
    `${context.dataset}. Nodes represent ${context.nodes}.`,
    effectiveDirected
      ? `Directed arcs represent ${context.edges} from source to target.`
      : `Edges represent ${context.edges}.`,
  ];
  if (data.mode === "temporal" || data.weight) {
    const meaning = context.weightSemantics === "distance"
      ? "Larger weights mean greater distance or cost."
      : context.weightSemantics === "strength"
        ? "Larger weights mean stronger or more frequent relationships."
        : "";
    parts.push(`Weight represents ${context.weight}.`);
    if (meaning) parts.push(meaning);
  }
  if (data.mode === "temporal") parts.push(`Time represents ${context.time}.`);
  return parts.join(" ");
}

export function contextualMeaning(method: MethodSpec, context: NetworkContext): string {
  const template = method.score_meaning_template || method.meaning_template || method.description;
  const targets = method.target === "node" ? context.nodes : context.edges;
  return template
    .replaceAll("{nodes}", context.nodes)
    .replaceAll("{edges}", context.edges)
    .replaceAll("{weight}", context.weight)
    .replaceAll("{target_items}", targets);
}

export function initialControlValues(controls: ControlSpec[]): Record<string, ControlValue> {
  return Object.fromEntries(
    controls
      .filter((control) => control.control !== "notice" && control.default !== null)
      .map((control) => [control.name, control.default ?? ""]),
  );
}

export function methodCompatibilityReason(
  method: MethodSpec,
  { directed, weighted, positiveIntegerWeights, weightSign }: {
    directed: boolean;
    weighted: boolean;
    positiveIntegerWeights?: boolean;
    weightSign?: WeightSign | null;
  },
): string {
  if (directed && !method.supports_directed) return "Not available for directed networks";
  if (!weighted && method.requires_weights) return "Requires a weight column";
  if (method.requires_integer_weights && positiveIntegerWeights === false) {
    return "Requires positive whole-number weights";
  }
  if (weighted && method.requires_positive_weights && weightSign && weightSign !== "positive") {
    return "Requires positive weights";
  }
  if (weighted && method.requires_nonnegative_weights && weightSign === "mixed") {
    return "Requires non-negative weights";
  }
  return "";
}

export function filterOptions(method: MethodSpec): FilterName[] {
  const options = new Set<FilterName>([method.recommended_filter]);
  if (method.output_type === "pvalue") {
    options.add("significance");
    options.add("fraction");
    options.add("threshold");
  } else if (method.recommended_filter === "default") {
    options.add("fraction");
    options.add("threshold");
  } else {
    options.add("threshold");
    options.add("fraction");
  }
  return [...options];
}

export function buildPayload(
  data: DataDraft,
  context: NetworkContext,
  method: MethodSpec | null,
  filter: FilterName,
  controls: Record<string, ControlValue>,
): JsonRecord {
  const sourceDirected = data.directed;
  const effectiveDirected = sourceDirected && data.directionMode === "preserve";
  const payload: JsonRecord = {
    data_mode: data.mode,
    source: data.mode === "graphml" ? null : data.source,
    target: data.mode === "graphml" ? null : data.target,
    weight: data.mode === "temporal" ? null : data.weight || null,
    delimiter: data.delimiter,
    directed: data.mode === "graphml" ? false : data.directed,
    direction_mode: sourceDirected ? data.directionMode : "preserve",
    reciprocal_merge: data.reciprocalMerge,
    context: contextSummary(data, context, effectiveDirected),
    guided: {
      method: method?.name || null,
      filter,
      controls,
    },
  };
  if (data.mode === "graphml") payload.graphml_text = data.text;
  else payload.csv_text = data.text;
  if (data.mode === "temporal") {
    payload.time = data.time;
    payload.event_weight = data.eventWeight || null;
    const weighting = data.temporalWeighting;
    const usesElapsedTime = weighting.startsWith("persistent_");
    payload.temporal = {
      weighting,
      parameters: data.temporalParameters,
      evaluation_time: data.evaluationTime || null,
      time_unit: usesElapsedTime ? data.timeUnit || null : null,
      snapshot_size: usesElapsedTime ? null : data.snapshotSize || null,
      snapshot_origin: usesElapsedTime ? null : data.snapshotOrigin || null,
      zero_weight_policy: data.zeroWeightPolicy,
    };
  }
  return payload;
}

export function formatPercent(value: unknown): string {
  const number = Number(value);
  return Number.isFinite(number) ? `${(number * 100).toFixed(1)}%` : "Not available";
}

export function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Not available";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return String(value);
    return Number.isInteger(value) ? String(value) : value.toPrecision(5).replace(/\.?0+$/, "");
  }
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function labelize(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

