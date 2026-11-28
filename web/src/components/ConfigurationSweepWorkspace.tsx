import { ChevronDown, Copy, LoaderCircle, Pencil, Play, Plus, Settings2, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { RefObject } from "react";
import { api, downloadCsv, downloadJson, downloadWorkspaceExperiment } from "../api";
import { describeConfiguration, filterLabel, formatMetric, mergeDescriptions, metricLabel } from "../labels";
import {
  compileSweep, defaultRange, fixedText, initialVariation, isPercentSetting, newSweepDraft, plannedRuns, settingChoices,
  settingRange, splitSweepValues, sweepSettings, SWEEP_RUN_LIMIT, variationFor,
} from "../sweepSetup";
import type { SweepDraft, SweepEnvironment, SweepRange, SweepSetting, SweepVariation } from "../sweepSetup";
import type { FilterName, JsonRecord, MethodSpec, SweepResponse, UiSchema } from "../types";
import { filterOptions, methodCompatibilityReason } from "../utils";
import { BackLink } from "./BackLink";
import { SettingsList } from "./BackboneDetails";
import { DownloadMenu } from "./DownloadMenu";
import type { DownloadItem } from "./DownloadMenu";
import { Hint } from "./Hint";
import { SweepVisualizations, useSweepFigure } from "./SweepFigure";
import "./AnalysisWorkspaces.css";

interface Props extends SweepEnvironment {
  schema: UiSchema;
  method: MethodSpec;
  filterName: FilterName;
  basePayload: JsonRecord;
  initialConfiguration?: JsonRecord | null;
  onBack: () => void;
}

export function SweepWorkspace({ schema, method, filterName, directed, weighted, positiveIntegerWeights, weightSign, basePayload, initialConfiguration, onBack }: Props) {
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
  const [result, setResult] = useState<SweepResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);
  const setupHeading = useRef<HTMLHeadingElement>(null);
  const focusSetup = useRef(false);
  const compiled = compileSweep(drafts, schema, environment);
  const activeDraft = drafts.find((draft) => draft.id === activeId) ?? drafts[0]!;
  const settings = sweepSettings(activeDraft, schema, environment);
  const availableMetrics = schema.comparison?.single_metrics.map((metric) => metric.name) ?? [];
  const runCount = compiled.count;
  const validation = compiled.error || (!metrics.length ? "Choose at least one measurement."
    : runCount > SWEEP_RUN_LIMIT ? `Reduce the sweep to ${SWEEP_RUN_LIMIT} runs or fewer.` : "");
  // With one setting in one setup, the value line already lists every run.
  const listRuns = !compiled.error && (drafts.length > 1 || drafts.some((draft) => draft.variations.length > 1));

  useEffect(() => {
    window.scrollTo(0, 0);
    heading.current?.focus({ preventScroll: true });
  }, [result]);

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

  async function run() {
    if (busy || validation) return;
    setBusy(true);
    setError("");
    try {
      setResult(await api.sweep({
        ...basePayload,
        variation: { scope: "configurations" },
        configurations: compiled.configurations,
        metrics,
      }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Sweep failed.");
    } finally {
      setBusy(false);
    }
  }

  if (result) return <SweepResults result={result} schema={schema} heading={heading} onBack={onBack} onEdit={() => { setResult(null); setError(""); }} />;

  return (
    <main className="workspace sweep-workspace sweep-setup-workspace" aria-labelledby="sweep-title">
      <BackLink onClick={onBack} />
      <header className="workspace-header">
        <div>
          <h1 id="sweep-title" ref={heading} tabIndex={-1}>Test a range of settings</h1>
          <p>Netbone builds a backbone for each value and measures how it changes.</p>
        </div>
      </header>

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
            <button className="button button--quiet" disabled={busy} onClick={() => addSetup()}><Plus size={16} aria-hidden="true" /> Add another setup</button>
            <small>Use a separate setup for another method or filter.</small>
          </div>
        </section>
        <details className="panel sweep-measurements">
          <summary><span>Measurements</span><small>{metrics.length} selected</small><ChevronDown size={16} aria-hidden="true" /></summary>
          <fieldset className="metric-checklist" aria-label="Backbone measurements" disabled={busy}>
            {availableMetrics.map((name) => (
              <label key={name}>
                <input type="checkbox" checked={metrics.includes(name)} onChange={() => {
                  setMetrics((current) => current.includes(name) ? current.filter((item) => item !== name) : [...current, name]);
                  setError("");
                }} />
                <span>{metricLabel(name)}</span>
              </label>
            ))}
          </fieldset>
        </details>
        {listRuns && runCount > 0 && (
          <details className="panel sweep-measurements sweep-planned-runs">
            <summary><span>Runs</span><small>{runCount} planned</small><ChevronDown size={16} aria-hidden="true" /></summary>
            <ol>{plannedRuns(drafts, schema, environment).map((line, index) => <li key={index}>{line}</li>)}</ol>
          </details>
        )}
      </div>

      <footer className="sweep-action-bar" aria-label="Sweep actions">
        {error && <p className="error-text sweep-action-message" role="alert">{error}</p>}
        {!error && validation && <p className="sweep-action-message" role="status">{validation}</p>}
        <div className="sweep-action-row">
          <div className="sweep-run-count">
            <strong aria-live="polite">{runCount ? runCount + (runCount === 1 ? " run" : " runs") : "No runs planned"}</strong>
            <Hint label="How runs are counted">Netbone runs every combination of the values in a setup, so two cutoffs and three method values make six runs. A sweep can have up to {SWEEP_RUN_LIMIT} runs.</Hint>
          </div>
          <div className="sweep-stage-buttons">
            <button className="button button--save" disabled={busy || Boolean(validation)} onClick={() => void run()}>
              {busy ? <LoaderCircle className="spin" size={17} aria-hidden="true" /> : <Play size={16} fill="currentColor" aria-hidden="true" />}
              {busy ? "Running sweep…" : "Run sweep"}
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
        <span>{method?.label ?? draft.method} · {filterLabel(draft.filter)}</span>
      </div>
      <h2 id="vary-settings-title" ref={heading} tabIndex={-1}>What to vary?</h2>
      {draft.variations.length ? (
        <div className="sweep-variation-list">
          {draft.variations.map((variation, index) => (
            <VariationEditor
              key={variation.id}
              label={draft.variations.length > 1 ? "Setting " + (index + 1) : "Setting"}
              variation={variation}
              settings={settings.filter((item) => item.key === variation.key || !selectedKeys.has(item.key))}
              onSelect={(key) => {
                const setting = settings.find((item) => item.key === key);
                replaceVariation(variation.id, setting ? variationFor(draft, setting, variation.id) : { key, text: "" });
              }}
              onChange={(patch) => replaceVariation(variation.id, patch)}
              onRemove={() => onChange({ ...draft, variations: draft.variations.filter((item) => item.id !== variation.id) })}
            />
          ))}
        </div>
      ) : <p className="sweep-fixed-message">{settings.length
        ? "This setup runs once with fixed settings. Add a setting to test more values."
        : "This method and filter have no settings to vary. Change the method or filter, or add another setup."}</p>}
      {remaining.length > 0 && !hasUnselectedRow && (
        <button className="button button--quiet sweep-add-setting" onClick={addVariation}>
          <Plus size={16} aria-hidden="true" /> {draft.variations.length ? "Add another setting" : "Add a setting to vary"}
        </button>
      )}

      <details className="advanced-options sweep-fixed-settings">
        <summary>Method, filter and fixed settings <ChevronDown size={16} aria-hidden="true" /></summary>
        <div className="sweep-fixed-fields">
          <label className="field"><span>Setup name</span><input value={draft.name} onChange={(event) => onChange({ ...draft, name: event.target.value })} /></label>
          <div className="field-grid">
            <label className="field"><span>Method</span><select value={draft.method} onChange={(event) => {
              const selected = schema.methods.find((item) => item.name === event.target.value);
              if (selected) changeBase(selected.name, selected.recommended_filter);
            }}>
              {schema.methods.map((item) => <option key={item.name} value={item.name} disabled={!methodIsCompatible(item, environment)}>
                {item.label}{methodCompatibilityNote(item, environment)}
              </option>)}
            </select></label>
            <label className="field"><span>Filter</span><select value={draft.filter} onChange={(event) => changeBase(draft.method, event.target.value as FilterName)}>
              {schema.filters.filter((item) => item.name === "default" || item.name === draft.filter || filterNames.includes(item.name)).map((item) => <option key={item.name} value={item.name}>{filterLabel(item.name)}</option>)}
            </select></label>
          </div>
          {remaining.length > 0 && <div className="field-grid">{remaining.map((setting) => (
            <FixedSetting key={setting.key} setting={setting} value={fixedText(draft, setting)} onChange={(text) => onChange({ ...draft, fixed: { ...draft.fixed, [setting.key]: text } })} />
          ))}</div>}
          <div className="sweep-base-actions">
            <button className="button button--quiet" onClick={onDuplicate}><Copy size={15} aria-hidden="true" /> Duplicate setup</button>
            {onRemove && <button className="button button--quiet" onClick={onRemove}><Trash2 size={15} aria-hidden="true" /> Remove setup</button>}
          </div>
        </div>
      </details>
    </fieldset>
  );
}

function VariationEditor({ label, variation, settings, onSelect, onChange, onRemove }: {
  label: string;
  variation: SweepVariation;
  settings: SweepSetting[];
  onSelect: (key: string) => void;
  onChange: (patch: Partial<SweepVariation>) => void;
  onRemove: () => void;
}) {
  const setting = settings.find((item) => item.key === variation.key);
  return (
    <div className="sweep-variation">
      <div className="sweep-variation-header">
        <label className="field">
          <span>{label}</span>
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
        <button className="icon-button" title="Remove this setting" aria-label={"Remove " + (setting?.label.toLowerCase() ?? "this setting")} onClick={onRemove}><X size={17} aria-hidden="true" /></button>
      </div>
      {setting && (settingChoices(setting).length > 0
        ? <ChoiceValues setting={setting} text={variation.text} onChange={(text) => onChange({ text })} />
        : <NumberValues setting={setting} variation={variation} onChange={onChange} />)}
    </div>
  );
}

function ChoiceValues({ setting, text, onChange }: { setting: SweepSetting; text: string; onChange: (text: string) => void }) {
  const id = useId();
  const values = splitSweepValues(text);
  return (
    <div className="sweep-choice-fields">
      <span id={id}>Values</span>
      <div className="parameter-choices" role="group" aria-labelledby={id} aria-describedby={id + "-hint"}>
        {settingChoices(setting).map((choice) => (
          <button key={choice.value} aria-pressed={values.includes(choice.value)} onClick={() => onChange(
            (values.includes(choice.value) ? values.filter((item) => item !== choice.value) : [...values, choice.value]).join(", "),
          )}>{choice.label}</button>
        ))}
      </div>
      <small id={id + "-hint"}>Choose two or more.</small>
    </div>
  );
}

const RANGE_PARTS = [["from", "From"], ["to", "To"], ["step", "Step"]] as const;

/** Numbers start as a From/To/Step range. "List" takes any values, typed with commas. */
function NumberValues({ setting, variation, onChange }: { setting: SweepSetting; variation: SweepVariation; onChange: (patch: Partial<SweepVariation>) => void }) {
  const id = useId();
  const percent = isPercentSetting(setting);
  const mode = variation.mode ?? "list";
  const range = variation.range ?? defaultRange(setting, splitSweepValues(variation.text)[0] ?? "");
  const checked = settingRange(range, setting);

  function setRange(next: SweepRange) {
    onChange({ mode: "range", range: next, text: settingRange(next, setting).text || variation.text });
  }

  return (
    <div className="sweep-number-values">
      <div className="sweep-values-header">
        <span id={id}>Values</span>
        <div className="segmented segmented--small" role="group" aria-label={"How to enter " + setting.label.toLowerCase()}>
          <button aria-pressed={mode === "range"} onClick={() => mode !== "range" && setRange(range)}>Range</button>
          <button aria-pressed={mode === "list"} onClick={() => onChange({ mode: "list" })}>List</button>
        </div>
      </div>
      {mode === "range" ? <>
        <div className="sweep-range-fields" role="group" aria-labelledby={id}>
          {RANGE_PARTS.map(([part, name]) => (
            <label className="field" key={part}>
              <span>{name}{percent && <span className="visually-hidden"> in percent</span>}</span>
              <span className="number-with-unit">
                <input type="number" inputMode="decimal" step="any" value={range[part]} onChange={(event) => setRange({ ...range, [part]: event.target.value })} />
                {percent && <span aria-hidden="true">%</span>}
              </span>
            </label>
          ))}
        </div>
        <p className={checked.error ? "sweep-values-line is-error" : "sweep-values-line"} aria-live="polite">
          {checked.error || `${checked.values.length} values: ${checked.text}`}
        </p>
      </> : (
        <label className="field">
          <span className="visually-hidden">Values for {setting.label.toLowerCase()}</span>
          <input aria-describedby={id + "-hint"} value={variation.text} onChange={(event) => onChange({ text: event.target.value })} placeholder={percent ? "25%, 50%, 75%" : "Value 1, value 2, value 3"} />
          <small id={id + "-hint"}>{listHint(setting)}</small>
        </label>
      )}
    </div>
  );
}

function listHint(setting: SweepSetting): string {
  if (isPercentSetting(setting)) return "Two or more percentages, separated by commas.";
  if (setting.min !== undefined && setting.max !== undefined) return `Two or more values from ${setting.min} to ${setting.max}, separated by commas.`;
  return "Two or more values, separated by commas.";
}

function FixedSetting({ setting, value, onChange }: { setting: SweepSetting; value: string; onChange: (text: string) => void }) {
  const choices = settingChoices(setting);
  if (choices.length) {
    return <label className="field">
      <span>{setting.label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Use default</option>
        {choices.map((choice) => <option key={choice.value} value={choice.value}>{choice.label}</option>)}
      </select>
    </label>;
  }
  if (isPercentSetting(setting)) {
    // A retained fraction is typed in percent here too.
    const shown = value.trim().endsWith("%") ? value.trim().slice(0, -1).trim() : value.trim() ? String(Number((Number(value) * 100).toPrecision(12))) : "";
    return <label className="field">
      <span>{setting.label}<span className="visually-hidden"> in percent</span></span>
      <span className="number-with-unit">
        <input type="number" inputMode="decimal" step="any" min={0} max={100} value={shown} placeholder="Use default" onChange={(event) => onChange(event.target.value ? event.target.value + "%" : "")} />
        <span aria-hidden="true">%</span>
      </span>
    </label>;
  }
  return <label className="field">
    <span>{setting.label}</span>
    <input type="number" step="any" min={setting.min} max={setting.max} value={value} onChange={(event) => onChange(event.target.value)} placeholder="Use default" />
  </label>;
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

function SweepResults({ result, schema, heading, onBack, onEdit }: {
  result: SweepResponse;
  schema: UiSchema;
  heading: RefObject<HTMLHeadingElement | null>;
  onBack: () => void;
  onEdit: () => void;
}) {
  const figure = useSweepFigure(result, schema);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const settingsButton = useRef<HTMLButtonElement>(null);
  const closeDrawer = useCallback(() => {
    setDrawerOpen(false);
    settingsButton.current?.focus();
  }, []);
  const total = result.runs.length;
  const failed = result.runs.filter((run) => run.status === "failed").length;
  const experimentId = result.experiment_id;
  const downloads: DownloadItem[] = [
    { label: "Measurements (CSV)", onSelect: () => downloadCsv(result.metrics, "netbone-sweep-metrics.csv") },
    { label: "Runs (CSV)", onSelect: () => downloadCsv(result.runs, "netbone-sweep-runs.csv") },
    { label: "Settings (JSON)", onSelect: () => downloadJson(result.configuration, "netbone-sweep-config.json") },
    ...figure.downloads,
    ...(experimentId ? [{ label: "Full experiment (ZIP)", onSelect: () => downloadWorkspaceExperiment(experimentId) }] : []),
  ];
  return <main className="workspace sweep-workspace sweep-results-workspace" aria-labelledby="sweep-results-title">
    <BackLink onClick={onBack} />
    <header className="workspace-header">
      <div>
        <h1 id="sweep-results-title" ref={heading} tabIndex={-1}>Sweep results</h1>
        <p>{failed ? `${total - failed} of ${total} runs finished. ${failed} failed; the table says why.` : `${total} ${total === 1 ? "run" : "runs"} finished.`}</p>
      </div>
      <div className="figure-actions">
        <button ref={settingsButton} className="button button--quiet" onClick={() => setDrawerOpen(true)}><Settings2 size={16} aria-hidden="true" /> Run settings</button>
        <button className="button button--quiet" onClick={onEdit}><Pencil size={16} aria-hidden="true" /> Edit sweep</button>
        <DownloadMenu items={downloads} />
      </div>
    </header>
    <SweepVisualizations figure={figure} />
    <section className="panel sweep-table-panel" aria-labelledby="sweep-table-title">
      <header><div><h2 id="sweep-table-title">Measurements</h2><p>One row for each run.</p></div></header>
      <SweepTable result={result} labels={figure.runLabels} />
    </section>
    {drawerOpen && <RunSettingsDrawer result={result} schema={schema} onClose={closeDrawer} />}
  </main>;
}

/** The settings of every run, said once per setup. A setting the sweep changed lists each value it took. */
function RunSettingsDrawer({ result, schema, onClose }: { result: SweepResponse; schema: UiSchema; onClose: () => void }) {
  const close = useRef<HTMLButtonElement>(null);
  const configurations = (result.configuration.configurations || {}) as JsonRecord;
  const setups = new Map<string, JsonRecord[]>();
  for (const run of result.runs) {
    const name = String(run.pipeline_name);
    const configuration = configurations[name];
    const setup = result.setup_names[name] || name;
    if (configuration && typeof configuration === "object" && !Array.isArray(configuration)) setups.set(setup, [...(setups.get(setup) ?? []), configuration]);
  }
  useEffect(() => {
    close.current?.focus();
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);
  return <>
    <button className="drawer-scrim" tabIndex={-1} aria-hidden="true" onClick={onClose} />
    <aside className="configuration-drawer" role="dialog" aria-modal="true" aria-labelledby="run-settings-title">
      <header>
        <h2 id="run-settings-title">Run settings</h2>
        <button ref={close} className="icon-button" title="Close" aria-label="Close run settings" onClick={onClose}><X size={18} aria-hidden="true" /></button>
      </header>
      <div className="configuration-drawer-list">{[...setups].map(([setup, runs]) => (
        <section key={setup}>
          {setups.size > 1 && <h3>{setup} <small>· {runs.length} {runs.length === 1 ? "run" : "runs"}</small></h3>}
          <SettingsList described={mergeDescriptions(runs.map((configuration) => describeConfiguration(configuration, schema)))} />
        </section>
      ))}</div>
    </aside>
  </>;
}

/** One row per run and one column per measurement. Notes appear only when something is missing. */
function SweepTable({ result, labels }: { result: SweepResponse; labels: Map<number, string> }) {
  const metrics = [...new Set(result.metrics.map((row) => row.metric).filter((name): name is string => typeof name === "string"))];
  const cells = new Map(result.metrics.filter((row) => typeof row.metric === "string").map((row) => [`${row.run_id}\u0000${row.metric}`, row]));
  const rows = result.runs.map((run) => {
    const id = Number(run.run_id);
    const values = metrics.map((metric) => {
      const cell = cells.get(`${id}\u0000${metric}`);
      return cell?.status === "ok" && typeof cell.value === "number" && Number.isFinite(cell.value) ? cell.value : null;
    });
    const notes = run.status === "failed"
      ? [String(run.explanation || run.failure_detail || "This run failed.")]
      : metrics.flatMap((metric, index) => values[index] !== null ? [] : [`${metricLabel(metric)}: ${String(cells.get(`${id}\u0000${metric}`)?.explanation || "unavailable.")}`]);
    return { id, label: labels.get(id) ?? `Run ${id}`, values, notes: notes.join(" ") };
  });
  const hasNotes = rows.some((row) => row.notes);
  return <div className="table-wrap"><table>
    <thead><tr><th>Run</th>{metrics.map((metric) => <th key={metric} className="is-numeric">{metricLabel(metric)}</th>)}{hasNotes && <th>Notes</th>}</tr></thead>
    <tbody>{rows.map((row) => (
      <tr key={row.id}>
        <td className="sweep-run-label">{row.label}</td>
        {row.values.map((value, index) => <td key={metrics[index]} className="is-numeric">{formatMetric(metrics[index] ?? "", value)}</td>)}
        {hasNotes && <td>{row.notes}</td>}
      </tr>
    ))}</tbody>
  </table></div>;
}
