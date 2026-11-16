import { BarChart3, Download, Table2 } from "lucide-react";
import { forwardRef, useRef, useState } from "react";
import { downloadCsv } from "../api";
import { downloadPngFigure, downloadSvgFigure } from "../figureExport";
import { numericSweepParameters, tradeoffRows, trajectoryRows } from "../sweepFigureData";
import type { SweepPlotRow } from "../sweepFigureData";
import type { SweepResponse } from "../types";
import { formatValue, labelize } from "../utils";

const colors = ["#0072b2", "#e69f00", "#009e73", "#cc79a7", "#56b4e9", "#d55e00"];

export function SweepVisualizations({ result }: { result: SweepResponse }) {
  const parameters = numericSweepParameters(result.runs);
  const metrics = [...new Set(result.metrics.map((row) => row.metric).filter((name): name is string => typeof name === "string"))];
  const retentionMetrics = metrics.filter((name) => name.endsWith("_retention"));
  const componentMetrics = metrics.filter((name) => name.endsWith("_component_count"));
  const setups = [...new Set(result.runs.map((run) => result.setup_names[String(run.pipeline_name)] || String(run.pipeline_name)))];
  const [mode, setMode] = useState<"trajectory" | "tradeoff">((parameters.length ? "trajectory" : "tradeoff"));
  const [view, setView] = useState<"chart" | "table">("chart");
  const [setup, setSetup] = useState("all");
  const [parameterChoice, setParameterChoice] = useState(parameters[0] || "");
  const [metricChoice, setMetricChoice] = useState(metrics.includes("edge_retention") ? "edge_retention" : metrics[0] || "");
  const [retentionChoice, setRetentionChoice] = useState(retentionMetrics.includes("edge_retention") ? "edge_retention" : retentionMetrics[0] || "");
  const [componentChoice, setComponentChoice] = useState(componentMetrics.includes("connected_component_count") ? "connected_component_count" : componentMetrics[0] || "");
  const [figureError, setFigureError] = useState("");
  const [point, setPoint] = useState<{ key: string; rows: SweepPlotRow[] } | null>(null);
  const figureRef = useRef<SVGSVGElement>(null);
  const parameter = parameters.includes(parameterChoice) ? parameterChoice : parameters[0] || "";
  const metric = metrics.includes(metricChoice) ? metricChoice : metrics[0] || "";
  const retention = retentionMetrics.includes(retentionChoice) ? retentionChoice : retentionMetrics[0] || "";
  const component = componentMetrics.includes(componentChoice) ? componentChoice : componentMetrics[0] || "";
  const ready = mode === "trajectory" ? Boolean(parameter && metric) : Boolean(retention && component);
  const rows = !ready ? [] : mode === "trajectory"
    ? trajectoryRows(result, parameter, metric, setup)
    : tradeoffRows(result, retention, component, setup);
  const validCount = rows.filter((row) => row.x !== null && row.y !== null).length;
  const unavailableCount = rows.length - validCount;
  const xLabel = mode === "trajectory" ? parameterLabel(parameter) : labelize(retention);
  const yLabel = labelize(mode === "trajectory" ? metric : component);
  const title = mode === "trajectory" ? `${yLabel} by ${xLabel}` : `${labelize(retention)} and ${yLabel}`;
  const description = mode === "trajectory"
    ? "Each line follows one setup and one combination of its other parameters."
    : "Each point is one completed extraction. Lower component counts mean fewer disconnected groups.";
  const filename = `netbone-sweep-${mode}-${mode === "trajectory" ? `${parameter}-${metric}` : `${retention}-${component}`}`;
  const chartKey = `${filename}:${setup}`;
  const pointRuns = point?.key === chartKey ? point.rows : [];

  return <section className="panel sweep-figure-panel" aria-labelledby="sweep-figure-title">
    <header className="sweep-figure-header">
      <div><span className="eyebrow">VISUALIZE</span><h2 id="sweep-figure-title">Sweep figures</h2><p>Compare measured outcomes across the generated runs.</p></div>
      <div className="segmented" role="tablist" aria-label="Sweep figure">
        <button role="tab" aria-selected={mode === "trajectory"} onClick={() => { setMode("trajectory"); setFigureError(""); }}>Trajectory</button>
        <button role="tab" aria-selected={mode === "tradeoff"} onClick={() => { setMode("tradeoff"); setFigureError(""); }}>Trade-off</button>
      </div>
    </header>
    <div className="sweep-figure-controls">
      <label className="field"><span>Setup</span><select value={setup} onChange={(event) => setSetup(event.target.value)}><option value="all">All setups</option>{setups.map((name) => <option key={name} value={name}>{name}</option>)}</select></label>
      {mode === "trajectory" ? <>
        <label className="field"><span>Varying parameter</span><select value={parameter} disabled={!parameters.length} onChange={(event) => setParameterChoice(event.target.value)}>{parameters.map((name) => <option key={name} value={name}>{parameterLabel(name)}</option>)}</select></label>
        <label className="field"><span>Measured property</span><select value={metric} disabled={!metrics.length} onChange={(event) => setMetricChoice(event.target.value)}>{metrics.map((name) => <option key={name} value={name}>{labelize(name)}</option>)}</select></label>
      </> : <>
        <label className="field"><span>Retention</span><select value={retention} disabled={!retentionMetrics.length} onChange={(event) => setRetentionChoice(event.target.value)}>{retentionMetrics.map((name) => <option key={name} value={name}>{labelize(name)}</option>)}</select></label>
        <label className="field"><span>Connectivity</span><select value={component} disabled={!componentMetrics.length} onChange={(event) => setComponentChoice(event.target.value)}>{componentMetrics.map((name) => <option key={name} value={name}>{labelize(name)}</option>)}</select></label>
      </>}
    </div>
    <div className="sweep-figure-toolbar">
      <div className="segmented segmented--icons" aria-label="Sweep figure view">
        <button aria-pressed={view === "chart"} title="Chart view" onClick={() => setView("chart")}><BarChart3 size={17} /></button>
        <button aria-pressed={view === "table"} title="Table view" onClick={() => setView("table")}><Table2 size={17} /></button>
      </div>
      <div className="figure-actions">
        <button className="button button--export" disabled={!rows.length} onClick={() => downloadCsv(rows.map((row) => ({ ...row })), `${filename}.csv`)}><Download size={15} /> CSV</button>
        {view === "chart" && <>
          <button className="button button--export" disabled={!validCount} onClick={() => { if (figureRef.current) downloadSvgFigure(figureRef.current, filename); }}><Download size={15} /> SVG</button>
          <button className="button button--export" disabled={!validCount} onClick={() => { if (figureRef.current) void downloadPngFigure(figureRef.current, filename).catch((error: unknown) => setFigureError(error instanceof Error ? error.message : "PNG export failed.")); }}><Download size={15} /> PNG</button>
        </>}
      </div>
    </div>
    {!ready ? <div className="empty-state empty-state--quiet"><h3>{mode === "trajectory" ? "No numeric parameter sweep" : "Metrics needed for this figure"}</h3><p>{mode === "trajectory" ? "Vary a numeric method or filter parameter in at least two runs." : "Measure a retention metric and a component-count metric, then run the sweep again."}</p></div>
      : view === "table" ? <SweepFigureTable rows={rows} xLabel={xLabel} yLabel={yLabel} />
        : validCount ? <>
          <div className="sweep-point-details">
            <p className="sweep-figure-note">Hover over, focus, or tap a point to see which run it represents.</p>
            <div aria-live="polite">
              {pointRuns.length > 0 && <ul>{pointRuns.map((row) => <li key={row.runId}>
                <strong>{row.runLabel}</strong> <span>· {xLabel} {axisValue(row.x ?? 0, mode === "tradeoff")}, {yLabel} {axisValue(row.y ?? 0, (mode === "trajectory" ? metric : component).endsWith("_retention"))}</span>
              </li>)}</ul>}
            </div>
          </div>
          <div className="sweep-chart-scroll"><SweepFigure ref={figureRef} rows={rows} mode={mode} title={title} description={description} xLabel={xLabel} yLabel={yLabel} xIsRatio={mode === "tradeoff"} yIsRatio={(mode === "trajectory" ? metric : component).endsWith("_retention")} onPoint={(matches) => setPoint({ key: chartKey, rows: matches })} /></div>
        </>
          : <div className="empty-state empty-state--quiet"><h3>No plottable values</h3><p>The selected records are unavailable. Open the table to inspect their explanations.</p></div>}
    {ready && <p className="sweep-figure-note">{validCount} of {rows.length} runs plotted{unavailableCount ? `; ${unavailableCount} unavailable in the chart and retained in the table below` : ""}.</p>}
    {figureError && <p className="error-text">{figureError}</p>}
  </section>;
}

const SweepFigure = forwardRef<SVGSVGElement, {
  rows: SweepPlotRow[]; mode: "trajectory" | "tradeoff"; title: string; description: string;
  xLabel: string; yLabel: string; xIsRatio: boolean; yIsRatio: boolean;
  onPoint: (rows: SweepPlotRow[]) => void;
}>(function SweepFigure({ rows, mode, title, description, xLabel, yLabel, xIsRatio, yIsRatio, onPoint }, ref) {
  const width = 960;
  const left = 96;
  const top = 100;
  const plotWidth = 814;
  const plotHeight = 350;
  const labels = [...new Set(rows.map((row) => row.series))];
  const height = 540 + Math.ceil(labels.length / 3) * 24;
  const valid = rows.filter((row): row is SweepPlotRow & { x: number; y: number } => row.x !== null && row.y !== null);
  const xValues = rows.map((row) => row.x).filter((value): value is number => value !== null);
  const rawMin = Math.min(...xValues);
  const rawMax = Math.max(...xValues);
  const padding = rawMin === rawMax ? Math.max(0.01, Math.abs(rawMin) * 0.05) : 0;
  const xMin = xIsRatio ? 0 : rawMin - padding;
  const xMax = xIsRatio ? 1 : rawMax + padding;
  const yMax = yIsRatio ? 1 : Math.max(1, ...valid.map((row) => row.y));
  const scaleX = (value: number) => left + (value - xMin) / Math.max(1e-12, xMax - xMin) * plotWidth;
  const scaleY = (value: number) => top + plotHeight - value / yMax * plotHeight;
  const ticks = Array.from({ length: 5 }, (_, index) => index / 4);
  const id = `sweep-${mode}`;
  const points = new Map<string, typeof valid>();
  for (const row of valid) {
    const key = `${row.x},${row.y}`;
    const matches = points.get(key);
    if (matches) matches.push(row);
    else points.set(key, [row]);
  }

  return <svg ref={ref} className="comparison-figure sweep-figure" viewBox={`0 0 ${width} ${height}`} role="group" aria-labelledby={`${id}-title ${id}-description`}>
    <title id={`${id}-title`}>{title}</title><desc id={`${id}-description`}>{description}</desc>
    <rect width={width} height={height} fill="#ffffff" />
    <text x={24} y={35} fill="#172033" fontSize={22} fontWeight={750}>{truncate(title, 68)}</text>
    <text x={24} y={61} fill="#64748b" fontSize={12}>{truncate(description, 120)}</text>
    {ticks.map((tick) => {
      const x = left + tick * plotWidth;
      const y = top + plotHeight - tick * plotHeight;
      return <g key={tick}>
        <line x1={x} y1={top} x2={x} y2={top + plotHeight} stroke="#e2e8f0" />
        <line x1={left} y1={y} x2={left + plotWidth} y2={y} stroke="#e2e8f0" />
        <text x={x} y={top + plotHeight + 21} fill="#64748b" fontSize={11} textAnchor="middle">{axisValue(xMin + tick * (xMax - xMin), xIsRatio)}</text>
        <text x={left - 12} y={y + 4} fill="#64748b" fontSize={11} textAnchor="end">{axisValue(tick * yMax, yIsRatio)}</text>
      </g>;
    })}
    <line x1={left} y1={top} x2={left} y2={top + plotHeight} stroke="#64748b" />
    <line x1={left} y1={top + plotHeight} x2={left + plotWidth} y2={top + plotHeight} stroke="#64748b" />
    <text x={left + plotWidth / 2} y={top + plotHeight + 48} fill="#334155" fontSize={13} fontWeight={650} textAnchor="middle">{xLabel}</text>
    <text transform={`translate(28 ${top + plotHeight / 2}) rotate(-90)`} fill="#334155" fontSize={13} fontWeight={650} textAnchor="middle">{yLabel}</text>
    <defs><clipPath id={`${id}-clip`}><rect x={left} y={top} width={plotWidth} height={plotHeight} /></clipPath></defs>
    <g clipPath={`url(#${id}-clip)`}>
      {labels.map((label, index) => {
        const series = rows.filter((row) => row.series === label).sort((a, b) => (a.x || 0) - (b.x || 0));
        const color = colors[index % colors.length];
        return <g key={label}>
          {mode === "trajectory" && lineSegments(series, scaleX, scaleY).map((path, pathIndex) => <path key={pathIndex} d={path} fill="none" stroke={color} strokeWidth={2.5} />)}
        </g>;
      })}
    </g>
    {[...points].map(([key, matches]) => {
      const row = matches.at(-1);
      if (!row) return null;
      const caption = matches.map((match) => match.runLabel).join("\n");
      return <circle className="sweep-plot-point" key={key} cx={scaleX(row.x)} cy={scaleY(row.y)} r={mode === "trajectory" ? 5 : 7}
        fill={colors[labels.indexOf(row.series) % colors.length]} fillOpacity={0.86} stroke="#ffffff" strokeWidth={1.5}
        tabIndex={0} aria-label={caption} onFocus={() => onPoint(matches)} onPointerEnter={() => onPoint(matches)} onClick={() => onPoint(matches)}>
        <title>{caption}</title>
      </circle>;
    })}
    {labels.map((label, index) => <g key={label} transform={`translate(${30 + index % 3 * 305} ${525 + Math.floor(index / 3) * 24})`}>
      <circle cx={5} cy={-4} r={5} fill={colors[index % colors.length]} />
      <text x={17} fill="#334155" fontSize={11}>{truncate(label, 39)}</text>
    </g>)}
  </svg>;
});

function SweepFigureTable({ rows, xLabel, yLabel }: { rows: SweepPlotRow[]; xLabel: string; yLabel: string }) {
  return <div className="table-wrap sweep-figure-table"><table><thead><tr><th>Run</th><th>{xLabel}</th><th>{yLabel}</th><th>Status</th><th>Explanation</th></tr></thead><tbody>{rows.map((row) => <tr key={row.runId}><td className="sweep-run-label">{row.runLabel}</td><td>{row.x === null ? "—" : formatValue(row.x)}</td><td>{row.y === null ? "—" : formatValue(row.y)}</td><td>{row.status}</td><td>{row.explanation}</td></tr>)}</tbody></table></div>;
}

function lineSegments(rows: SweepPlotRow[], scaleX: (value: number) => number, scaleY: (value: number) => number): string[] {
  const paths: string[] = [];
  let current = "";
  for (const row of rows) {
    if (row.x === null || row.y === null) {
      if (current) paths.push(current);
      current = "";
    } else {
      current += `${current ? " L" : "M"}${scaleX(row.x)} ${scaleY(row.y)}`;
    }
  }
  if (current) paths.push(current);
  return paths;
}

function parameterLabel(name: string): string { return name.split(".").map(labelize).join(" · "); }
function axisValue(value: number, ratio: boolean): string { return ratio ? `${Math.round(value * 100)}%` : formatValue(value); }
function truncate(value: string, length: number): string { return value.length > length ? `${value.slice(0, length - 1)}…` : value; }
