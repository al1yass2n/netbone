import { BarChart3, Table2 } from "lucide-react";
import { forwardRef, useMemo, useRef, useState } from "react";
import { figureColor, niceTicks } from "../chart";
import { downloadPngFigure, downloadSvgFigure } from "../figureExport";
import { formatMetric, isRatioMetric, metricLabel, sentenceCase } from "../labels";
import { numericSweepParameters, sweepRunLabels, tradeoffRows, trajectoryRows } from "../sweepFigureData";
import type { SettingLabeler, SweepPlotRow } from "../sweepFigureData";
import type { SweepResponse, UiSchema } from "../types";
import { formatPercent, formatValue } from "../utils";
import type { DownloadItem } from "./DownloadMenu";

function isIntegerSetting(schema: UiSchema, key: string): boolean {
  const [scope = "", name = ""] = key.split(".");
  const groups = scope === "method" ? Object.values(schema.controls.methods) : Object.values(schema.controls.filters);
  return groups.flat().some((control) => control.name === name && control.step === 1);
}

/** Names a varied setting from the schema, so "filter.fraction" reads "Retained fraction". */
export function schemaLabeler(schema: UiSchema): SettingLabeler {
  return (scope, name) => {
    if (scope === "filter" && name === "fraction") return "Retained fraction";
    if (scope === "filter" && name === "value") return "Cutoff";
    const groups = scope === "method" ? Object.values(schema.controls.methods) : Object.values(schema.controls.filters);
    return groups.flat().find((control) => control.name === name)?.label;
  };
}

/** The chart's choices and data. The page reads it too, to list the chart in its Download menu. */
export function useSweepFigure(result: SweepResponse, schema: UiSchema) {
  const labeler = useMemo(() => schemaLabeler(schema), [schema]);
  const runLabels = useMemo(() => sweepRunLabels(result, labeler), [result, labeler]);
  const parameters = numericSweepParameters(result.runs);
  const metrics = [...new Set(result.metrics.map((row) => row.metric).filter((name): name is string => typeof name === "string"))];
  const retentionMetrics = metrics.filter((name) => name.endsWith("_retention"));
  const componentMetrics = metrics.filter((name) => name.endsWith("_component_count"));
  const setups = [...new Set(result.runs.map((run) => result.setup_names[String(run.pipeline_name)] || String(run.pipeline_name)))];
  const [mode, setMode] = useState<"trajectory" | "tradeoff">((parameters.length ? "trajectory" : "tradeoff"));
  const [view, setView] = useState<"chart" | "table">("chart");
  const [setupChoice, setSetup] = useState("all");
  const [parameterChoice, setParameterChoice] = useState(parameters[0] || "");
  const [metricChoice, setMetricChoice] = useState(metrics.includes("edge_retention") ? "edge_retention" : metrics[0] || "");
  const [retentionChoice, setRetentionChoice] = useState(retentionMetrics.includes("edge_retention") ? "edge_retention" : retentionMetrics[0] || "");
  const [componentChoice, setComponentChoice] = useState(componentMetrics.includes("connected_component_count") ? "connected_component_count" : componentMetrics[0] || "");
  const figureRef = useRef<SVGSVGElement>(null);
  const setup = setups.length > 1 ? setupChoice : "all";
  const parameter = parameters.includes(parameterChoice) ? parameterChoice : parameters[0] || "";
  const metric = metrics.includes(metricChoice) ? metricChoice : metrics[0] || "";
  const retention = retentionMetrics.includes(retentionChoice) ? retentionChoice : retentionMetrics[0] || "";
  const component = componentMetrics.includes(componentChoice) ? componentChoice : componentMetrics[0] || "";
  const ready = mode === "trajectory" ? Boolean(parameter && metric) : Boolean(retention && component);
  const rows = !ready ? [] : mode === "trajectory"
    ? trajectoryRows(result, parameter, metric, setup, runLabels)
    : tradeoffRows(result, retention, component, setup, runLabels);
  const validCount = rows.filter((row) => row.x !== null && row.y !== null).length;
  const parameterName = (key: string) => {
    const [scope = "", name = key] = key.split(".");
    return labeler(scope, name) ?? sentenceCase(name);
  };
  const xMetric = mode === "trajectory" ? "" : retention;
  const yMetric = mode === "trajectory" ? metric : component;
  const xLabel = mode === "trajectory" ? parameterName(parameter) : metricLabel(retention);
  const yLabel = metricLabel(yMetric);
  const xIsPercent = mode === "tradeoff" ? isRatioMetric(xMetric) : parameter === "filter.fraction";
  const xValues = rows.map((row) => row.x).filter((value): value is number => value !== null);
  const xIsCount = !xIsPercent && xValues.length > 0 && xValues.every(Number.isInteger) && (mode === "tradeoff" || isIntegerSetting(schema, parameter));
  const filename = `netbone-sweep-${mode}-${mode === "trajectory" ? `${parameter}-${metric}` : `${retention}-${component}`}`;
  // The chart is offered only while it is on screen; the measurements file holds the data.
  const downloads: DownloadItem[] = view === "chart" && ready ? [
    { label: "Chart (SVG)", disabled: !validCount, onSelect: () => { if (figureRef.current) downloadSvgFigure(figureRef.current, filename); } },
    { label: "Chart (PNG)", disabled: !validCount, onSelect: () => figureRef.current ? downloadPngFigure(figureRef.current, filename) : undefined },
  ] : [];
  return {
    mode, setMode, view, setView, setups, setup, setSetup, parameters, parameter, setParameterChoice, metrics, metric, setMetricChoice,
    retentionMetrics, retention, setRetentionChoice, componentMetrics, component, setComponentChoice,
    figureRef, ready, rows, validCount, xLabel, yLabel, xIsPercent, xIsCount, yMetric, parameterName, filename, downloads, runLabels,
  };
}

export type SweepFigureState = ReturnType<typeof useSweepFigure>;

export function SweepVisualizations({ figure }: { figure: SweepFigureState }) {
  const {
    mode, setMode, view, setView, setups, setup, setSetup, parameters, parameter, setParameterChoice, metrics, metric, setMetricChoice,
    retentionMetrics, retention, setRetentionChoice, componentMetrics, component, setComponentChoice,
    figureRef, ready, rows, validCount, xLabel, yLabel, xIsPercent, xIsCount, yMetric, parameterName, filename,
  } = figure;
  const [point, setPoint] = useState<{ key: string; rows: SweepPlotRow[] } | null>(null);
  const unavailableCount = rows.length - validCount;
  const yIsPercent = isRatioMetric(yMetric);
  const title = mode === "trajectory" ? `${yLabel} by ${xLabel.charAt(0).toLowerCase()}${xLabel.slice(1)}` : `${xLabel} and ${yLabel.charAt(0).toLowerCase()}${yLabel.slice(1)}`;
  const severalLines = new Set(rows.map((row) => row.series)).size > 1;
  const description = mode === "trajectory"
    ? severalLines ? "Each line follows one setup and one combination of its other settings." : "Each dot is one run."
    : "Each dot is one run. Fewer components mean fewer disconnected groups.";
  const chartKey = `${filename}:${setup}`;
  const pointRuns = point?.key === chartKey ? point.rows : [];
  // A dropdown with a single choice says nothing, so it is left out.
  const controls = [
    setups.length > 1 && <label className="field" key="setup"><span>Setup</span><select value={setup} onChange={(event) => setSetup(event.target.value)}><option value="all">All setups</option>{setups.map((name) => <option key={name} value={name}>{name}</option>)}</select></label>,
    ...(mode === "trajectory" ? [
      parameters.length > 1 && <label className="field" key="parameter"><span>Varying setting</span><select value={parameter} onChange={(event) => setParameterChoice(event.target.value)}>{parameters.map((name) => <option key={name} value={name}>{parameterName(name)}</option>)}</select></label>,
      metrics.length > 1 && <label className="field" key="metric"><span>Measurement</span><select value={metric} onChange={(event) => setMetricChoice(event.target.value)}>{metrics.map((name) => <option key={name} value={name}>{metricLabel(name)}</option>)}</select></label>,
    ] : [
      retentionMetrics.length > 1 && <label className="field" key="retention"><span>Retention</span><select value={retention} onChange={(event) => setRetentionChoice(event.target.value)}>{retentionMetrics.map((name) => <option key={name} value={name}>{metricLabel(name)}</option>)}</select></label>,
      componentMetrics.length > 1 && <label className="field" key="component"><span>Connectivity</span><select value={component} onChange={(event) => setComponentChoice(event.target.value)}>{componentMetrics.map((name) => <option key={name} value={name}>{metricLabel(name)}</option>)}</select></label>,
    ]),
  ].filter(Boolean);

  return <section className="panel sweep-figure-panel" aria-label="Sweep chart">
    <div className="sweep-figure-toolbar">
      <div className="segmented" role="tablist" aria-label="Sweep chart">
        <button role="tab" aria-selected={mode === "trajectory"} onClick={() => setMode("trajectory")}>Trajectory</button>
        <button role="tab" aria-selected={mode === "tradeoff"} onClick={() => setMode("tradeoff")}>Trade-off</button>
      </div>
      <div className="segmented segmented--icons" role="group" aria-label="Sweep chart view">
        <button aria-pressed={view === "chart"} aria-label="Chart" title="Chart" onClick={() => setView("chart")}><BarChart3 size={17} aria-hidden="true" /></button>
        <button aria-pressed={view === "table"} aria-label="Table" title="Table" onClick={() => setView("table")}><Table2 size={17} aria-hidden="true" /></button>
      </div>
    </div>
    {controls.length > 0 && <div className="sweep-figure-controls">{controls}</div>}
    {!ready ? <div className="empty-state empty-state--quiet"><h3>{mode === "trajectory" ? "No numeric setting was varied" : "Measurements needed for this chart"}</h3><p>{mode === "trajectory" ? "Vary a numeric method or filter setting across at least two runs." : "Measure a retention and a component count, then run the sweep again."}</p></div>
      : view === "table" ? <SweepFigureTable rows={rows} xLabel={xLabel} yLabel={yLabel} xIsPercent={xIsPercent} yMetric={yMetric} />
        : validCount ? <>
          <div className="sweep-chart-scroll"><SweepFigure ref={figureRef} rows={rows} mode={mode} title={title} description={description} xLabel={xLabel} yLabel={yLabel} xIsRatio={xIsPercent} yIsRatio={yIsPercent} xIsCount={xIsCount} onPoint={(matches) => setPoint({ key: chartKey, rows: matches })} /></div>
          <div className="sweep-point-details" aria-live="polite">
            {pointRuns.length > 0
              ? <ul>{pointRuns.map((row) => <li key={row.runId}><strong>{row.runLabel}</strong> <span>· {yLabel} {axisValue(row.y ?? 0, yIsPercent)}</span></li>)}</ul>
              : <p className="sweep-figure-note">Point to a dot to see its run.{unavailableCount ? ` ${unavailableCount} of ${rows.length} runs have no value and are listed in the table.` : ""}</p>}
          </div>
        </>
          : <div className="empty-state empty-state--quiet"><h3>No values to plot</h3><p>Open the table to read why these values are unavailable.</p></div>}
  </section>;
}

const SweepFigure = forwardRef<SVGSVGElement, {
  rows: SweepPlotRow[]; mode: "trajectory" | "tradeoff"; title: string; description: string;
  xLabel: string; yLabel: string; xIsRatio: boolean; yIsRatio: boolean; xIsCount: boolean;
  onPoint: (rows: SweepPlotRow[]) => void;
}>(function SweepFigure({ rows, mode, title, description, xLabel, yLabel, xIsRatio, yIsRatio, xIsCount, onPoint }, ref) {
  const width = 960;
  const left = 96;
  const labels = [...new Set(rows.map((row) => row.series))];
  // One line needs no legend.
  const legendRows = labels.length > 1 ? Math.ceil(labels.length / 3) : 0;
  const top = 84 + legendRows * 24;
  const plotWidth = 814;
  const plotHeight = 350;
  const height = top + plotHeight + 68;
  const valid = rows.filter((row): row is SweepPlotRow & { x: number; y: number } => row.x !== null && row.y !== null);
  const xValues = rows.map((row) => row.x).filter((value): value is number => value !== null);
  const rawMin = Math.min(...xValues);
  const rawMax = Math.max(...xValues);
  const padding = rawMin === rawMax ? Math.max(0.01, Math.abs(rawMin) * 0.05) : 0;
  const xTicks = xIsRatio ? [0, 0.25, 0.5, 0.75, 1] : niceTicks(rawMin - padding, rawMax + padding, 5, xIsCount);
  // Measurements other than shares are counts here, so their axis steps by whole numbers.
  const yTicks = yIsRatio ? [0, 0.25, 0.5, 0.75, 1] : niceTicks(0, Math.max(1, ...valid.map((row) => row.y)), 5, true);
  const xMin = xTicks[0] ?? 0;
  const xMax = xTicks.at(-1) ?? 1;
  const yMax = yTicks.at(-1) ?? 1;
  const scaleX = (value: number) => left + (value - xMin) / Math.max(1e-12, xMax - xMin) * plotWidth;
  const scaleY = (value: number) => top + plotHeight - value / yMax * plotHeight;
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
    <text x={24} y={35} fill="#16302b" fontSize={22} fontWeight={750}>{truncate(title, 68)}</text>
    <text x={24} y={61} fill="#586863" fontSize={12}>{truncate(description, 120)}</text>
    {xTicks.map((tick) => <g key={`x${tick}`}>
      <line x1={scaleX(tick)} y1={top} x2={scaleX(tick)} y2={top + plotHeight} stroke="#e6edea" />
      <text x={scaleX(tick)} y={top + plotHeight + 21} fill="#586863" fontSize={11} textAnchor="middle">{axisValue(tick, xIsRatio)}</text>
    </g>)}
    {yTicks.map((tick) => <g key={`y${tick}`}>
      <line x1={left} y1={scaleY(tick)} x2={left + plotWidth} y2={scaleY(tick)} stroke="#e6edea" />
      <text x={left - 12} y={scaleY(tick) + 4} fill="#586863" fontSize={11} textAnchor="end">{axisValue(tick, yIsRatio)}</text>
    </g>)}
    <line x1={left} y1={top + plotHeight} x2={left + plotWidth} y2={top + plotHeight} stroke="#c3cfcb" />
    <text x={left + plotWidth / 2} y={top + plotHeight + 48} fill="#41534e" fontSize={13} fontWeight={650} textAnchor="middle">{xLabel}</text>
    <text transform={`translate(28 ${top + plotHeight / 2}) rotate(-90)`} fill="#41534e" fontSize={13} fontWeight={650} textAnchor="middle">{yLabel}</text>
    <defs><clipPath id={`${id}-clip`}><rect x={left} y={top} width={plotWidth} height={plotHeight} /></clipPath></defs>
    <g clipPath={`url(#${id}-clip)`}>
      {labels.map((label, index) => {
        const series = rows.filter((row) => row.series === label).sort((a, b) => (a.x || 0) - (b.x || 0));
        return <g key={label}>
          {mode === "trajectory" && lineSegments(series, scaleX, scaleY).map((path, pathIndex) => <path key={pathIndex} d={path} fill="none" stroke={figureColor(index)} strokeWidth={2.5} />)}
        </g>;
      })}
    </g>
    {[...points].map(([key, matches]) => {
      const row = matches.at(-1);
      if (!row) return null;
      const caption = matches.map((match) => match.runLabel).join("\n");
      return <circle className="sweep-plot-point" key={key} cx={scaleX(row.x)} cy={scaleY(row.y)} r={mode === "trajectory" ? 5 : 7}
        fill={figureColor(labels.indexOf(row.series))} fillOpacity={0.86} stroke="#ffffff" strokeWidth={1.5}
        tabIndex={0} aria-label={caption} onFocus={() => onPoint(matches)} onPointerEnter={() => onPoint(matches)} onClick={() => onPoint(matches)}>
        <title>{caption}</title>
      </circle>;
    })}
    {legendRows > 0 && labels.map((label, index) => <g key={label} transform={`translate(${24 + index % 3 * 305} ${92 + Math.floor(index / 3) * 24})`}>
      <circle cx={5} cy={-4} r={5} fill={figureColor(index)} />
      <text x={17} fill="#41534e" fontSize={11}>{truncate(label, 39)}</text>
    </g>)}
  </svg>;
});

function SweepFigureTable({ rows, xLabel, yLabel, xIsPercent, yMetric }: { rows: SweepPlotRow[]; xLabel: string; yLabel: string; xIsPercent: boolean; yMetric: string }) {
  const problems = rows.some((row) => row.x === null || row.y === null);
  return <div className="table-wrap sweep-figure-table"><table>
    <thead><tr><th>Run</th><th className="is-numeric">{xLabel}</th><th className="is-numeric">{yLabel}</th>{problems && <th>Explanation</th>}</tr></thead>
    <tbody>{rows.map((row) => <tr key={row.runId}>
      <td className="sweep-run-label">{row.runLabel}</td>
      <td className="is-numeric">{row.x === null ? "—" : xIsPercent ? formatPercent(row.x) : formatValue(row.x)}</td>
      <td className="is-numeric">{row.y === null ? "—" : formatMetric(yMetric, row.y)}</td>
      {problems && <td>{row.x === null || row.y === null ? row.explanation || "Unavailable" : ""}</td>}
    </tr>)}</tbody>
  </table></div>;
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

function axisValue(value: number, ratio: boolean): string { return ratio ? `${Math.round(value * 100)}%` : formatValue(value); }
function truncate(value: string, length: number): string { return value.length > length ? `${value.slice(0, length - 1)}…` : value; }
