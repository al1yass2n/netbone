import { ArrowLeft, ArrowRight, ChevronDown, Copy, Download, LoaderCircle, Pencil, Play, Plus, Settings2, Trash2, X } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import type { RefObject } from "react";
import { api, downloadCsv, downloadJson } from "../api";
import {
  compileSweep, fixedText, initialVariation, newSweepDraft, record, settingChoices,
  splitSweepValues, sweepSettings,
} from "../sweepSetup";
import type { SweepDraft, SweepEnvironment, SweepSetting, SweepVariation } from "../sweepSetup";
import type { FilterName, JsonRecord, JsonValue, MethodSpec, SweepResponse, UiSchema } from "../types";
import { filterOptions, formatValue, labelize, methodCompatibilityReason } from "../utils";
import { sweepRunLabels } from "../sweepFigureData";
import { Hint } from "./Hint";
import { ExperimentExport } from "./ExperimentExport";
import { SweepVisualizations } from "./SweepFigure";
import "./AnalysisWorkspaces.css";

interface Props extends SweepEnvironment {
  schema: UiSchema;
  method: MethodSpec;
  filterName: FilterName;
  basePayload: JsonRecord;
  initialConfiguration?: JsonRecord | null;
}

const runLimit = 100;

export function SweepWorkspace({ schema, method, filterName, directed, weighted, positiveIntegerWeights, weightSign, basePayload, initialConfiguration }: Props) {
  const environment = { directed, weighted, positiveIntegerWeights, weightSign };
  const baseMethod = schema.methods.find((item) => item.name === method.name && methodIsCompatible(item, environment))
    ?? schema.methods.find((item) => methodIsCompatible(item, environment)) ?? method;
  const baseFilter = baseMethod.name === method.name ? filterName : baseMethod.recommended_filter;
  const nextId = useRef(2);
  const [drafts, setDrafts] = useState<SweepDraft[]>(() => [
    newSweepDraft(1, baseMethod.name, baseFilter, schema, environment, initialConfiguration),
  ]);
  const [activeId, setActiveId] = useState(1);
  const [metrics, setMetrics] = useState(() => [
    "edge_retention",
    "node_retention",
    directed ? "weakly_connected_component_count" : "connected_component_count",
  ]);
  const [preview, setPreview] = useState<SweepResponse | null>(null);
  const [result, setResult] = useState<SweepResponse | null>(null);
  const [configurationDrawerOpen, setConfigurationDrawerOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);
  const setupHeading = useRef<HTMLHeadingElement>(null);
  const focusSetup = useRef(false);
  const stage = result ? "results" : preview ? "review" : "configure";
  const compiled = compileSweep(drafts, schema, environment);
  const activeDraft = drafts.find((draft) => draft.id === activeId) ?? drafts[0]!;
  const settings = sweepSettings(activeDraft, schema, environment);
  const availableMetrics = schema.comparison?.single_metrics.map((metric) => metric.name) ?? [];
  const runCount = preview ? responseCount(preview) : compiled.count;
  const validation = compiled.error || (!metrics.length ? "Choose at least one measurement."
    : runCount > runLimit ? "Reduce the sweep to 100 runs or fewer." : "");

  useEffect(() => {
    window.scrollTo(0, 0);
    heading.current?.focus({ preventScroll: true });
  }, [stage]);

  useEffect(() => {
    if (!focusSetup.current) return;
    focusSetup.current = false;
    setupHeading.current?.focus({ preventScroll: true });
  }, [activeId]);

  function update(draft: SweepDraft) {
    setDrafts((current) => current.map((item) => item.id === draft.id ? draft : item));
    setError("");
  }

  function addSetup(source?: SweepDraft) {
    const id = nextId.current++;
    const draft = source
      ? { ...source, id, name: uniqueSetupName(source.name.trim() + " copy", drafts) }
      : newSweepDraft(id, baseMethod.name, baseFilter, schema, environment, initialConfiguration);
    if (!source) draft.name = uniqueSetupName("Setup " + id, drafts);
    setDrafts((current) => [...current, draft]);
    focusSetup.current = true;
    setActiveId(id);
    setError("");
  }

  function removeSetup() {
    const remaining = drafts.filter((item) => item.id !== activeDraft.id);
    if (!remaining.length) return;
    focusSetup.current = true;
    setActiveId(remaining[0]!.id);
    setDrafts(remaining);
    setError("");
  }

  function editSweep() {
    setResult(null);
    setPreview(null);
    setConfigurationDrawerOpen(false);
    setError("");
  }

  async function execute(previewOnly: boolean) {
    if (busy || validation) return;
    setBusy(true);
    setError("");
    try {
      const response = await api.sweep({
        ...basePayload,
        variation: { scope: "configurations" },
        configurations: compiled.configurations,
        metrics,
        preview_only: previewOnly,
      });
      if (previewOnly) setPreview(response);
      else setResult(response);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Sweep failed.");
    } finally {
      setBusy(false);
    }
  }

  if (result) return <SweepResultsView result={result} drawerOpen={configurationDrawerOpen} onDrawer={setConfigurationDrawerOpen} onEdit={editSweep} heading={heading} />;

  return (
    <main className="workspace sweep-workspace sweep-setup-workspace" aria-labelledby="sweep-title">
      <header className="workspace-header">
        <div>
          <h1 id="sweep-title" ref={heading} tabIndex={-1}>{preview ? "Review sweep runs" : "Test a range of settings"}</h1>
          <p>{preview ? "Check the values Netbone will use before running the sweep."
            : "Choose a setting and enter the values you want to compare."}</p>
        </div>
      </header>

      {preview ? <SweepReview preview={preview} drafts={drafts} schema={schema} environment={environment} metrics={metrics} /> : (
        <div className="sweep-configure">
          <section className="panel sweep-configure-panel" aria-labelledby="vary-settings-title">
            {drafts.length > 1 && (
              <label className="field sweep-setup-picker">
                <span>Editing setup</span>
                <select value={activeDraft.id} disabled={busy} onChange={(event) => setActiveId(Number(event.target.value))}>
                  {drafts.map((draft, index) => <option key={draft.id} value={draft.id}>{(index + 1) + ". " + (draft.name.trim() || "Unnamed setup")}</option>)}
                </select>
              </label>
            )}
            <SetupEditor
              key={activeDraft.id}
              draft={activeDraft}
              settings={settings}
              schema={schema}
              environment={environment}
              heading={setupHeading}
              busy={busy}
              onChange={update}
              onDuplicate={() => addSetup(activeDraft)}
              onRemove={drafts.length > 1 ? removeSetup : undefined}
            />
            <div className="sweep-add-setup">
              <button className="button button--quiet" disabled={busy} onClick={() => addSetup()}><Plus size={16} /> Add another setup</button>
              <small>Use a separate setup for another method, filter, or baseline.</small>
            </div>
          </section>
          <details className="panel sweep-measurements">
            <summary><span>Measurements</span><small>{metrics.length} selected</small><ChevronDown size={16} /></summary>
            <fieldset className="metric-checklist" aria-label="Backbone measurements" disabled={busy}>
              {availableMetrics.map((name) => (
                <label key={name}>
                  <input type="checkbox" checked={metrics.includes(name)} onChange={() => {
                    setMetrics((current) => current.includes(name) ? current.filter((item) => item !== name) : [...current, name]);
                    setError("");
                  }} />
                  <span>{labelize(name)}</span>
                </label>
              ))}
            </fieldset>
          </details>
        </div>
      )}

      <footer className="sweep-action-bar" aria-label="Sweep actions">
        {error && <p className="error-text sweep-action-message" role="alert">{error}</p>}
        {!error && validation && <p className="sweep-action-message" role="status">{validation}</p>}
        <div className="sweep-action-row">
          <div className="sweep-run-count">
            <strong aria-live="polite">{runCount ? runCount + (runCount === 1 ? " run" : " runs") : "No runs planned"}</strong>
            <Hint label="How sweep run counts work">Each setup runs every combination of its varying values. Two cutoffs and three method values in one setup make six runs. Netbone adds the runs from each setup, up to 100.</Hint>
          </div>
          <div className="sweep-stage-buttons">
            {preview && <button className="button button--quiet" disabled={busy} onClick={editSweep}><ArrowLeft size={16} /> Edit settings</button>}
            <button className="button button--save" disabled={busy || Boolean(validation)} onClick={() => void execute(!preview)}>
              {busy ? <LoaderCircle className="spin" size={17} /> : preview ? <Play size={16} fill="currentColor" /> : <ArrowRight size={17} />}
              {busy ? (preview ? "Running sweep…" : "Preparing runs…") : preview
                ? "Run " + runCount + (runCount === 1 ? " configuration" : " configurations")
                : "Review runs"}
            </button>
          </div>
        </div>
      </footer>
    </main>
  );
}

function SetupEditor({ draft, settings, schema, environment, heading, busy, onChange, onDuplicate, onRemove }: {
  draft: SweepDraft;
  settings: SweepSetting[];
  schema: UiSchema;
  environment: SweepEnvironment;
  heading: RefObject<HTMLHeadingElement | null>;
  busy: boolean;
  onChange: (draft: SweepDraft) => void;
  onDuplicate: () => void;
  onRemove?: () => void;
}) {
  const method = schema.methods.find((item) => item.name === draft.method);
  const filter = schema.filters.find((item) => item.name === draft.filter);
  const filterNames = method ? filterOptions(method) : [];
  const selectedKeys = new Set(draft.variations.map((item) => item.key));
  const remaining = settings.filter((item) => !selectedKeys.has(item.key));
  const hasUnselectedRow = draft.variations.some((item) => !item.key);

  function replaceVariation(id: number, patch: Partial<SweepVariation>) {
    onChange({ ...draft, variations: draft.variations.map((item) => item.id === id ? { ...item, ...patch } : item) });
  }

  function addVariation() {
    const id = Math.max(0, ...draft.variations.map((item) => item.id)) + 1;
    onChange({ ...draft, variations: [...draft.variations, { id, key: "", text: "" }] });
  }

  function changeBase(methodName: string, filterName: FilterName) {
    const sameMethod = methodName === draft.method;
    const sameFilter = sameMethod && filterName === draft.filter;
    const next = {
      ...draft,
      method: methodName,
      filter: filterName,
      fixed: sameMethod ? Object.fromEntries(Object.entries(draft.fixed).filter(([key]) => key.startsWith("method."))) : {},
      variations: sameMethod ? draft.variations.filter((item) => item.key.startsWith("method.")) : [],
      initialMethodParameters: sameMethod ? draft.initialMethodParameters : undefined,
      initialFilterParameters: sameFilter ? draft.initialFilterParameters : undefined,
    };
    const nextSettings = sweepSettings(next, schema, environment);
    onChange({ ...next, variations: next.variations.length ? next.variations : initialVariation(next, nextSettings) });
  }

  return (
    <fieldset className="sweep-editor-fields" disabled={busy}>
      <div className="sweep-setup-context">
        <strong>{draft.name.trim() || "Unnamed setup"}</strong>
        <span>{method?.label ?? labelize(draft.method)} · {filter?.label ?? labelize(draft.filter)}</span>
      </div>
      <h2 id="vary-settings-title" ref={heading} tabIndex={-1}>What to vary?</h2>
      {draft.variations.length ? (
        <div className="sweep-variation-list">
          {draft.variations.map((variation, index) => (
            <VariationEditor
              key={variation.id}
              index={index}
              variation={variation}
              settings={settings.filter((item) => item.key === variation.key || !selectedKeys.has(item.key))}
              onSelect={(key) => {
                const setting = settings.find((item) => item.key === key);
                replaceVariation(variation.id, { key, text: setting ? fixedText(draft, setting) : "" });
              }}
              onValues={(text) => replaceVariation(variation.id, { text })}
              onRemove={() => onChange({ ...draft, variations: draft.variations.filter((item) => item.id !== variation.id) })}
            />
          ))}
        </div>
      ) : <p className="sweep-fixed-message">{settings.length
        ? "This setup runs once with fixed settings. Add a setting to test more values."
        : "This method and filter have no settings to vary. Change the base setup or add a separate setup."}</p>}
      {remaining.length > 0 && !hasUnselectedRow && (
        <button className="button button--quiet sweep-add-setting" onClick={addVariation}>
          <Plus size={16} /> {draft.variations.length ? "Add another setting" : "Add a varying setting"}
        </button>
      )}

      <details className="advanced-options sweep-fixed-settings">
        <summary>Base setup and fixed settings <ChevronDown size={16} /></summary>
        <div className="sweep-fixed-fields">
          <label className="field"><span>Setup name</span><input value={draft.name} onChange={(event) => onChange({ ...draft, name: event.target.value })} /></label>
          <div className="field-grid">
            <label className="field"><span>Scoring method</span><select value={draft.method} onChange={(event) => {
              const selected = schema.methods.find((item) => item.name === event.target.value);
              if (selected) changeBase(selected.name, selected.recommended_filter);
            }}>
              {schema.methods.map((item) => <option key={item.name} value={item.name} disabled={!methodIsCompatible(item, environment)}>
                {item.label}{methodCompatibilityNote(item, environment)}
              </option>)}
            </select></label>
            <label className="field"><span>Filter</span><select value={draft.filter} onChange={(event) => changeBase(draft.method, event.target.value as FilterName)}>
              {schema.filters.filter((item) => item.name === "default" || item.name === draft.filter || filterNames.includes(item.name)).map((item) => <option key={item.name} value={item.name}>{item.label}</option>)}
            </select></label>
          </div>
          {remaining.length > 0 && <div className="field-grid">{remaining.map((setting) => (
            <FixedSetting key={setting.key} setting={setting} value={fixedText(draft, setting)} onChange={(text) => onChange({ ...draft, fixed: { ...draft.fixed, [setting.key]: text } })} />
          ))}</div>}
          <div className="sweep-base-actions">
            <button className="button button--quiet" onClick={onDuplicate}><Copy size={15} /> Duplicate setup</button>
            {onRemove && <button className="button button--quiet" onClick={onRemove}><Trash2 size={15} /> Remove setup</button>}
          </div>
        </div>
      </details>
    </fieldset>
  );
}

function VariationEditor({ index, variation, settings, onSelect, onValues, onRemove }: {
  index: number;
  variation: SweepVariation;
  settings: SweepSetting[];
  onSelect: (key: string) => void;
  onValues: (text: string) => void;
  onRemove: () => void;
}) {
  const id = useId();
  const setting = settings.find((item) => item.key === variation.key);
  const choices = setting ? settingChoices(setting) : [];
  const values = splitSweepValues(variation.text);
  const numericHint = setting?.name === "fraction"
    ? "Enter at least two comma-separated fractions or percentages, such as 0.25, 0.5 or 25%, 50%."
    : setting?.min !== undefined && setting.max !== undefined
      ? "Enter at least two comma-separated values between " + setting.min + " and " + setting.max + "."
      : "Enter at least two comma-separated values.";
  return (
    <div className="sweep-variation">
      <div className="sweep-variation-header">
        <label className="field">
          <span>{"Setting " + (index + 1)}</span>
          <select value={variation.key} autoFocus={!variation.key} onChange={(event) => onSelect(event.target.value)}>
            <option value="" disabled>Choose a setting</option>
            {(["filter", "method"] as const).map((kind) => {
              const available = settings.filter((item) => item.kind === kind);
              return available.length > 0 && <optgroup key={kind} label={kind === "filter" ? "Filter settings" : "Method settings"}>
                {available.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
              </optgroup>;
            })}
          </select>
        </label>
        <button className="icon-button" title="Remove varying setting" aria-label={"Remove varying setting " + (index + 1)} onClick={onRemove}><X size={17} /></button>
      </div>
      {setting && (choices.length > 0 ? (
        <div className="sweep-choice-fields">
          <span id={id}>{"Values for " + setting.label.toLowerCase()}</span>
          <div className="parameter-choices" role="group" aria-labelledby={id} aria-describedby={id + "-hint"}>
            {choices.map((choice) => (
              <button key={choice.value} aria-pressed={values.includes(choice.value)} onClick={() => onValues(
                (values.includes(choice.value) ? values.filter((item) => item !== choice.value) : [...values, choice.value]).join(", "),
              )}>{choice.label}</button>
            ))}
          </div>
          <small id={id + "-hint"}>Choose two or more values to compare.</small>
        </div>
      ) : (
        <label className="field">
          <span>{"Values for " + setting.label.toLowerCase()}</span>
          <input aria-describedby={id + "-hint"} value={variation.text} onChange={(event) => onValues(event.target.value)} placeholder={setting.name === "fraction" ? "25%, 50%, 75%" : "Value 1, value 2, value 3"} />
          <small id={id + "-hint"}>{numericHint}</small>
        </label>
      ))}
    </div>
  );
}

function FixedSetting({ setting, value, onChange }: { setting: SweepSetting; value: string; onChange: (text: string) => void }) {
  const choices = settingChoices(setting);
  return <label className="field">
    <span>{setting.label}</span>
    {choices.length ? <select value={value} onChange={(event) => onChange(event.target.value)}>
      <option value="">Use default</option>
      {choices.map((choice) => <option key={choice.value} value={choice.value}>{choice.label}</option>)}
    </select> : <input type="number" step="any" min={setting.min} max={setting.max} value={value} onChange={(event) => onChange(event.target.value)} placeholder="Use default" />}
  </label>;
}

function SweepReview({ preview, drafts, schema, environment, metrics }: {
  preview: SweepResponse;
  drafts: SweepDraft[];
  schema: UiSchema;
  environment: SweepEnvironment;
  metrics: string[];
}) {
  const configurations = record(preview.configuration.configurations) ?? {};
  const setups = new Map(drafts.map((draft) => [draft.name.trim(), { draft, settings: sweepSettings(draft, schema, environment) }]));
  return <section className="panel sweep-run-preview" aria-labelledby="sweep-preview-title">
    <h2 id="sweep-preview-title">Runs to execute</h2>
    <p className="sweep-measurement-summary">{"Measurements: " + metrics.map(labelize).join(", ")}</p>
    <p>Open a run to see its complete method and filter settings.{Object.keys(configurations).length > 4 && " Scroll down to see all runs."}</p>
    <div className="sweep-preview-list">
      {Object.entries(configurations).map(([name, configuration]) => {
        const setupName = preview.setup_names[name] ?? "Extraction setup";
        const setup = setups.get(setupName);
        const changes = setup ? variedSettings(configuration, setup.draft.variations, setup.settings) : [];
        return <details key={name}>
          <summary>
            <span>
              <strong>{setupName}</strong>
              <small>{configurationSummary(configuration)}</small>
              {changes.length > 0 ? <span className="sweep-reviewed-values">{changes.map(({ key, label, value }) => <span key={key}>{label}: {value}</span>)}</span> : <small>Fixed settings</small>}
            </span>
            <ChevronDown size={16} />
          </summary>
          <ConfigurationDetails value={configuration} />
        </details>;
      })}
    </div>
  </section>;
}

function variedSettings(configuration: JsonValue, variations: SweepVariation[], settings: SweepSetting[]) {
  const config = record(configuration);
  return variations.flatMap((variation) => {
    const setting = settings.find((item) => item.key === variation.key);
    if (!setting) return [];
    const value = record(record(config?.[setting.kind])?.parameters)?.[setting.name];
    const label = settingChoices(setting).find((item) => item.value === String(value))?.label;
    const formatted = setting.name === "fraction" && typeof value === "number"
      ? new Intl.NumberFormat("en", { style: "percent", maximumSignificantDigits: 16 }).format(value)
      : typeof value === "number" ? String(value) : formatValue(value);
    return [{ key: setting.key, label: setting.label, value: label ?? formatted }];
  });
}

function methodIsCompatible(method: MethodSpec, environment: SweepEnvironment): boolean {
  return !methodCompatibilityReason(method, environment);
}

function methodCompatibilityNote(method: MethodSpec, environment: SweepEnvironment): string {
  const reason = methodCompatibilityReason(method, environment);
  return reason ? ` (${reason})` : "";
}

function uniqueSetupName(base: string, drafts: SweepDraft[]): string {
  const names = new Set(drafts.map((draft) => draft.name.trim()));
  let name = base;
  let suffix = 2;
  while (names.has(name)) name = base + " " + suffix++;
  return name;
}

function SweepResultsView({ result, drawerOpen, onDrawer, onEdit, heading }: { result: SweepResponse; drawerOpen: boolean; onDrawer: (open: boolean) => void; onEdit: () => void; heading: RefObject<HTMLHeadingElement | null> }) {
  const configurations = (result.configuration.configurations || {}) as JsonRecord;
  const runLabels = sweepRunLabels(result);
  return <main className="workspace sweep-workspace sweep-results-workspace" aria-labelledby="sweep-results-title">
    <header className="workspace-header">
      <div><h1 id="sweep-results-title" ref={heading} tabIndex={-1}>Sweep results</h1><p>See how your settings affected retention and other backbone properties.</p></div>
      <div className="figure-actions">
        <button className="button button--quiet" onClick={() => onDrawer(true)}><Settings2 size={16} /> Run settings</button>
        <button className="button button--primary" onClick={onEdit}><Pencil size={16} /> Edit sweep</button>
        {result.experiment_id && <ExperimentExport key={result.experiment_id} experimentId={result.experiment_id} />}
      </div>
    </header>
    <div className="sweep-summary"><Summary label="Total runs" value={result.runs.length} /><Summary label="Successful runs" value={result.runs.filter((row) => row.status === "ok").length} /><Summary label="Failed runs" value={result.runs.filter((row) => row.status === "failed").length} /><Summary label="Runs reusing scores" value={result.score_cache_hits} /></div>
    <SweepVisualizations result={result} />
    <section className="panel sweep-table-panel"><header><div><h2>Run measurements</h2><p>Review each measured value and explanations for unavailable or failed results.</p></div><div className="figure-actions"><button className="button button--export" onClick={() => downloadCsv(result.metrics, "netbone-sweep-metrics.csv")}><Download size={15} /> Metrics CSV</button><button className="button button--export" onClick={() => downloadCsv(result.runs, "netbone-sweep-runs.csv")}><Download size={15} /> Runs CSV</button><button className="button button--export" onClick={() => downloadJson(result.configuration, "netbone-sweep-config.json")}><Download size={15} /> Settings JSON</button></div></header><SweepTable result={result} /></section>
    {drawerOpen && <><button className="drawer-scrim" aria-label="Close configuration details" onClick={() => onDrawer(false)} /><aside className="configuration-drawer" aria-label="Generated configurations"><header><div><span className="eyebrow">SWEEP SETUP</span><h2>Generated configurations</h2></div><button className="icon-button" title="Close" aria-label="Close configuration details" onClick={() => onDrawer(false)}><X size={18} /></button></header><div className="configuration-drawer-list">{result.runs.map((run) => {
      const name = String(run.pipeline_name);
      const configuration = configurations[name];
      return <section key={name}><b>{formatValue(run.run_id)}</b><div><strong>{runLabels.get(Number(run.run_id))}</strong><small>{configurationSummary(configuration)}</small><ConfigurationDetails value={configuration} /></div></section>;
    })}</div></aside></>}
  </main>;
}

function ConfigurationDetails({ value }: { value: unknown }) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const configuration = value as JsonRecord;
  const method = configuration.method as JsonRecord | undefined;
  const filter = configuration.filter as JsonRecord | undefined;
  return <dl><div><dt>Method parameters</dt><dd>{compactParameters(method?.parameters)}</dd></div><div><dt>Filter parameters</dt><dd>{compactParameters(filter?.parameters)}</dd></div></dl>;
}

function compactParameters(value: unknown): string {
  if (!value || typeof value !== "object" || Array.isArray(value)) return "Registered defaults";
  const entries = Object.entries(value as JsonRecord);
  return entries.length ? entries.map(([name, parameter]) => labelize(name) + ": " + (typeof parameter === "number" ? String(parameter) : formatValue(parameter))).join(" · ") : "Registered defaults";
}

function Summary({ label, value }: { label: string; value: unknown }) { return <div><span>{label}</span><strong>{formatValue(value)}</strong></div>; }
function SweepTable({ result }: { result: SweepResponse }) {
  const labels = sweepRunLabels(result);
  return <div className="table-wrap"><table>
    <thead><tr><th>Run</th><th>Metric</th><th>Value</th><th>Status</th><th>Explanation</th></tr></thead>
    <tbody>{result.metrics.map((record, index) => (
      <tr key={index}>
        <td className="sweep-run-label">{labels.get(Number(record.run_id)) ?? `Run ${record.run_id}`}</td>
        <td>{typeof record.metric === "string" ? labelize(record.metric) : "—"}</td>
        <td>{formatValue(record.value)}</td>
        <td>{formatValue(record.status)}</td>
        <td>{typeof record.explanation === "string" && record.explanation ? record.explanation : "—"}</td>
      </tr>
    ))}</tbody>
  </table></div>;
}

function responseCount(response: SweepResponse): number { return Object.keys((response.configuration.configurations || {}) as JsonRecord).length; }
function configurationSummary(value: unknown): string { if (!value || typeof value !== "object" || Array.isArray(value)) return "Resolved pipeline"; const config = value as JsonRecord; const method = config.method as JsonRecord | undefined; const filter = config.filter as JsonRecord | undefined; return `${labelize(String(method?.name || "method"))} · ${labelize(String(filter?.name || "filter"))}`; }
