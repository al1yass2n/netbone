import {
  Archive,
  ArrowLeft,
  ArrowRight,
  BarChart3,
  Check,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  Clock3,
  Download,
  FileJson,
  GitCompareArrows,
  LoaderCircle,
  Moon,
  Network,
  Play,
  Plus,
  Search,
  Settings2,
  SlidersHorizontal,
  Sun,
  Upload,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent } from "react";
import { api, downloadExperiment, downloadGraph, downloadJson } from "./api";
import { ComparisonWorkspace } from "./components/ComparisonWorkspace";
import { ControlField } from "./components/ControlField";
import { Hint } from "./components/Hint";
import LauncherBackdrop from "./components/LauncherBackdrop";
import { NetworkPreview } from "./components/NetworkPreview";
import { ScoreDistribution } from "./components/ScoreDistribution";
import { StatisticsTable } from "./components/StatisticsTable";
import { SweepWorkspace } from "./components/ConfigurationSweepWorkspace";
import "./components/NetworkLauncher.css";
import { defaultContext, emptyDataDraft, guidedExamples } from "./examples";
import { shortBackboneLabel, uniqueResultLabel } from "./savedBackbones";
import type {
  ControlSpec,
  ControlValue,
  DataDraft,
  ExtractionResponse,
  FilterName,
  FilterPreview,
  JsonRecord,
  MethodSpec,
  NetworkContext,
  PreviewResponse,
  SavedResult,
  ScoreResponse,
  UiSchema,
  Workspace,
} from "./types";
import {
  buildPayload,
  contextualMeaning,
  detectDelimiter,
  filterOptions,
  formatPercent,
  formatValue,
  guessColumn,
  initialControlValues,
  methodCompatibilityReason,
  parseHeaders,
} from "./utils";

import { demoMode, loadDemo } from "./demo-api";

export default function App() {
  const [schema, setSchema] = useState<UiSchema | null>(null);
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    try {
      return localStorage.getItem("netbone-theme") === "dark" ? "dark" : "light";
    } catch {
      return "light";
    }
  });
  const [workspace, setWorkspace] = useState<Workspace>(demoMode ? "analysis" : "start");
  const [data, setData] = useState<DataDraft>({ ...emptyDataDraft });
  const [context, setContext] = useState<NetworkContext>({ ...defaultContext });
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);
  const [methodName, setMethodName] = useState("");
  const [methodControls, setMethodControls] = useState<Record<string, ControlValue>>({});
  const [filterName, setFilterName] = useState<FilterName>("fraction");
  const [filterChosen, setFilterChosen] = useState(false);
  const [filterControls, setFilterControls] = useState<Record<string, ControlValue>>({});
  const [score, setScore] = useState<ScoreResponse | null>(null);
  const [filterPreview, setFilterPreview] = useState<FilterPreview | null>(null);
  const [filterPreviewError, setFilterPreviewError] = useState("");
  const [result, setResult] = useState<ExtractionResponse | null>(null);
  const [savedResults, setSavedResults] = useState<SavedResult[]>([]);
  const [busy, setBusy] = useState<"score" | "filter" | "">("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [methodSearch, setMethodSearch] = useState("");
  const [mappingReviewPending, setMappingReviewPending] = useState(false);
  const importInput = useRef<HTMLInputElement>(null);
  const graphmlWeightDetected = useRef(false);
  const hasData = Boolean(data.text);
  const analysisOpen = workspace !== "start";

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [workspace]);

  useEffect(() => {
    const initialize = demoMode ? loadDemo().then((demo) => {
      const baseline = Object.values(demo.runs).filter(({ result }) => demo.baseline.includes(result.result_id));
      const first = baseline[0];
      const initialMethod = demo.schema.methods.find(({ name }) => name === first?.result.extraction.method);
      const initialScore = initialMethod && demo.scores[initialMethod.name];
      if (!first || !initialMethod || !initialScore) throw new Error("The demo results are incomplete.");
      setData({ ...emptyDataDraft, mode: "graphml", text: demo.graphml, filename: "karate-club.graphml", weight: "weight" });
      setContext({
        ...defaultContext,
        dataset: "Zachary’s Karate Club",
        nodes: "club members",
        edges: "interactions",
        weight: "interaction contexts",
        weightSemantics: "strength",
      });
      setPreview(demo.preview);
      setMethodName(initialMethod.name);
      setFilterControls(filterDefaults(demo.schema, "fraction", initialMethod, initialScore));
      setFilterChosen(true);
      setScore(initialScore);
      setResult(first.result);
      setSavedResults(baseline.map(({ result }) => ({
        resultId: result.result_id, label: shortBackboneLabel(result), selected: true, result,
      })));
      setSchema(demo.schema);
    }) : api.schema().then(setSchema);
    initialize
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Could not load the UI schema."));
  }, []);

  const method = useMemo(
    () => schema?.methods.find((item) => item.name === methodName) || null,
    [schema, methodName],
  );
  const effectiveDirected = Boolean(preview?.directed);
  const weighted = data.mode === "temporal" || Boolean(data.weight);
  const positiveIntegerWeights = preview?.positive_integer_weights;
  const methodCompatibility = useCallback((candidate: MethodSpec) => methodCompatibilityReason(
    candidate, { directed: effectiveDirected, weighted, positiveIntegerWeights },
  ), [effectiveDirected, weighted, positiveIntegerWeights]);

  const combinedControls = useMemo(
    () => ({ ...methodControls, ...filterControls }),
    [methodControls, filterControls],
  );
  const currentPayload = useCallback(
    () => buildPayload(data, context, method, filterName, combinedControls),
    [data, context, method, filterName, combinedControls],
  );
  const previewPayload = useCallback(
    () => buildPayload(data, context, null, "fraction", {}),
    [data, context],
  );

  useEffect(() => {
    if (demoMode || !schema || !data.text || !analysisOpen) return;
    let cancelled = false;
    setPreviewBusy(true);
    const timer = window.setTimeout(async () => {
      try {
        const nextPreview = await api.preview(previewPayload());
        if (cancelled) return;
        setPreview(nextPreview);
        if (data.mode === "graphml") {
          const attributes = nextPreview.numeric_edge_attributes || [];
          const detectWeight = !graphmlWeightDetected.current && nextPreview.valid;
          if (detectWeight) graphmlWeightDetected.current = true;
          setData((current) => {
            const weight = detectWeight ? current.weight || attributes[0] || "" : current.weight;
            const directed = nextPreview.source_directed === true;
            if (weight === current.weight && directed === current.directed) return current;
            return { ...current, weight, directed };
          });
        }
      } catch (reason) {
        if (cancelled) return;
        setPreview({ valid: false, can_run: false, errors: [errorMessage(reason)] });
      } finally {
        if (!cancelled) setPreviewBusy(false);
      }
    }, 280);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [schema, data.text, analysisOpen, previewPayload]);

  useEffect(() => {
    if (!score?.score_id || !method || !filterChosen) {
      setFilterPreview(null);
      setFilterPreviewError("");
      return;
    }
    setFilterPreview(null);
    setFilterPreviewError("");
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        const nextPreview = await api.filterPreview({ score_id: score.score_id, guided: currentPayload().guided! });
        if (![nextPreview.backbone_edge_count, nextPreview.original_edge_count, nextPreview.backbone_component_count].every(Number.isFinite)
          || nextPreview.graph?.nodes.some((node) => node.retained && node.component == null)) {
          throw new Error("The preview server is out of date. Open the latest local Netbone server and compute scores again.");
        }
        if (!cancelled) setFilterPreview(nextPreview);
      } catch (reason) {
        if (!cancelled) setFilterPreviewError(errorMessage(reason));
      }
    }, 180);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [score, method, filterChosen, filterName, filterControls, currentPayload]);

  function selectMethod(selected: MethodSpec) {
    if (!schema || !preview?.can_run || previewBusy || busy || methodCompatibility(selected) || (weighted && !context.weightSemantics)) return;
    setMethodName(selected.name);
    const controls = initialControlValues(resolvedControls(schema.controls.methods[selected.name] || [], data, effectiveDirected, context));
    setMethodControls(controls);
    setFilterName(selected.recommended_filter);
    setFilterChosen(false);
    const defaults = filterDefaults(schema, selected.recommended_filter, selected);
    setFilterControls(defaults);
    setScore(null);
    setFilterPreview(null);
    setResult(null);
    void scoreMethod(selected, buildPayload(data, context, selected, selected.recommended_filter, { ...controls, ...defaults }));
  }

  function chooseFilter(name: FilterName) {
    if (!schema || !method || !score || (filterChosen && name === filterName)) return;
    setFilterName(name);
    setFilterChosen(true);
    setFilterControls(filterDefaults(schema, name, method, score));
    setFilterPreview(null);
    setResult(null);
  }

  function loadExample(name: string) {
    const example = guidedExamples.find((item) => item.name === name);
    if (!example) return;
    setData({ ...example.data, temporalParameters: { ...example.data.temporalParameters } });
    setContext({ ...example.context });
    resetAnalysis();
    setMappingReviewPending(false);
    setWorkspace("analysis");
  }

  async function importFile(file: File) {
    const text = await file.text();
    if (!text.trim()) throw new Error("This file is empty. Choose a network file with data.");
    const graphml = /\.(graphml|xml)$/i.test(file.name);
    const mode = graphml ? "graphml" : "static";
    const delimiter = graphml ? "," : detectDelimiter(file.name, text);
    const headers = graphml ? [] : parseHeaders(text, delimiter);
    setData({
      ...emptyDataDraft,
      mode,
      text,
      filename: file.name,
      delimiter,
      source: guessColumn(headers, ["source", "from", "src", "origin"], 0),
      target: guessColumn(headers, ["target", "to", "dst", "destination"], 1),
      weight: guessColumn(headers, ["weight", "strength", "value", "flow", "volume"], null),
    });
    setContext({ ...defaultContext, dataset: file.name.replace(/\.[^.]+$/, "") });
    resetAnalysis();
    setMappingReviewPending(true);
    setWorkspace("analysis");
  }

  function openNetworkFile(file: File) {
    void importFile(file).catch((reason: unknown) => setError(errorMessage(reason)));
  }

  function resetAnalysis() {
    setMethodName("");
    setMethodControls({});
    setFilterChosen(false);
    graphmlWeightDetected.current = false;
    setPreview(null);
    setScore(null);
    setFilterPreview(null);
    setResult(null);
    setSavedResults([]);
    setMessage("");
    setError("");
    setMethodSearch("");
  }

  function updateData(patch: Partial<DataDraft>, invalidate = true) {
    if ((patch.mode !== undefined && patch.mode !== data.mode)
      || (patch.weight !== undefined && patch.weight !== data.weight)
      || (patch.eventWeight !== undefined && patch.eventWeight !== data.eventWeight)) {
      setContext((current) => ({ ...current, weightSemantics: "" }));
    }
    setData((current) => ({ ...current, ...patch }));
    if (invalidate) {
      setPreview(null);
      setScore(null);
      setFilterPreview(null);
      setResult(null);
    }
  }

  function updateContext(patch: Partial<NetworkContext>) {
    const semantics = patch.weightSemantics;
    if (semantics && semantics !== context.weightSemantics && method
      && schema?.controls.methods[method.name]?.some((control) => control.name === "distance_transform")) {
      setMethodControls((current) => ({ ...current, distance_transform: semantics === "distance" ? "identity" : "inverse" }));
    }
    setContext((current) => ({ ...current, ...patch }));
    setScore(null);
    setFilterPreview(null);
    setResult(null);
  }

  function computeScores() {
    if (!method || !preview?.can_run || previewBusy || busy || methodCompatibility(method) || (weighted && !context.weightSemantics)) return;
    void scoreMethod(method, currentPayload());
  }

  async function scoreMethod(scoringMethod: MethodSpec, payload: JsonRecord) {
    setBusy("score");
    setError("");
    setMessage(`Computing ${scoringMethod.label} scores…`);
    try {
      const nextScore = await api.score(payload);
      setFilterChosen(demoMode);
      setScore(nextScore);
      setResult(null);
      setMessage(`${nextScore.score_summary.score_row_count} ${scoringMethod.target} scores are ready.`);
    } catch (reason) {
      setError(errorMessage(reason));
      setMessage("");
    } finally {
      setBusy("");
    }
  }

  async function materializeBackbone(save: boolean) {
    if (!score?.score_id || !filterChosen) return;
    if (result) {
      if (save) saveBackbone(result);
      return;
    }
    setBusy("filter");
    setError("");
    setMessage("Applying the retention rule to the existing scores...");
    try {
      const extraction = await api.filter({ score_id: score.score_id, guided: currentPayload().guided! });
      setResult(extraction);
      if (save) saveBackbone(extraction);
      else setMessage("Backbone ready to inspect and export.");
    } catch (reason) {
      setError(errorMessage(reason));
      setMessage("");
    } finally {
      setBusy("");
    }
  }

  function saveBackbone(extraction: ExtractionResponse) {
    const normalized = uniqueResultLabel(shortBackboneLabel(extraction), savedResults, extraction.result_id);
    setSavedResults((current) => current.some((item) => item.resultId === extraction.result_id)
      ? current
      : [...current, {
        resultId: extraction.result_id,
        label: normalized,
        selected: true,
        result: extraction,
      }]);
    setMessage(`${normalized} saved for comparison.`);
  }

  if (!schema) {
    return (
      <div className="boot-state">
        <LoaderCircle className="spin" size={28} />
        <strong>Loading Netbone...</strong>
        {error && <span>{error}</span>}
      </div>
    );
  }

  const nextTheme = theme === "dark" ? "light" : "dark";
  const themeButton = (
    <button type="button" className="theme-toggle" onClick={() => {
      setTheme(nextTheme);
      try { localStorage.setItem("netbone-theme", nextTheme); } catch { /* Theme switching still works for this visit. */ }
    }}>
      {nextTheme === "dark" ? <Moon size={16} aria-hidden="true" /> : <Sun size={16} aria-hidden="true" />}
      {nextTheme === "dark" ? "Dark theme" : "Light theme"}
    </button>
  );

  return (
    <div className={`app-shell app-shell--${workspace === "start" ? "launcher" : workspace}`} data-theme={theme}>
      {workspace === "start" && <div className="launcher-theme">{themeButton}</div>}
      {workspace !== "start" && (
        <header className="app-header app-header--start single-workbench-header">
          {workspace === "analysis" ? (
            <span className="brand"><strong>{demoMode ? "Netbone demo" : "Netbone"}</strong></span>
          ) : (
            <button className="brand" disabled={busy !== ""} onClick={() => setWorkspace("analysis")}>
              <span className="brand-mark"><Network size={20} aria-hidden="true" /></span>
              <span><strong>Netbone</strong><small>Network workbench</small></span>
            </button>
          )}
          <div className="workbench-header-actions">
            {themeButton}
            {demoMode && <a className="button button--quiet" href="../browser/launch/">Run locally</a>}
            {!demoMode && hasData && workspace === "analysis" && <button className="button button--quiet new-analysis" disabled={busy !== ""} onClick={() => { setError(""); setWorkspace("start"); }}>
              Change network
            </button>}
            {hasData && workspace !== "analysis" && <button className="button button--quiet new-analysis" onClick={() => setWorkspace("analysis")}><ArrowLeft size={16} /> Back to analysis</button>}
          </div>
        </header>
      )}

      {workspace === "start" && (
        <StartWorkspace
          onExample={loadExample}
          onImport={() => importInput.current?.click()}
          onDropFile={openNetworkFile}
          onBack={hasData ? () => setWorkspace("analysis") : undefined}
          error={error}
        />
      )}
      {workspace === "analysis" && (
        <AnalysisWorkspace
          schema={schema}
          data={data}
          context={context}
          preview={preview}
          previewBusy={previewBusy}
          mappingReviewPending={mappingReviewPending}
          onMappingReviewFinished={() => setMappingReviewPending(false)}
          method={method}
          methods={schema.methods}
          methodSearch={methodSearch}
          methodControls={methodControls}
          filterName={filterName}
          filterChosen={filterChosen}
          filterControls={filterControls}
          score={score}
          filterPreview={filterPreview}
          filterPreviewError={filterPreviewError}
          result={result}
          saved={savedResults.some((item) => item.resultId === result?.result_id)}
          savedCount={savedResults.length}
          busy={busy}
          message={message}
          error={error}
          compatibility={methodCompatibility}
          onSearch={setMethodSearch}
          onMethod={selectMethod}
          onMethodControl={(name, value) => { setMethodControls((current) => ({ ...current, [name]: value })); setScore(null); setFilterPreview(null); setResult(null); }}
          onFilter={chooseFilter}
          onFilterControl={(name, value) => { setFilterControls((current) => ({ ...current, [name]: value })); setFilterPreview(null); setResult(null); }}
          onScore={computeScores}
          onMaterialize={materializeBackbone}
          onData={updateData}
          onContext={updateContext}
          onImport={() => importInput.current?.click()}
          onCompare={() => setWorkspace("compare")}
          onSweep={() => setWorkspace("sweep")}
        />
      )}
      {workspace === "compare" && (
        <ComparisonWorkspace saved={savedResults} onChange={setSavedResults} onExtract={() => setWorkspace("analysis")} />
      )}
      {workspace === "sweep" && preview?.can_run && method && (
        <SweepWorkspace
          schema={schema}
          method={method}
          filterName={filterName}
          directed={Boolean(preview.directed)}
          weighted={weighted}
          positiveIntegerWeights={positiveIntegerWeights}
          basePayload={currentPayload()}
          initialConfiguration={result?.resolved_config ?? filterPreview?.resolved_config}
        />
      )}

      {!demoMode && <input
        ref={importInput}
        hidden
        type="file"
        accept=".csv,.tsv,.txt,.graphml,.xml"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) openNetworkFile(file);
          event.target.value = "";
        }}
      />}
      <footer className="citation-footer">
        <a href="https://doi.org/10.1038/s41598-023-42076-3">Cite Netbone</a>
        <span>Yassin et al. · Scientific Reports (2023)</span>
      </footer>
    </div>
  );
}

const illustrationNodes = [[42, 145], [94, 50], [117, 218], [164, 116], [206, 39], [224, 263], [258, 169], [307, 74], [358, 240], [370, 132], [417, 62], [438, 182], [491, 112]];
const illustrationRetained = [[1, 3], [2, 3], [3, 6], [6, 7], [6, 8], [7, 9], [9, 11]] as const;
const illustrationExcluded = [[0, 1], [0, 2], [0, 3], [1, 4], [1, 6], [2, 5], [3, 4], [3, 7], [4, 7], [5, 6], [5, 8], [6, 9], [6, 11], [7, 10], [8, 9], [8, 11], [9, 10], [10, 11], [10, 12], [11, 12]] as const;

function StartWorkspace({ onExample, onImport, onDropFile, onBack, error }: {
  onExample: (name: string) => void;
  onImport: () => void;
  onDropFile: (file: File) => void;
  onBack?: () => void;
  error: string;
}) {
  const [dragging, setDragging] = useState(false);
  const [dropError, setDropError] = useState("");

  return (
    <main className="network-launcher" aria-labelledby="start-title">
      <LauncherBackdrop />
      <div className="launcher-content">
        <header className="launcher-intro">
          <h1 id="start-title">Find the structure within.</h1>
          <p>One network, different backbones.</p>
        </header>
        <div className="launcher-actions">
          <button
            type="button"
            className="launcher-action launcher-open"
            data-dragging={dragging}
            aria-describedby="launcher-drop-hint"
            onClick={() => { setDropError(""); onImport(); }}
            onDragOver={(event) => {
              if (!event.dataTransfer.types.includes("Files")) return;
              event.preventDefault();
              event.dataTransfer.dropEffect = "copy";
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              const files = event.dataTransfer.files;
              if (!files.length) return;
              if (files.length !== 1) {
                setDropError("Drop one network file at a time.");
                return;
              }
              const file = files[0];
              if (file) {
                setDropError("");
                onDropFile(file);
              }
            }}
          >
            <Upload size={18} aria-hidden="true" />
            Open a network
          </button>
          <span id="launcher-drop-hint" className="visually-hidden">You can also drop a file onto this button.</span>
          <details
            className="launcher-examples"
            onKeyDown={(event) => {
              if (event.key !== "Escape" || !event.currentTarget.open) return;
              event.currentTarget.open = false;
              event.currentTarget.querySelector("summary")?.focus();
            }}
          >
            <summary className="launcher-action launcher-example-trigger">
              Try an example
              <ChevronDown size={16} aria-hidden="true" />
            </summary>
            <div className="launcher-example-list">
              {guidedExamples.map((example) => {
                const Icon = example.name === "temporal" ? Clock3 : example.name === "weighted" ? SlidersHorizontal : Network;
                return (
                  <button key={example.name} type="button" onClick={() => onExample(example.name)}>
                    <span className="launcher-example-icon" data-example={example.name}><Icon size={18} aria-hidden="true" /></span>
                    <span className="launcher-example-text"><strong>{example.label}</strong><small>{example.description}</small></span>
                    <ArrowRight size={16} aria-hidden="true" />
                  </button>
                );
              })}
            </div>
          </details>
        </div>
        {(dropError || error) && <p className="launcher-error" role="alert">{dropError || error}</p>}
        {onBack && (
          <button type="button" className="launcher-action launcher-return" onClick={onBack}>
            <ArrowLeft size={16} aria-hidden="true" />
            Back to analysis
          </button>
        )}
      </div>
    </main>
  );
}

function BackboneIllustration() {
  return (
    <svg viewBox="0 0 534 306" focusable="false" aria-hidden="true">
      {[illustrationExcluded, illustrationRetained].map((links, index) => (
        <g key={index} className={index === 1 ? "illustration-backbone" : "illustration-context"}>
          {links.map(([from, to]) => <line key={`${from}-${to}`} x1={illustrationNodes[from]?.[0]} y1={illustrationNodes[from]?.[1]} x2={illustrationNodes[to]?.[0]} y2={illustrationNodes[to]?.[1]} />)}
        </g>
      ))}
      {illustrationNodes.map(([x, y], index) => <circle key={index} cx={x} cy={y} r={index === 6 ? 9 : 5} className={illustrationRetained.some(([from, to]) => from === index || to === index) ? "illustration-node is-retained" : "illustration-node"} />)}
    </svg>
  );
}

interface NetworkSettingsProps {
  data: DataDraft;
  context: NetworkContext;
  preview: PreviewResponse | null;
  busy: boolean;
  schema: UiSchema;
  onData: (patch: Partial<DataDraft>, invalidate?: boolean) => void;
  onContext: (patch: Partial<NetworkContext>) => void;
  onImport: () => void;
}

function NetworkSettings({ data, context, preview, busy, schema, onData, onContext }: NetworkSettingsProps) {
  const [mappingExpanded, setMappingExpanded] = useState(false);
  const headers = useMemo(() => data.mode === "graphml" ? [] : parseHeaders(data.text, data.delimiter), [data.mode, data.text, data.delimiter]);
  const numericAttributes = preview?.numeric_edge_attributes || [];
  const temporalSpec = schema.temporal.weightings.find((item) => item.name === data.temporalWeighting);
  const temporalControls = schema.temporal.controls[data.temporalWeighting] || [];
  const previewOkay = preview?.valid === true && preview.can_run === true;
  const showMapping = mappingExpanded || Boolean(preview && !previewOkay);
  const formatLabel = data.mode === "graphml" ? "GraphML" : data.mode === "temporal" ? "Temporal event list" : "Edge list";

  function changeColumns(patch: Partial<DataDraft>) {
    setMappingExpanded(true);
    onData(patch);
  }

  function changeMode(mode: DataDraft["mode"]) {
    const nextHeaders = mode === "graphml" ? [] : parseHeaders(data.text, data.delimiter);
    changeColumns({
      mode,
      source: mode === "graphml" ? data.source : guessColumn(nextHeaders, ["source", "from", "src", "origin"], 0),
      target: mode === "graphml" ? data.target : guessColumn(nextHeaders, ["target", "to", "dst", "destination"], 1),
      time: mode === "temporal" ? guessColumn(nextHeaders, ["time", "timestamp", "date", "snapshot"], 2) : data.time,
      eventWeight: mode === "temporal" ? guessColumn(nextHeaders, ["event_weight", "magnitude", "weight", "value"], null) : data.eventWeight,
    });
  }

  return (
      <div className="network-settings-stack">
        <section className="panel mapping-panel" aria-labelledby="mapping-title">
          <div className="pane-heading">
            <div><h3 id="mapping-title">{data.mode === "graphml" ? "Graph settings" : showMapping ? "Map the network" : "Detected mapping"}</h3>{!showMapping && <p>{formatLabel}</p>}</div>
            <button className="button button--configure" disabled={showMapping && (!previewOkay || busy)} aria-controls="network-column-mapping" onClick={() => setMappingExpanded(!showMapping)}>{showMapping ? "Finish editing" : "Change mapping"}</button>
          </div>
          {!showMapping && (
            <dl className="mapping-list" id="network-column-mapping">
              {data.mode !== "graphml" && <>
                <div><dt>Source</dt><dd>{data.source || "Choose a column"}</dd></div>
                <div><dt>Target</dt><dd>{data.target || "Choose a column"}</dd></div>
              </>}
              {data.mode === "temporal" ? <>
                <div><dt>Time</dt><dd>{data.time || "Choose a column"}</dd></div>
                <div><dt>Event magnitude</dt><dd>{data.eventWeight || "Unit magnitude"}</dd></div>
              </> : <div><dt>{data.mode === "graphml" ? "Weight attribute" : "Weight"}</dt><dd>{data.weight || "Unweighted"}</dd></div>}
              <div><dt>Input direction</dt><dd>{data.directed ? "Directed" : "Undirected"}</dd></div>
            </dl>
          )}
          {showMapping && (
            <div className="field-grid" id="network-column-mapping">
              <label className="field"><span>Input format</span><select value={data.mode} onChange={(event) => changeMode(event.target.value as DataDraft["mode"])}>
                <option value="static">Edge list</option><option value="temporal">Temporal event list</option><option value="graphml">GraphML</option>
              </select></label>
              {data.mode === "graphml" ? <SelectField label="Numeric edge attribute" value={data.weight} options={numericAttributes} optional="Unweighted" onChange={(weight) => onData({ weight })} /> : <>
              <SelectField label="Source" value={data.source} options={headers} onChange={(source) => changeColumns({ source })} />
              <SelectField label="Target" value={data.target} options={headers} onChange={(target) => changeColumns({ target })} />
              {data.mode === "temporal" ? (
                <>
                  <SelectField label="Time" value={data.time} options={headers} onChange={(time) => changeColumns({ time })} />
                  <SelectField label="Event magnitude" value={data.eventWeight} options={headers} optional="Unit magnitude" onChange={(eventWeight) => changeColumns({ eventWeight })} />
                </>
              ) : <SelectField label="Weight" value={data.weight} options={headers} optional="Unweighted" onChange={(weight) => changeColumns({ weight })} />}
              <label className="field"><span>Delimiter</span><select value={data.delimiter} onChange={(event) => changeColumns({ delimiter: event.target.value })}><option value=",">Comma</option><option value=";">Semicolon</option><option value={"\t"}>Tab</option></select></label>
              <label className="toggle-row compact"><span><strong>Directed network</strong><small>Preserve source-to-target arcs.</small></span><input type="checkbox" checked={data.directed} onChange={(event) => changeColumns({ directed: event.target.checked })} /><i /></label>
              </>}
            </div>
          )}
          {(data.directed || preview?.source_directed) && (
            <div className="direction-settings">
              <label className="field"><span>Direction handling</span><select value={data.directionMode} onChange={(event) => onData({ directionMode: event.target.value as DataDraft["directionMode"] })}><option value="preserve">Keep directed arcs</option><option value="undirected">Convert to undirected</option></select></label>
              {data.directionMode === "undirected" && <label className="field"><span>Reciprocal weights</span><select value={data.reciprocalMerge} onChange={(event) => onData({ reciprocalMerge: event.target.value as DataDraft["reciprocalMerge"] })}><option value="sum">Sum</option><option value="mean">Mean</option><option value="max">Maximum</option><option value="min">Minimum</option></select></label>}
            </div>
          )}
          {data.mode === "temporal" && (
            <div className="temporal-panel">
              <div className="section-divider"><span>TEMPORAL WEIGHTING</span></div>
              <label className="field"><span>Weighting</span><select value={data.temporalWeighting} onChange={(event) => {
                const weighting = schema.temporal.weightings.find((item) => item.name === event.target.value);
                onData({ temporalWeighting: event.target.value, temporalParameters: { ...(weighting?.default_parameters || {}) } });
              }}>{schema.temporal.weightings.map((item) => <option key={item.name} value={item.name}>{item.label}</option>)}</select><small>{temporalSpec?.description}</small></label>
              <div className="field-grid">{temporalControls.map((control) => <ControlField key={control.name} control={control} value={data.temporalParameters[control.name]} onChange={(name, value) => onData({ temporalParameters: { ...data.temporalParameters, [name]: value } })} />)}</div>
            </div>
          )}
          {!busy && preview && <NetworkReadiness preview={preview} />}
        </section>
        {(data.mode === "temporal" || data.weight) && (
          <fieldset className="choice-field weight-meaning" aria-describedby="weight-meaning-description">
            <legend>What do higher weights mean?</legend>
            <p id="weight-meaning-description">Choose one to set the default for shortest-path methods.</p>
            <div className="choice-grid choice-grid--compact">
              <label className="choice-option">
                <input type="radio" name="weight-meaning" value="strength" required checked={context.weightSemantics === "strength"} onChange={() => onContext({ weightSemantics: "strength" })} />
                <span><strong>Strength</strong><small>Stronger or more frequent ties, such as more messages.</small></span>
              </label>
              <label className="choice-option">
                <input type="radio" name="weight-meaning" value="distance" required checked={context.weightSemantics === "distance"} onChange={() => onContext({ weightSemantics: "distance" })} />
                <span><strong>Distance or cost</strong><small>Longer or costlier ties, such as more travel time.</small></span>
              </label>
            </div>
          </fieldset>
        )}
        <details className="advanced-options network-source-preview">
          <summary>Source preview</summary>
          <div className="network-source-content">
          {preview?.records && preview.records.length > 0 && data.mode !== "graphml" && (
            <DataSample
              records={preview.records}
              headers={headers}
              mappedColumns={data.mode === "temporal" ? [data.source, data.target, data.time, data.eventWeight] : [data.source, data.target, data.weight]}
            />
          )}
          {data.mode === "graphml" && (
            <div className="graphml-summary">
              <Network size={28} />
              <div><strong>GraphML structure</strong><small>{formatValue(preview?.node_count)} nodes · {formatValue(preview?.edge_count)} {preview?.directed ? "arcs" : "edges"} · {numericAttributes.length} numeric edge attributes</small></div>
            </div>
          )}
          {data.mode !== "graphml" && !preview?.records?.length && <p>{busy || !preview ? "Checking file…" : "Sample rows are available after the mapping is valid."}</p>}
          </div>
        </details>
          <details className="context-details">
            <summary><span><strong>Describe this network</strong><small>Optional context improves method explanations.</small></span><ChevronRight size={16} /></summary>
            <div className="context-fields">
              <label className="field"><span>Dataset</span><input value={context.dataset} onChange={(event) => onContext({ dataset: event.target.value })} /></label>
              <div className="field-grid">
                <label className="field"><span>Nodes represent</span><input value={context.nodes} onChange={(event) => onContext({ nodes: event.target.value })} /></label>
                <label className="field"><span>{data.directed ? "Arcs" : "Edges"} represent</span><input value={context.edges} onChange={(event) => onContext({ edges: event.target.value })} /></label>
              </div>
              {(data.mode === "temporal" || data.weight) && (
                <label className="field"><span>Weight represents</span><input value={context.weight} onChange={(event) => onContext({ weight: event.target.value })} /></label>
              )}
              {data.mode === "temporal" && <label className="field"><span>Time represents</span><input value={context.time} onChange={(event) => onContext({ time: event.target.value })} /></label>}
            </div>
          </details>
      </div>
  );
}

interface AnalysisWorkspaceProps extends Omit<NetworkSettingsProps, "busy"> {
  previewBusy: boolean;
  mappingReviewPending: boolean;
  onMappingReviewFinished: () => void;
  method: MethodSpec | null;
  methods: MethodSpec[];
  methodSearch: string;
  methodControls: Record<string, ControlValue>;
  filterName: FilterName;
  filterChosen: boolean;
  filterControls: Record<string, ControlValue>;
  score: ScoreResponse | null;
  filterPreview: FilterPreview | null;
  filterPreviewError: string;
  result: ExtractionResponse | null;
  saved: boolean;
  savedCount: number;
  busy: string;
  message: string;
  error: string;
  compatibility: (method: MethodSpec) => string;
  onSearch: (query: string) => void;
  onMethod: (method: MethodSpec) => void;
  onMethodControl: (name: string, value: ControlValue) => void;
  onFilter: (filter: FilterName) => void;
  onFilterControl: (name: string, value: ControlValue) => void;
  onScore: () => void;
  onMaterialize: (save: boolean) => Promise<void>;
  onCompare: () => void;
  onSweep: () => void;
}

function AnalysisWorkspace(props: AnalysisWorkspaceProps) {
  const [targetFilter, setTargetFilter] = useState<"all" | "edge" | "node">("all");
  const [approachFilter, setApproachFilter] = useState("all");
  const [supportFilter, setSupportFilter] = useState("all");
  const [compatibleOnly, setCompatibleOnly] = useState(false);
  const methodDialog = useRef<HTMLDialogElement>(null);
  const methodLibraryBody = useRef<HTMLDivElement>(null);
  const filterDialog = useRef<HTMLDialogElement>(null);
  const settingsDialog = useRef<HTMLDialogElement>(null);
  const resultDialog = useRef<HTMLDialogElement>(null);
  const previousScore = useRef(props.score);
  const {
    schema, data, context, preview, previewBusy, mappingReviewPending, onMappingReviewFinished,
    method, methods, methodSearch, methodControls,
    filterName, filterChosen, filterControls, score, filterPreview, filterPreviewError, result, saved, savedCount, busy, message, error,
    compatibility, onSearch, onMethod, onMethodControl, onFilter,
    onFilterControl, onScore, onMaterialize, onCompare, onSweep,
  } = props;
  const methodSpecs = method ? resolvedControls(schema.controls.methods[method.name] || [], data, Boolean(preview?.directed), context) : [];
  const basicMethodSpecs = methodSpecs.filter((control) => !control.advanced);
  const advancedMethodSpecs = methodSpecs.filter((control) => control.advanced);
  const filterSpecs = method && filterChosen ? adjustedFilterControls(schema.controls.filters[filterName] || [], score, method) : [];
  const basicFilterSpecs = filterSpecs.filter((control) => !control.advanced && control.name !== "drop_isolates");
  const advancedFilterSpecs = filterSpecs.filter((control) => control.advanced || control.name === "drop_isolates");
  const searchTerms = methodSearch.toLowerCase().trim().split(/\s+/).filter(Boolean);
  const activeMethodFilterCount = [targetFilter !== "all", approachFilter !== "all", supportFilter !== "all", compatibleOnly].filter(Boolean).length;
  const hasMethodFilters = activeMethodFilterCount > 0;
  const compatibleMethods = methods
    .filter((candidate) => {
      const searchable = `${candidate.label} ${candidate.description} ${contextualMeaning(candidate, context)}`.toLowerCase();
      return searchTerms.every((term) => searchable.includes(term));
    })
    .filter((candidate) => targetFilter === "all" || candidate.target === targetFilter)
    .filter((candidate) => approachFilter === "all" || candidate.approaches.includes(approachFilter))
    .filter((candidate) => supportFilter === "all"
      || (supportFilter === "directed" && candidate.supports_directed)
      || (supportFilter === "undirected_only" && !candidate.supports_directed)
      || (supportFilter === "weighted" && candidate.supports_weighted)
      || (supportFilter === "unweighted" && !candidate.requires_weights))
    .filter((candidate) => !compatibleOnly || !compatibility(candidate))
    .sort((left, right) => Number(Boolean(compatibility(left))) - Number(Boolean(compatibility(right))) || left.label.localeCompare(right.label));
  const selectedBlocked = method ? compatibility(method) : "";
  const boundary = filterBoundary(score, filterName, filterControls);
  const weightMeaningMissing = (data.mode === "temporal" || Boolean(data.weight)) && !context.weightSemantics;
  const networkReady = Boolean(preview?.can_run) && !previewBusy && !weightMeaningMissing;
  const waitingForData = previewBusy || !preview;
  useEffect(() => {
    const dialog = settingsDialog.current;
    if (mappingReviewPending && dialog && !dialog.open) dialog.showModal();
  }, [mappingReviewPending, data.filename, data.text]);
  const graph = filterPreview?.graph ?? result?.graph;
  const previewHeading = useRef<HTMLHeadingElement>(null);
  const [previewHeadingVisible, setPreviewHeadingVisible] = useState(true);
  useEffect(() => {
    const heading = previewHeading.current;
    if (!heading) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry) setPreviewHeadingVisible(entry.intersectionRatio >= 1);
    }, { threshold: 1 });
    observer.observe(heading);
    return () => observer.disconnect();
  }, []);
  const draftReady = Boolean(filterPreview || result);

  useEffect(() => {
    methodLibraryBody.current?.scrollTo({ top: 0 });
  }, [methodSearch]);

  function resetMethodFilters() {
    setTargetFilter("all");
    setApproachFilter("all");
    setSupportFilter("all");
    setCompatibleOnly(false);
  }

  function clearMethodSearch() {
    onSearch("");
    resetMethodFilters();
  }

  function pickMethod(candidate: MethodSpec) {
    if (candidate.name !== method?.name) onMethod(candidate);
    methodDialog.current?.close();
  }

  const methodChoiceButton = (
    <button className="button button--configure" onClick={() => methodDialog.current?.showModal()}>
      <Search size={16} /> {method ? "Change method" : "Choose method"}
    </button>
  );
  const filterChoiceButton = (
    <button className="button button--configure" onClick={() => openFilterPicker(filterDialog.current)}>
      <Settings2 size={16} /> {filterChosen ? "Change filter" : "Choose filter"}
    </button>
  );

  const advancedMethodSettings = advancedMethodSpecs.length > 0 && (
    <div className="control-stack method-controls">
      {advancedMethodSpecs.map((control) => (
        <ControlField key={control.name} control={control} value={methodControls[control.name]} onChange={onMethodControl} compactChoices />
      ))}
    </div>
  );
  const scoringSettings = <>
    {selectedBlocked && <div className="compatibility-warning"><CircleAlert size={17} /><span>{selectedBlocked}. Browse methods to choose one for this network.</span></div>}
    {basicMethodSpecs.length > 0 && <div className="control-stack method-controls">
      {basicMethodSpecs.map((control) => (
        <ControlField key={control.name} control={control} value={methodControls[control.name]} onChange={onMethodControl} compactChoices />
      ))}
    </div>}
    {advancedMethodSettings && (score ? advancedMethodSettings : (
      <details className="advanced-options advanced-method-settings">
        <summary>Advanced method settings</summary>
        {advancedMethodSettings}
      </details>
    ))}
    {score && <button className="button button--primary" disabled={!networkReady || Boolean(selectedBlocked)} onClick={onScore}><Play size={16} /> Recompute scores</button>}
  </>;

  useEffect(() => {
    const dialog = filterDialog.current;
    if (!busy && score && score !== previousScore.current && !filterChosen && dialog && !dialog.open) {
      openFilterPicker(dialog);
    }
    if (!busy) previousScore.current = score;
  }, [busy, score, filterChosen]);

  return (
    <main className="workspace analysis-workbench" aria-labelledby="analysis-title">
      <header className="network-receipt">
        <div className="network-receipt-summary">
          <h1 id="analysis-title">{context.dataset.trim() || data.filename || "Network analysis"}</h1>
          {waitingForData || !preview?.valid ? (
            <p role="status">{waitingForData ? "Checking network…" : "Check the data format and column mapping to continue."}</p>
          ) : (
            <dl className="network-facts" aria-label="Network summary">
              <div><dt>Nodes</dt><dd>{formatValue(preview.node_count)}</dd></div>
              <div><dt>{preview.directed ? "Arcs" : "Edges"}</dt><dd>{formatValue(preview.edge_count)}</dd></div>
              <div><dt>{preview.directed ? "Weakly connected components" : "Components"}</dt><dd>{formatValue(preview.component_count)}</dd></div>
              <div><dt>Direction</dt><dd>{preview.directed ? "Directed" : "Undirected"}</dd></div>
              <div><dt>Weights</dt><dd>{data.mode === "temporal" ? "Temporal weights" : data.weight || "Unweighted"}</dd></div>
            </dl>
          )}
        </div>
        {!demoMode && <button className="button button--quiet" disabled={busy !== ""} onClick={() => settingsDialog.current?.showModal()}><Settings2 size={17} aria-hidden="true" /> Network settings</button>}
      </header>
      {demoMode && <p className="demo-note">Two 25% backbones are ready to compare. Edge Weight favors strong ties, while Edge Betweenness favors links on shortest paths. Choose 50% to try a larger edge budget.</p>}
      <dialog className="workbench-dialog network-settings-dialog" ref={settingsDialog} aria-labelledby="network-settings-title" key={data.filename} onCancel={onMappingReviewFinished}>
        <header>
          <div>
            <h2 id="network-settings-title">{mappingReviewPending ? "Review network settings" : "Network settings"}</h2>
            <p className="network-settings-file">{data.filename || "Imported data"}{typeof preview?.row_count === "number" ? ` · ${formatValue(preview.row_count)} rows` : ""}</p>
          </div>
          <button className="button button--quiet" onClick={props.onImport}>Replace file</button>
        </header>
        <div className="network-settings-body"><NetworkSettings {...props} busy={previewBusy} /></div>
        <footer className="network-settings-footer">
          <span role="status">{waitingForData ? "Checking mapping…" : !preview?.can_run ? "Review the mapping issues above." : weightMeaningMissing ? "Choose what higher weights mean to continue." : ""}</span>
          <button className="button button--success" disabled={weightMeaningMissing || (mappingReviewPending && !networkReady)} onClick={() => {
            settingsDialog.current?.close();
            onMappingReviewFinished();
            if (networkReady && !method) methodDialog.current?.showModal();
          }}>
            <Check size={16} /> {mappingReviewPending ? data.mode === "graphml" ? "Use this network" : "Use this mapping" : "Done"}
          </button>
        </footer>
      </dialog>
      {!networkReady && !waitingForData && <Warnings warnings={preview?.errors || []} />}
      {weightMeaningMissing && <Warnings warnings={["Choose Strength or Distance in Network settings before scoring."]} />}
      <Warnings warnings={preview?.warnings || []} />
      <dialog className="method-dialog" ref={methodDialog} aria-labelledby="method-dialog-title">
        <header className="method-library-header">
          <div className="pane-heading"><h2 id="method-dialog-title">Choose a scoring method</h2><button className="button button--quiet" onClick={() => methodDialog.current?.close()}>Close</button></div>
          <label className="search-field"><Search size={17} aria-hidden="true" /><input type="search" aria-label="Search methods" value={methodSearch} placeholder="Search methods" onChange={(event) => onSearch(event.target.value)} /></label>
        </header>
        <div className="method-library-body" ref={methodLibraryBody} role="region" aria-label="Scoring methods" tabIndex={0}>
          {!networkReady && <p role="status">{waitingForData ? "Checking network compatibility…" : "Review Network settings before choosing a method."}</p>}
          <details className="advanced-options method-facets">
            <summary><strong><SlidersHorizontal size={16} aria-hidden="true" /> Filters</strong>{hasMethodFilters && <span className="method-filter-count">{activeMethodFilterCount} active</span>}</summary>
            <div className="method-filter-panel" role="group" aria-label="Method filters">
              <div className="method-filters">
                <label><span>Scores</span><select value={targetFilter} onChange={(event) => setTargetFilter(event.target.value as typeof targetFilter)}><option value="all">All targets</option><option value="edge">Edges</option><option value="node">Nodes</option></select></label>
                <label><span>Approach</span><select value={approachFilter} onChange={(event) => setApproachFilter(event.target.value)}><option value="all">All approaches</option>{schema.method_filters.approaches.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
                <label><span>Network support</span><select value={supportFilter} onChange={(event) => setSupportFilter(event.target.value)}><option value="all">All networks</option><option value="directed">Directed compatible</option><option value="undirected_only">Undirected only</option><option value="weighted">Uses weights</option><option value="unweighted">Works unweighted</option></select></label>
              </div>
              <div className="method-filter-actions">
                <label className="compatible-toggle"><input type="checkbox" checked={compatibleOnly} onChange={(event) => setCompatibleOnly(event.target.checked)} /><span>Compatible only</span></label>
                <button type="button" className="button button--quiet" disabled={!hasMethodFilters} onClick={resetMethodFilters}>Reset filters</button>
              </div>
            </div>
          </details>
          <div className="method-library-results">
            <h3 id="method-results-title">{searchTerms.length || hasMethodFilters ? "Matching methods" : "All methods"}</h3>
            <span className="method-list-caption" role="status">{compatibleMethods.length} {compatibleMethods.length === 1 ? "method" : "methods"}</span>
          </div>
          <div className="method-list" role="group" aria-labelledby="method-results-title">
            {compatibleMethods.map((candidate) => {
              const blocked = compatibility(candidate);
              return (
                <button key={candidate.name} className={`${candidate.name === method?.name ? "is-active" : ""}${blocked ? " is-incompatible" : ""}`} disabled={!networkReady || Boolean(blocked)} aria-pressed={candidate.name === method?.name} onClick={() => pickMethod(candidate)}>
                  <span><strong>{candidate.label}</strong><small>{conciseScoreMeaning(candidate, context)}</small></span>
                  {!blocked && (candidate.name === method?.name ? <Check size={17} aria-hidden="true" /> : <ChevronRight size={17} aria-hidden="true" />)}
                  {blocked && <em>{blocked}</em>}
                </button>
              );
            })}
            {!compatibleMethods.length && <div className="method-empty"><Search size={24} aria-hidden="true" /><strong>No methods match</strong><button className="button button--configure" onClick={clearMethodSearch}>Clear search and filters</button></div>}
          </div>
        </div>
      </dialog>
      <dialog className="workbench-dialog filter-choice-dialog" ref={filterDialog} aria-labelledby="filter-choice-title">
        <header><h2 id="filter-choice-title">Choose a filter</h2><button className="button button--quiet" onClick={() => filterDialog.current?.close()}>Close</button></header>
        {method && <div className="filter-choice-list">
          {filterOptions(method).map((name) => <button type="button" key={name} data-initial-focus={name === (filterChosen ? filterName : method.recommended_filter) ? "" : undefined} className={name === method.recommended_filter ? "is-recommended" : ""} aria-pressed={filterChosen && name === filterName} onClick={() => { onFilter(name); filterDialog.current?.close(); }}>
            <strong>{filterLabel(name)}</strong>
            {name === method.recommended_filter && <span>Recommended</span>}
            <small>{filterDescription(name, context, method)}</small>
          </button>)}
        </div>}
      </dialog>

      <div className="analysis-canvas">
        <fieldset className="analysis-controls" disabled={busy !== ""}>
        <section className="analysis-step">
          <div className="pane-heading analysis-step-header">
            <h2 className="analysis-step-title"><span aria-hidden="true">1</span> Scoring method</h2>
            {method && methodChoiceButton}
          </div>
          {!method && <p className="analysis-step-intro">Choose how Netbone scores the nodes or edges in this network.</p>}
          {method && <div className="analysis-selection-row">
            <div className="label-with-hint"><strong>{method.label}</strong><Hint label={`How ${method.label} scores the network`}>{contextualMeaning(method, context)}</Hint></div>
            {!demoMode && score && <details className="advanced-options analysis-score-settings"><summary aria-label="Scoring settings">Settings</summary><div className="scoring-settings">{scoringSettings}</div></details>}
          </div>}
          {!score && (selectedBlocked || basicMethodSpecs.length > 0 || advancedMethodSpecs.length > 0) && <div className="scoring-settings">{scoringSettings}</div>}
          {!score && <div className="step-actions">
            {method ? <button className="button button--primary" disabled={busy !== "" || !networkReady || Boolean(selectedBlocked)} onClick={onScore}>
              {busy === "score" ? <LoaderCircle className="spin" size={17} /> : <Play size={17} fill="currentColor" />}
              {busy === "score" ? "Computing scores…" : "Compute scores"}
            </button> : methodChoiceButton}
          </div>}
        </section>

        {score && method && <section className="analysis-step">
          <div className="pane-heading analysis-step-header">
            <h2 className="analysis-step-title" id="retention-title" tabIndex={-1}><span aria-hidden="true">2</span> Filter</h2>
            {!demoMode && filterChosen && filterChoiceButton}
          </div>
              {filterChosen && <div className="analysis-selection-row"><div className="label-with-hint"><strong>{filterLabel(filterName)}</strong><Hint label="How this filter works">{filterDescription(filterName, context, method)}</Hint></div></div>}
              {!filterChosen && <div className="step-actions">{filterChoiceButton}</div>}
              <Warnings warnings={score.warnings} />
              {filterChosen && <>
              {basicFilterSpecs.length > 0 && <div className="control-stack filter-controls">{basicFilterSpecs.map((control) => <ControlField key={control.name} control={control} value={filterControls[control.name]} onChange={onFilterControl} />)}</div>}
              <details className="advanced-options"><summary>Inspect score distribution</summary><div className="scoring-settings">
                {score.statistics.length < score.score_summary.score_row_count && <p>Showing {formatValue(score.statistics.length)} of {formatValue(score.score_summary.score_row_count)} scores.</p>}
                <ScoreDistribution
                  statistics={score.statistics}
                  method={method}
                  boundary={boundary}
                  direction={filterDirection(filterName, filterControls, method)}
                  operator={filterName === "significance" ? "less" : filterName === "threshold" ? String(filterControls.operator || "") : undefined}
                />
              </div></details>
              {advancedFilterSpecs.length > 0 && <details className="advanced-options"><summary>Advanced filter options <span>{advancedFilterSpecs.length}</span></summary><div className="control-stack">{advancedFilterSpecs.map((control) => <ControlField key={control.name} control={control} value={filterControls[control.name]} onChange={onFilterControl} />)}</div></details>}
              </>}
        </section>}
        </fieldset>

        <section className="analysis-preview" data-waiting-for-scores={!score} aria-labelledby="live-preview-title">
          <header>
            <div className="label-with-hint"><h2 id="live-preview-title" tabIndex={-1} ref={previewHeading}>Network preview</h2><Hint label="How to read the network preview">Thicker teal edges belong to the backbone. Gray edges were left out. The drawing is available for networks with up to 80 nodes and 1,000 edges.</Hint></div>
            {saved && <span className="analysis-status"><Check size={14} /> Saved</span>}
          </header>
          {filterPreview && <RetentionPreview preview={filterPreview} directed={Boolean(graph?.directed)} />}
          {graph ? <NetworkPreview graph={graph} /> : (
            <div className="analysis-preview-empty">
              <div aria-hidden="true"><BackboneIllustration /></div>
              <p role="status">{filterPreviewError || (score && filterChosen ? "Updating the preview…" : "The backbone preview appears after you choose a filter.")}</p>
            </div>
          )}
          <Warnings warnings={[...new Set([...(filterPreview?.warnings || []), ...(result?.warnings || [])])].filter((warning) => !score?.warnings.includes(warning))} />
          {score && <a className="analysis-return-link" href="#retention-title" onClick={jumpToHeading}>Back to filter</a>}
        </section>
      </div>
      {(method || error) && <footer className="analysis-dock" aria-label="Analysis actions">
        {error && <div className="workbench-error" role="alert"><CircleAlert size={17} /><span>{error}</span></div>}
        <div className="analysis-dock-row">
          <div className="analysis-dock-context">
            <span className="analysis-dock-status">{busy === "score" ? message : score
              ? !filterChosen ? "Choose a filter to continue" : filterPreviewError ? "Preview unavailable" : !draftReady ? "Updating preview…"
                : savedCount > 0 ? `${savedCount} saved${savedCount === 1 ? " · Save another to compare" : ""}` : graph?.truncated ? "Backbone counts ready" : "Preview ready"
              : networkReady ? selectedBlocked ? "Choose a compatible method" : "Compute scores to unlock filtering"
                : waitingForData ? "Checking network…" : "Review Network settings to continue"}</span>
            {score && !previewHeadingVisible && <a className="analysis-preview-link" href="#live-preview-title" onClick={jumpToHeading}>{graph?.truncated ? "Jump to counts" : "Jump to graph"}</a>}
          </div>
          <div className="analysis-actions">
            {score && filterChosen && <>
              <button className="button button--save" disabled={busy !== "" || saved || !draftReady} onClick={() => void onMaterialize(true)}>{busy === "filter" ? <LoaderCircle className="spin" size={17} /> : saved ? <Check size={17} /> : <Plus size={17} />} {saved ? "Backbone saved" : "Save this backbone"}</button>
              <button className="button button--inspect" disabled={busy !== "" || !draftReady} onClick={() => { resultDialog.current?.showModal(); void onMaterialize(false); }}><Download size={16} /> Inspect &amp; export</button>
            </>}
            {!demoMode && networkReady && method && !selectedBlocked && (!score || filterChosen) && <button className="button button--explore" disabled={busy !== "" || Boolean(score && !draftReady)} onClick={onSweep} aria-label="Sweep: test a range of values"><BarChart3 size={16} /> Sweep</button>}
            {savedCount >= 2 && <button className="button button--compare" disabled={busy !== ""} onClick={onCompare}><GitCompareArrows size={16} /> Compare</button>}
          </div>
        </div>
      </footer>}
      <dialog className="workbench-dialog result-details-dialog" ref={resultDialog} aria-labelledby="result-title">
        <header><h2 id="result-title">Inspect &amp; export</h2><button className="button button--quiet" onClick={() => resultDialog.current?.close()}>Close</button></header>
        {result && method ? <ResultDetails key={result.result_id} result={result} method={method} /> : <p role={error ? "alert" : "status"}>{error || "Preparing the backbone…"}</p>}
      </dialog>
      <span className="visually-hidden" role="status" aria-atomic="true">{message}</span>
    </main>
  );
}

function openFilterPicker(dialog: HTMLDialogElement | null) {
  dialog?.showModal();
  dialog?.querySelector<HTMLButtonElement>("[data-initial-focus]")?.focus();
}

function ResultDetails({ result, method }: { result: ExtractionResponse; method: MethodSpec }) {
  const [format, setFormat] = useState<"graphml" | "gexf">("graphml");
  const [scope, setScope] = useState<"annotated" | "backbone">("annotated");
  const [exportError, setExportError] = useState("");
  const [preparingBundle, setPreparingBundle] = useState(false);
  const [bundleError, setBundleError] = useState("");

  async function exportExperiment() {
    setBundleError("");
    setPreparingBundle(true);
    try {
      await downloadExperiment(result.result_id);
    } catch (reason) {
      setBundleError(errorMessage(reason));
    } finally {
      setPreparingBundle(false);
    }
  }
  return (
    <div className="result-details">
      <div className="result-export-options" aria-label="Export options" role="group">
        <section className="result-export-card">
          <div className="result-export-heading">
            <Network size={20} aria-hidden="true" />
            <h3>Download graph</h3>
          </div>
          <div className="field-grid">
            <label className="field"><span>Graph</span><select value={scope} onChange={(event) => setScope(event.target.value as typeof scope)}><option value="backbone">Backbone only</option><option value="annotated">Annotated original</option></select></label>
            <label className="field"><span>Format</span><select value={format} onChange={(event) => setFormat(event.target.value as typeof format)}><option value="graphml">GraphML</option><option value="gexf">GEXF for Gephi</option></select></label>
          </div>
          <button className="button button--export export-card-download" onClick={() => {
            setExportError("");
            void downloadGraph(result.result_id, format, scope).catch((reason: unknown) => setExportError(errorMessage(reason)));
          }}><Download size={16} aria-hidden="true" /> Download {format === "graphml" ? "GraphML" : "GEXF"}</button>
          {exportError && <p className="error-text" role="alert">{exportError}</p>}
        </section>
        <section className="result-export-card">
          <div className="result-export-heading">
            <FileJson size={20} aria-hidden="true" />
            <h3>Reproduce this analysis</h3>
          </div>
          <p>Save the method, filter, and settings used for this run.</p>
          <details className="advanced-options resolved-config"><summary>View settings</summary><pre tabIndex={0}>{JSON.stringify(result.resolved_config, null, 2)}</pre></details>
          <button className="button button--export export-card-download" onClick={() => downloadJson(result.resolved_config, "netbone-pipeline.json")}><Download size={16} /> Download JSON</button>
        </section>
        <section className="result-export-card result-export-card--experiment">
          <div className="result-export-heading">
            <Archive size={20} aria-hidden="true" />
            <h3>Export full experiment</h3>
          </div>
          <ul className="result-experiment-contents">
            <li><Check size={16} aria-hidden="true" /> Backbone and annotated graph</li>
            <li><Check size={16} aria-hidden="true" /> Statistics and pipeline settings</li>
            <li><Check size={16} aria-hidden="true" /> Report and file manifest</li>
          </ul>
          <button type="button" className="button button--export export-card-download" disabled={preparingBundle} onClick={() => void exportExperiment()}>
            {preparingBundle ? <LoaderCircle className="spin" size={16} aria-hidden="true" /> : <Download size={16} aria-hidden="true" />}
            {preparingBundle ? "Preparing ZIP…" : "Download ZIP"}
          </button>
          <span className="visually-hidden" role="status">{preparingBundle ? "Preparing the experiment ZIP." : ""}</span>
          {bundleError && <p className="error-text" role="alert">{bundleError}</p>}
        </section>
      </div>
      <section className="result-statistics">
        <StatisticsTable heading="Inspect statistics" records={result.statistics} primaryStatistic={method.primary_statistic} filename={`${method.name}-statistics.csv`} />
      </section>
    </div>
  );
}

function Warnings({ warnings }: { warnings: string[] }) {
  if (!warnings.length) return null;
  return <div className="warning-list">{warnings.map((warning, index) => <div key={index}><CircleAlert size={16} />{warning}</div>)}</div>;
}

function DataSample({ records, headers, mappedColumns }: { records: JsonRecord[]; headers: string[]; mappedColumns: string[] }) {
  const [showAll, setShowAll] = useState(false);
  const available = Object.keys(records[0] || {});
  const mapped = [...new Set(mappedColumns)].filter((column) => available.includes(column));
  const allColumns = [...new Set([...mapped, ...headers, ...available])].filter((column) => available.includes(column));
  const hasExtra = mapped.length > 0 && mapped.length < allColumns.length;
  const columns = hasExtra && !showAll ? mapped : allColumns;
  const container = useRef<HTMLDivElement>(null);
  const [overflows, setOverflows] = useState(false);
  useEffect(() => {
    const element = container.current;
    if (!element) return;
    function measure() {
      setOverflows(Boolean(element && element.clientWidth > 0 && element.scrollWidth > element.clientWidth));
    }
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [records, showAll]);

  function toggleColumns() {
    if (container.current) container.current.scrollLeft = 0;
    setShowAll((current) => !current);
  }

  return (
    <div className="data-sample">
      <div className="data-sample-heading">
        <strong id="sample-rows-title">Sample rows</strong>
        {hasExtra && <button type="button" className="button button--quiet" aria-controls="source-sample-table" onClick={toggleColumns}>
          {showAll ? "Show mapped columns" : `Show all ${allColumns.length} columns`}
        </button>}
      </div>
      {overflows && <small id="sample-scroll-hint">Scroll sideways to see more columns.</small>}
      <div className="table-wrap" id="source-sample-table" ref={container} role="region" aria-labelledby="sample-rows-title" aria-describedby={overflows ? "sample-scroll-hint" : undefined} tabIndex={overflows ? 0 : undefined}>
        <table>
          <thead><tr>{columns.map((column) => <th scope="col" key={column}><span title={column}>{column}</span></th>)}</tr></thead>
          <tbody>{records.slice(0, 4).map((record, index) => <tr key={index}>{columns.map((column) => {
            const value = formatValue(record[column]);
            return <td key={column}><span title={value}>{value}</span></td>;
          })}</tr>)}</tbody>
        </table>
      </div>
    </div>
  );
}

function SelectField({ label, value, options, optional, onChange }: { label: string; value: string; options: string[]; optional?: string; onChange: (value: string) => void }) {
  return <label className="field"><span>{label}</span><select value={value} onChange={(event) => onChange(event.target.value)}>{optional && <option value="">{optional}</option>}{options.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>;
}

function NetworkReadiness({ preview }: { preview: PreviewResponse }) {
  if (preview.valid && preview.can_run) return <Warnings warnings={preview.warnings ?? []} />;
  return (
    <div className="readiness">
      <div role="status">
        <CircleAlert size={18} />
        <span><strong>Needs attention</strong>
          <small>{preview.errors?.[0] || "Choose data and map its columns."}</small>
        </span>
      </div>
      {preview.errors?.slice(1).map((error, index) => <p key={index}>{error}</p>)}
      {preview.warnings?.map((warning, index) => <p key={index}>{warning}</p>)}
    </div>
  );
}

function RetentionPreview({ preview, directed }: { preview: FilterPreview; directed: boolean }) {
  const edgeTarget = preview.target === "edge";
  const edgeFraction = preview.original_edge_count
    ? preview.backbone_edge_count / preview.original_edge_count
    : 0;
  return <div className="preview-counts" aria-label="Retention preview">
    <RetentionCount
      label="Backbone nodes"
      count={edgeTarget ? preview.node_coverage_count : preview.backbone_node_count}
      total={preview.original_node_count}
      fraction={edgeTarget ? preview.node_coverage_fraction : preview.backbone_node_fraction}
      explanation={edgeTarget ? "Counts nodes that touch at least one backbone edge." : undefined}
    />
    <RetentionCount label="Backbone edges" count={preview.backbone_edge_count} total={preview.original_edge_count} fraction={edgeFraction} />
    <div><span className="metric-label">{directed ? "Weakly connected components" : "Connected components"}</span><strong>{formatValue(preview.backbone_component_count)}</strong></div>
  </div>;
}

function RetentionCount({ label, count, total, fraction, explanation }: {
  label: string;
  count: number;
  total: number;
  fraction: number;
  explanation?: string;
}) {
  const percent = total ? formatPercent(fraction) : "—";
  return <div className="retention-count">
    <div className="label-with-hint"><span className="metric-label">{label}</span>{explanation && <Hint label={`How ${label.toLowerCase()} are counted`}>{explanation}</Hint>}</div>
    <strong>{formatValue(count)} <span className="retention-count-total">/ {formatValue(total)}</span></strong>
    <div className="retention-count-footer">
      <span className="retention-count-track" aria-hidden="true"><span style={{ width: total ? percent : "0%" }} /></span>
      <span className="retention-count-percent">{percent}</span>
    </div>
  </div>;
}

function resolvedControls(controls: ControlSpec[], data: DataDraft, directed: boolean, context: NetworkContext): ControlSpec[] {
  const weighted = data.mode === "temporal" || Boolean(data.weight);
  return controls.filter((control) => control.name !== "distance_transform" || weighted).map((control) => {
    let next = control;
    if (control.name === "weight_requirement" && data.mode === "temporal") next = { ...next, label: "Uses aggregated temporal weight" };
    if (control.name === "distance_transform") {
      const semantics = context.weightSemantics;
      next = { ...next, default: semantics === "distance" ? "identity" : semantics === "strength" ? "inverse" : null };
    }
    if (directed && control.ignored_when_directed) next = { ...next, disabled: true, disabled_reason: control.ignored_when_directed_reason };
    return next;
  });
}

function adjustedFilterControls(controls: ControlSpec[], score: ScoreResponse | null, method: MethodSpec): ControlSpec[] {
  if (method.name === "noise_corrected") {
    return controls.map((control) => control.name === "threshold_value"
      ? { ...control, control: "number", label: "Standard deviation cutoff", min: undefined, max: undefined }
      : control);
  }
  const range = score?.score_ranges[method.primary_statistic];
  if (!range) return controls;
  return controls.map((control) => control.name === "threshold_value"
    ? { ...control, min: range.min, max: range.max, step: rangeStep(range.min, range.max) }
    : control.name === "alpha"
      ? { ...control, min: 0, max: Math.min(1, Math.max(range.max, 0.05)), step: rangeStep(0, Math.min(1, Math.max(range.max, 0.05))) }
      : control);
}

function filterDefaults(schema: UiSchema, name: FilterName, method: MethodSpec, score?: ScoreResponse | null): Record<string, ControlValue> {
  const controls = adjustedFilterControls(schema.controls.filters[name] || [], score || null, method);
  const values = initialControlValues(controls);
  const registered = method.default_filter_parameters || {};
  for (const [key, value] of Object.entries(registered)) {
    if (key === "value" && name === "threshold") values.threshold_value = value;
    else if (key in values) values[key] = value;
  }
  const range = score?.score_ranges[method.primary_statistic];
  if (name === "threshold" && range && method.name !== "noise_corrected") {
    const configured = Number(values.threshold_value);
    const boundary = Number.isFinite(configured) ? configured : range.min;
    values.threshold_value = Math.min(range.max, Math.max(range.min, boundary));
  }
  if (name === "significance" && range) {
    const maximum = Math.min(1, Math.max(range.max, 0.05));
    const configured = Number(values.alpha);
    const boundary = Number.isFinite(configured) ? configured : 0.05;
    values.alpha = Math.min(maximum, Math.max(0, boundary));
  }
  return values;
}

function filterBoundary(score: ScoreResponse | null, name: FilterName, controls: Record<string, ControlValue>): number | undefined {
  if (!score) return undefined;
  let value: ControlValue | undefined;
  if (name === "threshold") value = controls.threshold_value;
  if (name === "significance" && (!controls.correction || controls.correction === "none")) value = controls.alpha;
  if (typeof value === "number") return value;
  if (typeof value === "string" && value.trim()) return Number(value);
}

function filterDirection(name: FilterName, controls: Record<string, ControlValue>, method: MethodSpec): "higher" | "lower" {
  if (name === "significance") return "lower";
  if (name === "fraction") return method.preferred_direction;
  if (name === "threshold") return String(controls.operator).startsWith("less") ? "lower" : "higher";
  return method.preferred_direction;
}

function filterLabel(name: FilterName): string {
  return { default: "Recommended selection", fraction: "Keep a fraction", significance: "Significance", threshold: "Score cutoff" }[name];
}

function filterDescription(name: FilterName, context: NetworkContext, method: MethodSpec): string {
  const items = method.target === "node" ? context.nodes : context.edges;
  if (name === "fraction") return `Rank ${items} and keep the requested share. Ties can change how many are kept.`;
  if (name === "significance") return `Keep ${items} with p-values below the significance level.`;
  if (name === "threshold" && method.name === "noise_corrected") return "Keep ties that exceed their expected strength by the chosen number of standard deviations.";
  if (name === "threshold") return `Keep ${items} whose scores pass the cutoff using the selected comparison.`;
  return "Use the method's structural selection rule.";
}

function conciseScoreMeaning(method: MethodSpec, context: NetworkContext): string {
  const meaning = contextualMeaning(method, context);
  const sentence = meaning.match(/^.*?[.!?](?:\s|$)/)?.[0]?.trim();
  return sentence || meaning;
}

function rangeStep(minimum: number, maximum: number): number {
  const width = Math.abs(maximum - minimum);
  if (width === 0) return 0.01;
  return Number((width / 200).toPrecision(4));
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "The request could not be completed.";
}

function jumpToHeading(event: MouseEvent<HTMLAnchorElement>) {
  const heading = document.getElementById(event.currentTarget.hash.slice(1));
  if (!heading) return;
  event.preventDefault();
  heading.focus({ preventScroll: true });
  heading.scrollIntoView({ block: "start" });
}
