export type JsonValue =
  | null
  | boolean
  | number
  | string
  | JsonValue[]
  | { [key: string]: JsonValue };

export type JsonRecord = Record<string, JsonValue>;
export type Workspace = "start" | "analysis" | "compare" | "sweep";
export type DataMode = "static" | "temporal" | "graphml";
export type ControlValue = boolean | number | string;

export interface OptionSpec {
  value: string;
  label: string;
  description?: string;
  disabled?: boolean;
  directed_only?: boolean;
  illustration?: Record<string, JsonValue>;
}

export interface ControlSpec {
  name: string;
  label: string;
  control: "checkbox" | "number" | "notice" | "range" | "select";
  default?: ControlValue | null;
  description?: string;
  min?: number;
  max?: number;
  step?: number;
  required?: boolean;
  advanced?: boolean;
  disabled?: boolean;
  disabled_reason?: string;
  ignored_when_directed?: boolean;
  ignored_when_directed_reason?: string;
  ignored_when_undirected?: boolean;
  ignored_when_undirected_reason?: string;
  /** Show the control only while these other controls hold these values. */
  shown_when?: Record<string, ControlValue>;
  options?: OptionSpec[];
}

export interface MethodSpec {
  name: string;
  label: string;
  description: string;
  target: "edge" | "node";
  output_type: string;
  preferred_direction: "higher" | "lower";
  primary_statistic: string;
  recommended_filter: FilterName;
  default_filter_parameters: Record<string, ControlValue>;
  requires_weights: boolean;
  requires_integer_weights?: boolean;
  requires_positive_weights?: boolean;
  requires_nonnegative_weights?: boolean;
  supports_directed: boolean;
  supports_weighted: boolean;
  approaches: string[];
  meaning_template?: string;
  score_meaning_template?: string;
  filter_reason?: string;
  references?: MethodReference[];
  reference_note?: string | null;
}

export interface MethodReference {
  citation: string;
  doi: string;
  url: string;
  bibtex: string;
}

export type FilterName = "default" | "fraction" | "significance" | "threshold";

export interface FilterSpec {
  name: FilterName;
  label: string;
  description?: string;
}

export interface TemporalWeightingSpec {
  name: string;
  label: string;
  description: string;
  formula: string;
  age_basis: "elapsed" | "snapshot";
  uses_age: boolean;
  default_parameters: Record<string, number>;
  required_parameters: string[];
  references?: MethodReference[];
  reference_note?: string | null;
}

export interface UiSchema {
  capabilities: Record<string, boolean>;
  defaults: { method: string };
  methods: MethodSpec[];
  method_filters: {
    approaches: Array<{ value: string; label: string }>;
  };
  filters: FilterSpec[];
  controls: {
    methods: Record<string, ControlSpec[]>;
    filters: Record<FilterName, ControlSpec[]>;
  };
  temporal: {
    default_weighting: string;
    weightings: TemporalWeightingSpec[];
    controls: Record<string, ControlSpec[]>;
  };
  comparison?: {
    single_metrics: Array<{ name: string }>;
    pairwise_metrics: Array<{ name: string }>;
  };
}

export interface DataDraft {
  mode: DataMode;
  text: string;
  filename: string;
  delimiter: string;
  source: string;
  target: string;
  weight: string;
  time: string;
  eventWeight: string;
  directed: boolean;
  directionMode: "preserve" | "undirected";
  reciprocalMerge: "sum" | "mean" | "max" | "min";
  temporalWeighting: string;
  temporalParameters: Record<string, ControlValue>;
  evaluationTime: string;
  timeUnit: string;
  snapshotSize: string;
  snapshotOrigin: string;
  zeroWeightPolicy: "drop" | "keep";
}

export interface NetworkContext {
  dataset: string;
  nodes: string;
  edges: string;
  weight: string;
  weightSemantics: "" | "strength" | "distance";
  time: string;
}

export type WeightSign = "positive" | "nonnegative" | "mixed";

export interface PreviewResponse {
  positive_integer_weights?: boolean;
  weight_sign?: WeightSign | null;
  status?: string;
  valid?: boolean;
  can_run?: boolean;
  directed?: boolean;
  source_directed?: boolean;
  weighted?: boolean;
  node_count?: number;
  edge_count?: number;
  row_count?: number;
  component_count?: number;
  connected_component_count?: number;
  weakly_connected_component_count?: number;
  strongly_connected_component_count?: number;
  numeric_edge_attributes?: string[];
  records?: JsonRecord[];
  warnings?: string[];
  errors?: string[];
}

export interface ScoreRange {
  count: number;
  min: number;
  max: number;
}

export interface ScoreResponse {
  status: string;
  score_id: string;
  score_summary: { score_row_count: number };
  score_ranges: Record<string, ScoreRange>;
  statistics: JsonRecord[];
  extraction: JsonRecord;
  resolved_config: JsonRecord;
  warnings: string[];
}

export interface ExtractionResponse {
  status: string;
  result_id: string;
  score_id: string;
  summary: Record<string, JsonValue>;
  extraction: Record<string, JsonValue>;
  statistics: JsonRecord[];
  graph: {
    directed: boolean;
    truncated: boolean;
    nodes: Array<{ id: JsonValue; retained: boolean; component?: number | null; isolated?: boolean }>;
    edges: Array<{
      source: JsonValue;
      target: JsonValue;
      retained: boolean;
      weight?: number;
    }>;
  };
  resolved_config: JsonRecord;
  warnings: string[];
}

export interface FilterPreview {
  status: string;
  target: "edge" | "node";
  selected_item_count: number;
  total_item_count: number;
  selected_item_fraction: number;
  original_node_count: number;
  backbone_node_count: number;
  backbone_edge_count: number;
  original_edge_count: number;
  backbone_component_count: number;
  backbone_node_fraction: number;
  node_coverage_count: number;
  node_coverage_fraction: number;
  drop_isolates: boolean;
  warnings?: string[];
  graph?: ExtractionResponse["graph"];
  resolved_config?: JsonRecord;
}

export interface SavedResult {
  resultId: string;
  label: string;
  selected: boolean;
  result: ExtractionResponse;
}

export interface MetricRecord {
  [key: string]: JsonValue | undefined;
  metric: string;
  status: "ok" | "invalid" | "undefined" | "failed";
  value?: number | null;
  explanation?: string;
  result?: string;
  result_a?: string;
  result_b?: string;
}

export interface ComparisonResponse {
  status: string;
  experiment_id: string;
  results: Array<{ label: string }>;
  single_metrics: MetricRecord[];
  pairwise_metrics: MetricRecord[];
  alignments: AlignmentRecord[];
}

export interface SweepResponse {
  status: string;
  experiment_id?: string;
  score_id?: string | null;
  variation: {
    scope: "configurations" | "filter" | "grid" | "method";
    configurations?: string[];
    parameter?: string;
    values?: JsonValue[];
    methods?: string[];
    filters?: string[];
  };
  configuration: JsonRecord;
  setup_names: Record<string, string>;
  score_cache_hits: number;
  score_cache_misses: number;
  runs: JsonRecord[];
  metrics: JsonRecord[];
}

export interface AlignmentPoint {
  source?: unknown;
  target?: unknown;
  node?: unknown;
  value_a: number;
  value_b: number;
  importance_rank_a: number;
  importance_rank_b: number;
}

export interface AlignmentRecord {
  result_a: string;
  result_b: string;
  status: string;
  explanation: string;
  target?: "edge" | "node";
  output_type_a?: string;
  output_type_b?: string;
  preferred_direction_a?: string;
  preferred_direction_b?: string;
  points: AlignmentPoint[];
}
