import { BarChart3, Check, Download, GitCompareArrows, GripVertical, Pencil, Settings2, Table2, Trash2, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { demoMode } from "../demo-api";
import type { PointerEvent } from "react";
import { api, downloadCsv, downloadJson } from "../api";
import { downloadPngFigure, downloadSvgFigure } from "../figureExport";
import { moveSavedBackbone, shortBackboneLabel, uniqueResultLabel } from "../savedBackbones";
import type { ComparisonResponse, ExtractionResponse, JsonValue, MetricRecord, SavedResult } from "../types";
import { formatPercent, formatValue, labelize } from "../utils";
import { ComparisonFigure } from "./ComparisonFigure";
import { ExperimentExport } from "./ExperimentExport";
import { Hint } from "./Hint";
import { ScoreAlignmentFigure } from "./ScoreAlignmentFigure";
import { StatisticsTable } from "./StatisticsTable";
import "./AnalysisWorkspaces.css";

interface ComparisonWorkspaceProps {
  saved: SavedResult[];
  onChange: (saved: SavedResult[]) => void;
  onExtract: () => void;
}

function ExtractionSettings({ result }: { result: ExtractionResponse }) {
  const extraction = result.extraction;
  const config = result.resolved_config;
  return <div className="saved-extraction-settings">
    <ExtractionParameters title="Scoring method" name={extraction.method} parameters={extraction.method_parameters} />
    <ExtractionParameters title="Filter" name={extraction.filter} parameters={extraction.filter_parameters} />
    {config.temporal_aggregation && <ExtractionParameters title="Temporal aggregation" parameters={config.temporal_aggregation} />}
    {config.direction_conversion && <ExtractionParameters title="Direction conversion" parameters={config.direction_conversion} />}
  </div>;
}

function ExtractionParameters({ title, name, parameters }: { title: string; name?: JsonValue; parameters?: JsonValue }) {
  const entries = parameters && typeof parameters === "object" && !Array.isArray(parameters) ? Object.entries(parameters) : [];
  return <section>
    <h3>{title}</h3>
    {typeof name === "string" && <strong>{name === "default" ? "Recommended selection" : labelize(name)}</strong>}
    {entries.length ? <dl>
      {entries.map(([key, value]) => <div key={key}>
        <dt>{labelize(key)}</dt>
        <dd>{typeof value === "string" ? value : JSON.stringify(value)}</dd>
      </div>)}
    </dl> : <p>No parameters recorded.</p>}
  </section>;
}

const metricDetails: Record<string, { label: string; description: string }> = {
  connected_component_count: {
    label: "Connected components",
    description: "Disconnected groups remaining in each backbone.",
  },
  edge_count: { label: "Retained edges", description: "Edges present in each backbone." },
  edge_retention: { label: "Edge retention", description: "Share of original edges preserved." },
  isolated_node_count: { label: "Isolated nodes", description: "Output nodes without a retained connection." },
  node_count: { label: "Output nodes", description: "Nodes present in each backbone output." },
  node_retention: { label: "Node retention", description: "Share of original nodes preserved." },
  strongly_connected_component_count: { label: "Strong components", description: "Mutually reachable groups in a directed backbone." },
  weakly_connected_component_count: { label: "Weak components", description: "Connected groups after ignoring direction." },
  weight_retention: { label: "Weight retention", description: "Share of total original edge weight preserved." },
  edge_jaccard: { label: "Shared-edge similarity", description: "Shared edges divided by all distinct retained edges." },
  edge_overlap: { label: "Shared edges", description: "Retained edges in common." },
  edge_overlap_coefficient: { label: "Edge overlap coefficient", description: "Shared edges relative to the smaller backbone." },
  node_jaccard: { label: "Shared-node similarity", description: "Shared nodes divided by all distinct output nodes." },
  node_overlap: { label: "Shared nodes", description: "Output nodes in common." },
  node_overlap_coefficient: { label: "Node overlap coefficient", description: "Shared nodes relative to the smaller backbone." },
  score_spearman: { label: "Importance-rank agreement", description: "Agreement between importance rankings, from -1 to 1." },
};

export function ComparisonWorkspace({ saved, onChange, onExtract }: ComparisonWorkspaceProps) {
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [scope, setScope] = useState<"single" | "pairwise" | "alignment">("single");
  const [view, setView] = useState<"chart" | "table">("chart");
  const [metric, setMetric] = useState<string>("edge_retention");
  const [alignmentPair, setAlignmentPair] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [inspectId, setInspectId] = useState<string | null>(null);
  const [inspectionView, setInspectionView] = useState<"settings" | "statistics">("settings");
  const [dropPosition, setDropPosition] = useState<{ source: number; destination: number } | null>(null);
  const [orderStatus, setOrderStatus] = useState("");
  const [renameId, setRenameId] = useState<string | null>(null);
  const [renameLabel, setRenameLabel] = useState("");
  const [figureError, setFigureError] = useState("");
  const figureRef = useRef<SVGSVGElement>(null);
  const comparisonSection = useRef<HTMLElement>(null);
  const savedList = useRef<HTMLDivElement>(null);
  const drag = useRef<{ pointerId: number; source: number; startY: number; y: number; active: boolean } | null>(null);
  const dragFrame = useRef(0);
  const selected = saved.filter((item) => item.selected);
  const canReorder = !demoMode && saved.length > 1;
  const inspected = saved.find((item) => item.resultId === inspectId) || null;
  const renaming = saved.find((item) => item.resultId === renameId);
  const suggestedLabel = renaming ? uniqueResultLabel(shortBackboneLabel(renaming.result), saved, renaming.resultId) : "";
  const records = scope === "single" ? comparison?.single_metrics || [] : scope === "pairwise" ? comparison?.pairwise_metrics || [] : [];
  const metrics = useMemo(() => [...new Set(records.map((record) => record.metric))], [records]);
  const activeMetric = metrics.includes(metric)
    ? metric
    : metrics.includes(scope === "single" ? "edge_retention" : "edge_jaccard")
      ? (scope === "single" ? "edge_retention" : "edge_jaccard")
      : metrics[0] || "";
  const activeRecords = records.filter((record) => record.metric === activeMetric);
  const metricTitle = scope === "alignment" ? "Importance-rank alignment" : detail(activeMetric).label;
  const metricDescription = scope === "alignment"
    ? "See whether two methods assign similar importance to the same nodes or edges."
    : detail(activeMetric).description;
  const alignments = comparison?.alignments || [];
  const activeAlignment = alignments.find((alignment) => pairKey(alignment.result_a, alignment.result_b) === alignmentPair) || alignments[0];
  const activePairKey = activeAlignment ? pairKey(activeAlignment.result_a, activeAlignment.result_b) : "";
  const alignmentSpearman = activeAlignment
    ? comparison?.pairwise_metrics.find((record) => record.metric === "score_spearman" && pairKey(record.result_a, record.result_b) === activePairKey)
    : undefined;
  const alignmentOverlap = activeAlignment
    ? comparison?.pairwise_metrics.find((record) => record.metric === `${activeAlignment.target}_jaccard` && pairKey(record.result_a, record.result_b) === activePairKey)
    : undefined;

  useEffect(() => {
    if (comparison) comparisonSection.current?.focus();
  }, [comparison]);

  useEffect(() => () => cancelAnimationFrame(dragFrame.current), []);

  async function runComparison() {
    if (selected.length < 2) return;
    setBusy(true);
    setMessage("");
    setOrderStatus("");
    try {
      const result = await api.compare({
        results: selected.map((item) => ({ result_id: item.resultId, label: item.label })),
      });
      setComparison(result);
      setAlignmentPair(result.alignments[0] ? pairKey(result.alignments[0].result_a, result.alignments[0].result_b) : "");
      setFigureError("");
    } catch (error) {
      setComparison(null);
      setMessage(error instanceof Error ? error.message : "Comparison failed.");
    } finally {
      setBusy(false);
    }
  }

  function toggleResult(resultId: string) {
    setComparison(null);
    setMessage("");
    onChange(saved.map((item) => item.resultId === resultId
      ? { ...item, selected: !item.selected }
      : item));
  }

  function removeResult(resultId: string) {
    setComparison(null);
    setMessage("");
    onChange(saved.filter((item) => item.resultId !== resultId));
  }

  function moveResult(item: SavedResult, destination: number) {
    const reordered = moveSavedBackbone(saved, item.resultId, destination);
    if (reordered === saved) return;
    setOrderStatus(`${item.label} moved to position ${reordered.indexOf(item) + 1}.${comparison ? " Compare again to update the results." : ""}`);
    setComparison(null);
    setMessage("");
    onChange(reordered);
  }

  function dropIndex(source: number, y: number) {
    let destination = 0;
    for (const [index, row] of Array.from(savedList.current?.children ?? []).entries()) {
      if (index === source) continue;
      const rect = row.getBoundingClientRect();
      if (y < rect.top + rect.height / 2) break;
      destination += 1;
    }
    return destination;
  }

  function updateDrag() {
    const active = drag.current;
    if (!active?.active) return;
    const edge = 48;
    const scrollTop = window.scrollY;
    if (active.y < edge) window.scrollBy(0, -10);
    else if (active.y > window.innerHeight - edge) window.scrollBy(0, 10);
    const destination = dropIndex(active.source, active.y);
    setDropPosition((previous) => previous?.destination === destination ? previous : { source: active.source, destination });
    if (window.scrollY !== scrollTop) dragFrame.current = requestAnimationFrame(updateDrag);
  }

  function startDrag(event: PointerEvent<HTMLButtonElement>, source: number) {
    if (!event.isPrimary || event.button !== 0 || drag.current || busy) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    drag.current = { pointerId: event.pointerId, source, startY: event.clientY, y: event.clientY, active: false };
  }

  function trackDrag(event: PointerEvent<HTMLButtonElement>) {
    const active = drag.current;
    if (!active || active.pointerId !== event.pointerId) return;
    active.y = event.clientY;
    if (!active.active && Math.abs(active.y - active.startY) < 5) return;
    active.active = true;
    cancelAnimationFrame(dragFrame.current);
    updateDrag();
  }

  function endDrag(pointerId: number) {
    const active = drag.current;
    if (!active || active.pointerId !== pointerId) return null;
    drag.current = null;
    cancelAnimationFrame(dragFrame.current);
    setDropPosition(null);
    return active;
  }

  function beginRename(item: SavedResult) {
    setRenameId(item.resultId);
    setRenameLabel(item.label);
  }

  function applyRename() {
    if (!renameId || !renameLabel.trim()) return;
    const nextLabel = uniqueResultLabel(renameLabel.trim(), saved, renameId);
    setComparison(null);
    setMessage("");
    onChange(saved.map((item) => item.resultId === renameId ? { ...item, label: nextLabel } : item));
    setRenameId(null);
  }

  return (
    <main className="workspace compare-workspace" aria-labelledby="compare-title">
      <header className="workspace-header">
        <div>
          <span className="eyebrow">ANALYSIS / COMPARE</span>
          <h1 id="compare-title">Compare backbones</h1>
          <p>See what each backbone keeps, where they overlap, and how their scores agree.</p>
        </div>
        {comparison?.experiment_id && <ExperimentExport key={comparison.experiment_id} experimentId={comparison.experiment_id} disabled={busy} />}
      </header>

      {!saved.length ? (
        <section className="empty-state">
          <GitCompareArrows size={34} />
          <h2>No saved backbones</h2>
          <p>Create a backbone and add it to your comparison from the result. You’ll need at least two to see how they differ.</p>
          <button className="button button--primary" onClick={onExtract}>Extract a backbone</button>
        </section>
      ) : (
        <div className="compare-layout">
          <aside className="selection-pane" aria-label="Saved backbones">
            <div className="pane-heading">
              <div>
                <h2>Saved backbones</h2>
              </div>
              <span className="compare-selection-count" role="status">{selected.length} of {saved.length} selected</span>
            </div>
            <div className="compare-selection-action">
              <button className="button button--save" disabled={selected.length < 2 || busy} onClick={runComparison}>
                <GitCompareArrows size={17} />
                {busy ? "Comparing…" : selected.length < 2 ? "Compare backbones" : `Compare ${selected.length} backbones`}
              </button>
              {selected.length < 2 && <small>Select at least two backbones.</small>}
              {message && <p className="error-text" role="alert">{message}</p>}
            </div>
            {canReorder && <span className="visually-hidden" id="saved-order-help">Drag to move, or press Up or Down.</span>}
            <span className="visually-hidden" role="status">{orderStatus}</span>
            <div className="saved-result-list" ref={savedList}>
              {saved.map((item, index) => {
                const summary = item.result.summary;
                const extraction = item.result.extraction;
                const retention = extraction.target === "node"
                  ? summary.node_fraction
                  : summary.edge_fraction;
                const dropSide = index === dropPosition?.destination
                  ? index < dropPosition.source ? "before" : index > dropPosition.source ? "after" : undefined
                  : undefined;
                return (
                  <article className={`saved-result${item.selected ? " is-selected" : ""}${canReorder ? " has-grip" : ""}${index === dropPosition?.source ? " is-dragging" : ""}`} data-drop-side={dropSide} key={item.resultId}>
                    {canReorder && <button
                      type="button"
                      className="icon-button saved-result__grip"
                      title="Drag to move · Up/Down on keyboard"
                      aria-label={`Move ${item.label}`}
                      aria-describedby="saved-order-help"
                      disabled={busy}
                      onPointerDown={(event) => startDrag(event, index)}
                      onPointerMove={trackDrag}
                      onPointerUp={(event) => {
                        const active = endDrag(event.pointerId);
                        if (active?.active) moveResult(item, dropIndex(active.source, event.clientY));
                      }}
                      onPointerCancel={(event) => endDrag(event.pointerId)}
                      onLostPointerCapture={(event) => endDrag(event.pointerId)}
                      onKeyDown={(event) => {
                        if (event.key === "Escape" && drag.current) {
                          endDrag(drag.current.pointerId);
                        } else if (!drag.current && (event.key === "ArrowUp" || event.key === "ArrowDown")) {
                          event.preventDefault();
                          const handle = event.currentTarget;
                          moveResult(item, index + (event.key === "ArrowUp" ? -1 : 1));
                          requestAnimationFrame(() => handle.focus());
                        }
                      }}
                    ><GripVertical size={16} aria-hidden="true" /></button>}
                    <button className="saved-result__select" aria-pressed={item.selected} disabled={busy} onClick={() => toggleResult(item.resultId)}>
                      <span>
                        <strong title={item.label}>{item.label}</strong>
                        <small>{labelize(String(extraction.method))} · {formatPercent(retention)} {extraction.target === "node" ? "nodes" : "edges"} kept</small>
                      </span>
                      <b aria-hidden="true">{item.selected && <Check size={15} />}</b>
                    </button>
                    <button className="icon-button" title="Inspect saved result" aria-label={`Inspect ${item.label}`} onClick={() => { setInspectionView("settings"); setInspectId(item.resultId); }}>
                      <Settings2 size={16} />
                    </button>
                    {!demoMode && <button className="icon-button" title="Rename saved result" aria-label={`Rename ${item.label}`} disabled={busy} onClick={() => beginRename(item)}>
                      <Pencil size={16} />
                    </button>}
                    <button className="icon-button icon-button--danger" title="Remove saved result" aria-label={`Remove ${item.label}`} disabled={busy} onClick={() => removeResult(item.resultId)}>
                      <Trash2 size={16} />
                    </button>
                  </article>
                );
              })}
            </div>
          </aside>

          <section className="comparison-canvas" ref={comparisonSection} tabIndex={-1} aria-label="Comparison results" aria-busy={busy}>
            {!comparison ? (
              <div className="empty-state empty-state--quiet">
                <GitCompareArrows size={36} />
                <h2>{busy ? "Comparing your backbones…" : selected.length >= 2 ? "Ready to compare" : "Choose backbones to compare"}</h2>
                <p>{selected.length >= 2 ? "Compare your selection to explore retention, overlap, and score agreement." : saved.length < 2 ? "Create and save one more backbone from the same network." : "Select two or more saved backbones to get started."}</p>
              </div>
            ) : (
              <>
                <div className="comparison-toolbar">
                  <div className="segmented" role="group" aria-label="Comparison scope">
                    <button aria-pressed={scope === "single"} onClick={() => { setScope("single"); setMetric("edge_retention"); setFigureError(""); }}>
                      Properties
                    </button>
                    <button aria-pressed={scope === "pairwise"} onClick={() => { setScope("pairwise"); setMetric("edge_jaccard"); setFigureError(""); }}>
                      Overlap & agreement
                    </button>
                    <button aria-pressed={scope === "alignment"} onClick={() => { setScope("alignment"); setFigureError(""); }}>
                      Score alignment
                    </button>
                  </div>
                  <div className="segmented compare-view-toggle" role="group" aria-label="Comparison view">
                    <button aria-pressed={view === "chart"} onClick={() => setView("chart")}><BarChart3 size={16} /> Chart</button>
                    <button aria-pressed={view === "table"} onClick={() => setView("table")}><Table2 size={16} /> Table</button>
                  </div>
                </div>
                <div className="property-view">
                    {scope === "alignment" ? (
                      <label className="field compare-metric-field">
                        <span>Backbone pair</span>
                        <select value={activePairKey} disabled={!alignments.length} onChange={(event) => { setAlignmentPair(event.target.value); setFigureError(""); }}>
                          {alignments.map((alignment) => {
                            const key = pairKey(alignment.result_a, alignment.result_b);
                            return <option value={key} key={key}>{alignment.result_a} ↔ {alignment.result_b}{alignment.status !== "ok" ? " (unavailable)" : ""}</option>;
                          })}
                        </select>
                      </label>
                    ) : (
                      <label className="field compare-metric-field">
                        <span>Metric</span>
                        <select value={activeMetric} onChange={(event) => { setMetric(event.target.value); setFigureError(""); }}>
                          {metrics.map((name) => {
                            const unavailable = records.filter((record) => record.metric === name && record.status !== "ok").length;
                            return <option value={name} key={name}>{detail(name).label}{unavailable ? ` (${unavailable} unavailable)` : ""}</option>;
                          })}
                        </select>
                      </label>
                    )}
                    <header>
                      <div className="analysis-heading-with-hint">
                        <h2>{metricTitle}</h2>
                        <Hint label={`What ${metricTitle} means`}>{metricDescription}</Hint>
                      </div>
                      <div className="figure-actions">
                        <button className="button button--export" disabled={scope === "alignment" && (!activeAlignment || activeAlignment.status !== "ok")} onClick={() => downloadCsv(scope === "alignment" ? (activeAlignment?.points.map((point) => ({ ...point })) || []) : activeRecords, scope === "alignment" ? "netbone-score-alignment.csv" : `netbone-comparison-${activeMetric}.csv`)}><Download size={15} /> CSV</button>
                        {view === "chart" && <button className="button button--export" disabled={scope === "alignment" && activeAlignment?.status !== "ok"} onClick={() => { if (figureRef.current) downloadSvgFigure(figureRef.current, scope === "alignment" ? "netbone-score-alignment" : `netbone-comparison-${activeMetric}`); }}><Download size={15} /> SVG</button>}
                        {view === "chart" && <button className="button button--export" disabled={scope === "alignment" && activeAlignment?.status !== "ok"} onClick={() => { if (figureRef.current) void downloadPngFigure(figureRef.current, scope === "alignment" ? "netbone-score-alignment" : `netbone-comparison-${activeMetric}`).catch((error: unknown) => setFigureError(error instanceof Error ? error.message : "PNG export failed.")); }}><Download size={15} /> PNG</button>}
                      </div>
                    </header>
                    {scope === "alignment" ? (
                      activeAlignment?.status === "ok" ? (
                        view === "chart"
                          ? <ScoreAlignmentFigure ref={figureRef} alignment={activeAlignment} spearman={alignmentSpearman} overlap={alignmentOverlap} />
                          : <AlignmentTable alignment={activeAlignment} />
                      ) : <div className="empty-state empty-state--quiet"><h3>Alignment unavailable</h3><p>{activeAlignment?.explanation || "No result pair is available."}</p></div>
                    ) : view === "chart"
                      ? <ComparisonFigure ref={figureRef} records={activeRecords} metric={activeMetric} scope={scope} labels={comparison.results.map((item) => item.label)} title={metricTitle} description={metricDescription} />
                      : <MetricTable records={activeRecords} scope={scope} />}
                    {figureError && <p className="error-text">{figureError}</p>}
                    {scope !== "alignment" && activeRecords.some((record) => record.status !== "ok") && <p className="comparison-note">See the table for explanations of unavailable values.</p>}
                </div>
              </>
            )}
          </section>
        </div>
      )}
      {inspected && (
        <div className="dialog-backdrop" onMouseDown={() => setInspectId(null)}>
          <section className="inspection-dialog" role="dialog" aria-modal="true" aria-labelledby="inspection-title" onMouseDown={(event) => event.stopPropagation()}>
            <header>
              <h2 id="inspection-title">{inspected.label}</h2>
              <button className="icon-button" title="Close inspection" onClick={() => setInspectId(null)}><X size={18} /></button>
            </header>
            <div className="inspection-content">
              <div className="inspection-toolbar">
                <div className="segmented" role="group" aria-label="Saved backbone details">
                  <button aria-pressed={inspectionView === "settings"} onClick={() => setInspectionView("settings")}>Extraction settings</button>
                  <button aria-pressed={inspectionView === "statistics"} onClick={() => setInspectionView("statistics")}>Statistics</button>
                </div>
                {inspectionView === "settings" && <button className="button button--export" onClick={() => {
                  const stem = inspected.label.replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-|-$/g, "");
                  downloadJson(inspected.result.resolved_config, `netbone-${stem ? `${stem}-` : ""}pipeline.json`);
                }}><Download size={16} aria-hidden="true" /> Download configuration</button>}
              </div>
              {inspectionView === "settings" ? <ExtractionSettings result={inspected.result} /> : <StatisticsTable records={inspected.result.statistics} primaryStatistic={String(inspected.result.extraction.primary_statistic ?? "score")} filename={`${inspected.label}-statistics.csv`} />}
            </div>
          </section>
        </div>
      )}
      {renameId && (
        <div className="dialog-backdrop" onMouseDown={() => setRenameId(null)}>
          <section className="rename-dialog" role="dialog" aria-modal="true" aria-labelledby="rename-title" onMouseDown={(event) => event.stopPropagation()}>
            <header><div><span className="eyebrow">COMPARISON LABEL</span><h2 id="rename-title">Rename saved backbone</h2></div><button className="icon-button" title="Close rename dialog" onClick={() => setRenameId(null)}><X size={18} /></button></header>
            <label className="field"><span>Label</span><input autoFocus maxLength={120} value={renameLabel} onChange={(event) => setRenameLabel(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") applyRename(); }} /></label>
            {suggestedLabel && <button className="button button--quiet" onClick={() => setRenameLabel(suggestedLabel)}>Use suggested label · {suggestedLabel}</button>}
            <button className="button button--save" disabled={!renameLabel.trim()} onClick={applyRename}>Save label</button>
          </section>
        </div>
      )}
    </main>
  );
}
function detail(metric: string) {
  return metricDetails[metric] || { label: labelize(metric), description: "Deterministic package comparison record." };
}

function MetricTable({ records, scope }: { records: MetricRecord[]; scope: "single" | "pairwise" }) {
  const columns = scope === "single"
    ? ["result", "value", "status", "explanation"]
    : ["result_a", "result_b", "value", "status", "explanation"];
  return (
    <div className="table-wrap">
      <table>
        <thead><tr>{columns.map((column) => <th key={column}>{labelize(column)}</th>)}</tr></thead>
        <tbody>{records.map((record, index) => (
          <tr key={index}>{columns.map((column) => <td key={column}>{formatValue(record[column])}</td>)}</tr>
        ))}</tbody>
      </table>
    </div>
  );
}

function AlignmentTable({ alignment }: { alignment: ComparisonResponse["alignments"][number] }) {
  const columns = alignment.target === "node"
    ? ["node", "value_a", "importance_rank_a", "value_b", "importance_rank_b"]
    : ["source", "target", "value_a", "importance_rank_a", "value_b", "importance_rank_b"];
  return (
    <div className="table-wrap">
      <table>
        <thead><tr>{columns.map((column) => <th key={column}>{labelize(column)}</th>)}</tr></thead>
        <tbody>{alignment.points.map((point, index) => (
          <tr key={index}>{columns.map((column) => <td key={column}>{formatValue(point[column as keyof typeof point])}</td>)}</tr>
        ))}</tbody>
      </table>
    </div>
  );
}

function pairKey(left: unknown, right: unknown): string {
  return [String(left), String(right)].sort().join("\u0000");
}
