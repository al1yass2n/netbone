import { BarChart3, GitCompareArrows, LoaderCircle, MoreHorizontal, Table2, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { demoMode } from "../demo-api";
import { api, downloadCsv, downloadWorkspaceExperiment } from "../api";
import { figureColor } from "../chart";
import { downloadPngFigure, downloadSvgFigure } from "../figureExport";
import { formatMetric, metricDescription, metricLabel, sentenceCase } from "../labels";
import { moveSavedBackbone, uniqueResultLabel } from "../savedBackbones";
import type { ComparisonResponse, MetricRecord, SavedResult, UiSchema } from "../types";
import { formatPercent, formatValue } from "../utils";
import { BackboneDetails } from "./BackboneDetails";
import { BackLink } from "./BackLink";
import { ComparisonFigure } from "./ComparisonFigure";
import { DownloadMenu } from "./DownloadMenu";
import type { DownloadItem } from "./DownloadMenu";
import { Hint } from "./Hint";
import { useMenu } from "./useMenu";
import { ScoreAlignmentFigure } from "./ScoreAlignmentFigure";
import "./AnalysisWorkspaces.css";

interface ComparisonWorkspaceProps {
  schema: UiSchema;
  saved: SavedResult[];
  onChange: (saved: SavedResult[]) => void;
  onBack: () => void;
}

export function ComparisonWorkspace({ schema, saved, onChange, onBack }: ComparisonWorkspaceProps) {
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [scope, setScope] = useState<"single" | "pairwise" | "alignment">("single");
  const [view, setView] = useState<"chart" | "table">("chart");
  const [metric, setMetric] = useState<string>("edge_retention");
  const [alignmentPair, setAlignmentPair] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [inspectId, setInspectId] = useState<string | null>(null);
  const [orderStatus, setOrderStatus] = useState("");
  const [renameId, setRenameId] = useState<string | null>(null);
  const [renameLabel, setRenameLabel] = useState("");
  const [figureError, setFigureError] = useState("");
  const figureRef = useRef<SVGSVGElement>(null);
  const selected = saved.filter((item) => item.selected);
  const inspected = saved.find((item) => item.resultId === inspectId) || null;
  // The comparison follows the ticked backbones, their names and their order.
  const selectionKey = JSON.stringify(selected.map((item) => [item.resultId, item.label]));
  const records = scope === "single" ? comparison?.single_metrics || [] : scope === "pairwise" ? comparison?.pairwise_metrics || [] : [];
  const metrics = useMemo(() => [...new Set(records.map((record) => record.metric))], [records]);
  const activeMetric = metrics.includes(metric)
    ? metric
    : metrics.includes(scope === "single" ? "edge_retention" : "edge_jaccard")
      ? (scope === "single" ? "edge_retention" : "edge_jaccard")
      : metrics[0] || "";
  const activeRecords = records.filter((record) => record.metric === activeMetric);
  const metricTitle = scope === "alignment" ? "Importance-rank alignment" : metricLabel(activeMetric);
  const metricText = scope === "alignment"
    ? "See whether two methods give the same nodes or edges similar importance."
    : metricDescription(activeMetric);
  const alignments = comparison?.alignments || [];
  const activeAlignment = alignments.find((alignment) => pairKey(alignment.result_a, alignment.result_b) === alignmentPair) || alignments[0];
  const activePairKey = activeAlignment ? pairKey(activeAlignment.result_a, activeAlignment.result_b) : "";
  const alignmentSpearman = activeAlignment
    ? comparison?.pairwise_metrics.find((record) => record.metric === "score_spearman" && pairKey(record.result_a, record.result_b) === activePairKey)
    : undefined;
  const alignmentOverlap = activeAlignment
    ? comparison?.pairwise_metrics.find((record) => record.metric === `${activeAlignment.target}_jaccard` && pairKey(record.result_a, record.result_b) === activePairKey)
    : undefined;
  const figureName = scope === "alignment" ? "netbone-score-alignment" : `netbone-comparison-${activeMetric}`;
  const alignmentReady = scope !== "alignment" || activeAlignment?.status === "ok";

  useEffect(() => {
    const entries = JSON.parse(selectionKey) as Array<[string, string]>;
    if (entries.length < 2) {
      setComparison(null);
      setBusy(false);
      return;
    }
    let cancelled = false;
    setBusy(true);
    setMessage("");
    api.compare({ results: entries.map(([resultId, label]) => ({ result_id: resultId, label })) })
      .then((response) => {
        if (cancelled) return;
        setComparison(response);
        setAlignmentPair((current) => response.alignments.some((alignment) => pairKey(alignment.result_a, alignment.result_b) === current)
          ? current
          : response.alignments[0] ? pairKey(response.alignments[0].result_a, response.alignments[0].result_b) : "");
        setFigureError("");
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setComparison(null);
        setMessage(error instanceof Error ? error.message : "Comparison failed.");
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectionKey]);

  function toggleResult(resultId: string) {
    onChange(saved.map((item) => item.resultId === resultId ? { ...item, selected: !item.selected } : item));
  }

  function removeResult(item: SavedResult) {
    setOrderStatus(`${item.label} removed.`);
    onChange(saved.filter((entry) => entry.resultId !== item.resultId));
  }

  function moveResult(item: SavedResult, destination: number) {
    const reordered = moveSavedBackbone(saved, item.resultId, destination);
    if (reordered === saved) return;
    setOrderStatus(`${item.label} moved to position ${reordered.indexOf(item) + 1}.`);
    onChange(reordered);
  }

  function applyRename() {
    if (!renameId || !renameLabel.trim()) return;
    const nextLabel = uniqueResultLabel(renameLabel.trim(), saved, renameId);
    onChange(saved.map((item) => item.resultId === renameId ? { ...item, label: nextLabel } : item));
    setRenameId(null);
  }

  const downloads: DownloadItem[] = comparison ? [
    {
      label: "Data (CSV)",
      disabled: !alignmentReady,
      onSelect: () => downloadCsv(scope === "alignment" ? (activeAlignment?.points.map((point) => ({ ...point })) || []) : activeRecords, `${figureName}.csv`),
    },
    ...(view === "chart" ? [
      { label: "Figure (SVG)", disabled: !alignmentReady, onSelect: () => { if (figureRef.current) downloadSvgFigure(figureRef.current, figureName); } },
      { label: "Figure (PNG)", disabled: !alignmentReady, onSelect: () => figureRef.current ? downloadPngFigure(figureRef.current, figureName) : undefined },
    ] : []),
    { label: "Full experiment (ZIP)", disabled: busy, onSelect: () => downloadWorkspaceExperiment(comparison.experiment_id) },
  ] : [];

  return (
    <main className="workspace compare-workspace" aria-labelledby="compare-title">
      <BackLink onClick={onBack} />
      <header className="workspace-header">
        <div>
          <h1 id="compare-title" tabIndex={-1}>Compare backbones</h1>
          <p>See what each backbone keeps, where they overlap, and how their scores agree.</p>
        </div>
        {comparison && <DownloadMenu items={downloads} />}
      </header>

      {!saved.length ? (
        <section className="empty-state">
          <GitCompareArrows size={34} aria-hidden="true" />
          <h2>No saved backbones</h2>
          <p>Save backbones in the analysis to compare them here. You need at least two from the same network.</p>
        </section>
      ) : (
        <div className="compare-layout">
          <aside className="selection-pane" aria-label="Saved backbones">
            <div className="pane-heading">
              <h2>Saved backbones</h2>
              <span className="compare-selection-count">{selected.length} of {saved.length} selected</span>
            </div>
            <span className="visually-hidden" role="status">{orderStatus}</span>
            <div className="saved-result-list">
              {saved.map((item, index) => (
                <SavedCard
                  key={item.resultId}
                  item={item}
                  schema={schema}
                  color={item.selected ? figureColor(selected.indexOf(item)) : undefined}
                  first={index === 0}
                  last={index === saved.length - 1}
                  onToggle={() => toggleResult(item.resultId)}
                  onDetails={() => setInspectId(item.resultId)}
                  onRename={demoMode ? undefined : () => { setRenameId(item.resultId); setRenameLabel(item.label); }}
                  onMove={(step) => moveResult(item, index + step)}
                  onRemove={() => removeResult(item)}
                />
              ))}
            </div>
          </aside>

          <section className="comparison-canvas" aria-label="Comparison results" aria-busy={busy}>
            {message && <p className="error-text" role="alert">{message}</p>}
            {!comparison ? (
              <div className="empty-state empty-state--quiet">
                {busy ? <LoaderCircle className="spin" size={34} aria-hidden="true" /> : <GitCompareArrows size={36} aria-hidden="true" />}
                <h2 role="status">{busy ? "Comparing your backbones…" : saved.length < 2 ? "Save one more backbone" : "Select two or more backbones"}</h2>
                {!busy && <p>{saved.length < 2 ? "Save another backbone from the same network to compare the two." : "Tick the backbones you want to compare."}</p>}
              </div>
            ) : (
              <div className="comparison-results" data-updating={busy || undefined}>
                <div className="comparison-toolbar">
                  <div className="segmented" role="group" aria-label="Comparison scope">
                    <button aria-pressed={scope === "single"} onClick={() => { setScope("single"); setMetric("edge_retention"); setFigureError(""); }}>Properties</button>
                    <button aria-pressed={scope === "pairwise"} onClick={() => { setScope("pairwise"); setMetric("edge_jaccard"); setFigureError(""); }}>Overlap &amp; agreement</button>
                    <button aria-pressed={scope === "alignment"} onClick={() => { setScope("alignment"); setFigureError(""); }}>Score alignment</button>
                  </div>
                  <div className="segmented compare-view-toggle" role="group" aria-label="Comparison view">
                    <button aria-pressed={view === "chart"} onClick={() => setView("chart")}><BarChart3 size={16} aria-hidden="true" /> Chart</button>
                    <button aria-pressed={view === "table"} onClick={() => setView("table")}><Table2 size={16} aria-hidden="true" /> Table</button>
                  </div>
                </div>
                <div className="property-view">
                  <div className="field compare-metric-field">
                    <div className="label-with-hint">
                      <label htmlFor="compare-metric">{scope === "alignment" ? "Backbone pair" : "Metric"}</label>
                      <Hint label={`What ${metricTitle} means`}>{metricText}</Hint>
                    </div>
                    {scope === "alignment" ? (
                      <select id="compare-metric" value={activePairKey} disabled={!alignments.length} onChange={(event) => { setAlignmentPair(event.target.value); setFigureError(""); }}>
                        {alignments.map((alignment) => {
                          const key = pairKey(alignment.result_a, alignment.result_b);
                          return <option value={key} key={key}>{alignment.result_a} ↔ {alignment.result_b}{alignment.status !== "ok" ? " (unavailable)" : ""}</option>;
                        })}
                      </select>
                    ) : (
                      <select id="compare-metric" value={activeMetric} onChange={(event) => { setMetric(event.target.value); setFigureError(""); }}>
                        {metrics.map((name) => {
                          const unavailable = records.filter((record) => record.metric === name && record.status !== "ok").length;
                          return <option value={name} key={name}>{metricLabel(name)}{unavailable ? ` (${unavailable} unavailable)` : ""}</option>;
                        })}
                      </select>
                    )}
                  </div>
                  {scope === "alignment" ? (
                    activeAlignment?.status === "ok" ? (
                      view === "chart"
                        ? <ScoreAlignmentFigure ref={figureRef} alignment={activeAlignment} spearman={alignmentSpearman} overlap={alignmentOverlap} />
                        : <AlignmentTable alignment={activeAlignment} />
                    ) : <div className="empty-state empty-state--quiet"><h3>Alignment unavailable</h3><p>{activeAlignment?.explanation || "No result pair is available."}</p></div>
                  ) : view === "chart"
                    ? <div className="figure-scroll"><ComparisonFigure ref={figureRef} records={activeRecords} metric={activeMetric} scope={scope} labels={comparison.results.map((item) => item.label)} title={metricTitle} description={metricText} /></div>
                    : <MetricTable records={activeRecords} scope={scope} metric={activeMetric} />}
                  {figureError && <p className="error-text">{figureError}</p>}
                  {scope !== "alignment" && view === "chart" && activeRecords.some((record) => record.status !== "ok") && <p className="comparison-note">Open the table to read why some values are unavailable.</p>}
                </div>
              </div>
            )}
          </section>
        </div>
      )}
      {inspected && (
        <div className="dialog-backdrop" onMouseDown={() => setInspectId(null)} onKeyDown={(event) => { if (event.key === "Escape") setInspectId(null); }}>
          <section className="inspection-dialog" role="dialog" aria-modal="true" aria-labelledby="inspection-title" onMouseDown={(event) => event.stopPropagation()}>
            <header>
              <h2 id="inspection-title">{inspected.label}</h2>
              <button className="icon-button dialog-close" title="Close" aria-label="Close" autoFocus onClick={() => setInspectId(null)}><X size={18} aria-hidden="true" /></button>
            </header>
            <div className="inspection-content">
              <BackboneDetails result={inspected.result} schema={schema} label={inspected.label} />
            </div>
          </section>
        </div>
      )}
      {renameId && (
        <div className="dialog-backdrop" onMouseDown={() => setRenameId(null)}>
          <form className="rename-dialog" role="dialog" aria-modal="true" aria-labelledby="rename-title" onMouseDown={(event) => event.stopPropagation()} onSubmit={(event) => { event.preventDefault(); applyRename(); }} onKeyDown={(event) => { if (event.key === "Escape") setRenameId(null); }}>
            <header><h2 id="rename-title">Rename backbone</h2><button type="button" className="icon-button dialog-close" title="Close" aria-label="Close" onClick={() => setRenameId(null)}><X size={18} aria-hidden="true" /></button></header>
            <label className="field"><span>Name</span><input autoFocus maxLength={120} value={renameLabel} onChange={(event) => setRenameLabel(event.target.value)} /></label>
            <div className="rename-actions">
              <button type="button" className="button button--quiet" onClick={() => setRenameId(null)}>Cancel</button>
              <button type="submit" className="button button--primary" disabled={!renameLabel.trim()}>Save name</button>
            </div>
          </form>
        </div>
      )}
    </main>
  );
}

function SavedCard({ item, schema, color, first, last, onToggle, onDetails, onRename, onMove, onRemove }: {
  item: SavedResult;
  schema: UiSchema;
  color?: string;
  first: boolean;
  last: boolean;
  onToggle: () => void;
  onDetails: () => void;
  onRename?: () => void;
  onMove: (step: -1 | 1) => void;
  onRemove: () => void;
}) {
  const menu = useMenu();
  const extraction = item.result.extraction;
  const summary = item.result.summary;
  const nodes = extraction.target === "node";
  const methodLabel = schema.methods.find((method) => method.name === extraction.method)?.label ?? sentenceCase(String(extraction.method ?? ""));
  const kept = `${formatPercent(nodes ? summary.node_fraction : summary.edge_fraction)} of ${nodes ? "nodes" : "edges"} kept`;
  // A renamed backbone no longer says which method made it, so the line below does.
  const detail = item.label.toLowerCase().startsWith(methodLabel.toLowerCase()) ? kept : `${methodLabel} · ${kept}`;
  const choose = (action: () => void) => () => { menu.close(); action(); };
  return (
    <article className={`saved-result${item.selected ? " is-selected" : ""}`}>
      <label className="saved-result__pick">
        <input type="checkbox" checked={item.selected} onChange={onToggle} />
        <span className="saved-result__dot" style={color ? { background: color } : undefined} aria-hidden="true" />
        <span className="saved-result__text">
          <strong title={item.label}>{item.label}</strong>
          <small>{detail}</small>
        </span>
      </label>
      <details className="saved-result__menu" {...menu.props}>
        <summary className="icon-button" aria-label={`Options for ${item.label}`} title="Options"><MoreHorizontal size={18} aria-hidden="true" /></summary>
        <div className="menu-list" role="group" aria-label={`Options for ${item.label}`}>
          <button type="button" onClick={choose(onDetails)}>Details</button>
          {onRename && <button type="button" onClick={choose(onRename)}>Rename</button>}
          <button type="button" disabled={first} onClick={choose(() => onMove(-1))}>Move up</button>
          <button type="button" disabled={last} onClick={choose(() => onMove(1))}>Move down</button>
          <button type="button" className="is-danger" onClick={choose(onRemove)}>Remove</button>
        </div>
      </details>
    </article>
  );
}

function MetricTable({ records, scope, metric }: { records: MetricRecord[]; scope: "single" | "pairwise"; metric: string }) {
  // Status and explanation columns only appear when a value is missing.
  const problems = records.some((record) => record.status !== "ok");
  const columns = [...(scope === "single" ? ["result"] : ["result_a", "result_b"]), "value", ...(problems ? ["status", "explanation"] : [])];
  const headings: Record<string, string> = {
    result: "Backbone", result_a: "Backbone A", result_b: "Backbone B", value: metricLabel(metric), status: "Status", explanation: "Explanation",
  };
  return (
    <div className="table-wrap">
      <table>
        <thead><tr>{columns.map((column) => <th key={column} className={column === "value" ? "is-numeric" : undefined}>{headings[column]}</th>)}</tr></thead>
        <tbody>{records.map((record, index) => (
          <tr key={index}>{columns.map((column) => (
            <td key={column} className={column === "value" ? "is-numeric" : undefined}>
              {column === "value" ? (record.status === "ok" ? formatMetric(metric, record.value) : "—")
                : column === "status" ? sentenceCase(record.status)
                  : column === "explanation" ? record.explanation || "—"
                    : formatValue(record[column])}
            </td>
          ))}</tr>
        ))}</tbody>
      </table>
    </div>
  );
}

function AlignmentTable({ alignment }: { alignment: ComparisonResponse["alignments"][number] }) {
  const columns = alignment.target === "node"
    ? ["node", "value_a", "importance_rank_a", "value_b", "importance_rank_b"]
    : ["source", "target", "value_a", "importance_rank_a", "value_b", "importance_rank_b"];
  const headings: Record<string, string> = {
    node: "Node",
    source: "Source",
    target: "Target",
    value_a: `${alignment.result_a} score`,
    importance_rank_a: `${alignment.result_a} rank`,
    value_b: `${alignment.result_b} score`,
    importance_rank_b: `${alignment.result_b} rank`,
  };
  return (
    <div className="table-wrap">
      <table>
        <thead><tr>{columns.map((column) => <th key={column}>{headings[column]}</th>)}</tr></thead>
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
