import { forwardRef } from "react";
import { figureColor, niceTicks, seriesClass } from "../chart";
import { formatMetric, isRatioMetric } from "../labels";
import type { MetricRecord } from "../types";

interface ComparisonFigureProps {
  records: MetricRecord[];
  metric: string;
  scope: "single" | "pairwise";
  labels: string[];
  title: string;
  description: string;
}

export const ComparisonFigure = forwardRef<SVGSVGElement, ComparisonFigureProps>(
  function ComparisonFigure({ records, metric, scope, labels, title, description }, ref) {
    return scope === "single"
      ? <BarFigure ref={ref} records={records} metric={metric} title={title} description={description} />
      : <MatrixFigure ref={ref} records={records} metric={metric} labels={labels} title={title} description={description} />;
  },
);

const BarFigure = forwardRef<SVGSVGElement, Omit<ComparisonFigureProps, "scope" | "labels">>(
  function BarFigure({ records, metric, title, description }, ref) {
    const width = 920;
    const margin = { top: 84, right: 110, bottom: 58, left: 245 };
    const rowHeight = 56;
    const height = Math.max(300, margin.top + margin.bottom + records.length * rowHeight);
    const validValues = records
      .filter((record) => record.status === "ok" && Number.isFinite(record.value))
      .map((record) => Number(record.value));
    // The bar chart shows shares or counts, and counts step by whole numbers.
    const ticks = isRatioMetric(metric) ? [0, 0.25, 0.5, 0.75, 1] : niceTicks(0, Math.max(1, ...validValues), 4, true);
    const maximum = ticks.at(-1) ?? 1;
    const plotWidth = width - margin.left - margin.right;
    const titleId = `comparison-${safeId(metric)}-title`;
    const descriptionId = `comparison-${safeId(metric)}-description`;

    return (
      <svg ref={ref} className="comparison-figure" viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby={`${titleId} ${descriptionId}`}>
        <title id={titleId}>{title}</title>
        <desc id={descriptionId}>{description}</desc>
        <rect className="figure-paper" width={width} height={height} fill="#ffffff" />
        <text className="figure-ink" x={24} y={34} fill="#1a1f25" fontSize={22} fontWeight={750}>{title}</text>
        <text className="figure-muted" x={24} y={58} fill="#5d6670" fontSize={13}>{truncate(description, 110)}</text>
        <line className="figure-axis" x1={margin.left} y1={margin.top - 8} x2={margin.left} y2={height - margin.bottom} stroke="#c6ccd3" />
        {ticks.map((tick) => {
          const x = margin.left + (tick / maximum) * plotWidth;
          return (
            <g key={tick}>
              <line className="figure-grid" x1={x} y1={margin.top - 8} x2={x} y2={height - margin.bottom} stroke="#eceef1" />
              <text className="figure-muted" x={x} y={height - 28} fill="#5d6670" fontSize={11} textAnchor="middle">{axisValue(metric, tick)}</text>
            </g>
          );
        })}
        {records.map((record, index) => {
          const y = margin.top + index * rowHeight;
          const valid = record.status === "ok" && Number.isFinite(record.value);
          const value = valid ? Number(record.value) : 0;
          const barWidth = Math.max(0, Math.min(plotWidth, (value / maximum) * plotWidth));
          return (
            <g key={`${String(record.result)}-${index}`}>
              <text className="figure-soft" x={margin.left - 12} y={y + 22} fill="#3f4750" fontSize={13} fontWeight={650} textAnchor="end">{truncate(String(record.result || "Result"), 31)}</text>
              {valid ? (
                <>
                  <rect className={seriesClass(index)} x={margin.left} y={y + 6} width={barWidth} height={25} rx={3} fill={figureColor(index)} />
                  <text className="figure-ink" x={margin.left + barWidth + 9} y={y + 23} fill="#1a1f25" fontSize={12} fontWeight={700}>{displayValue(metric, value)}</text>
                </>
              ) : (
                <>
                  <rect className="figure-empty" x={margin.left} y={y + 6} width={plotWidth} height={25} rx={3} fill="#f4f5f7" />
                  <text className="figure-warning" x={margin.left + 9} y={y + 23} fill="#c2410c" fontSize={12}>{record.status}: {truncate(record.explanation || "Unavailable", 62)}</text>
                </>
              )}
            </g>
          );
        })}
        <text className="figure-soft" x={margin.left + plotWidth / 2} y={height - 8} fill="#3f4750" fontSize={12} fontWeight={650} textAnchor="middle">{title}</text>
      </svg>
    );
  },
);

const MatrixFigure = forwardRef<SVGSVGElement, Omit<ComparisonFigureProps, "scope">>(
  function MatrixFigure({ records, metric, labels, title, description }, ref) {
    const cell = Math.max(64, Math.min(96, 560 / Math.max(1, labels.length)));
    const left = 190;
    const top = 142;
    const legendWidth = 180;
    const width = Math.max(720, left + labels.length * cell + 64);
    const height = Math.max(430, top + labels.length * cell + 92);
    const titleId = `comparison-${safeId(metric)}-title`;
    const descriptionId = `comparison-${safeId(metric)}-description`;
    const pairs = new Map(records.map((record) => [pairKey(record.result_a, record.result_b), record]));
    const validValues = records
      .filter((record) => record.status === "ok" && Number.isFinite(record.value))
      .map((record) => Number(record.value));
    const maximum = isRatioMetric(metric) || metric === "score_spearman" ? 1 : Math.max(1, ...validValues);

    return (
      <svg ref={ref} className="comparison-figure" viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby={`${titleId} ${descriptionId}`}>
        <title id={titleId}>{title}</title>
        <desc id={descriptionId}>{description}</desc>
        <defs>
          <linearGradient id={`legend-${safeId(metric)}`} x1="0" x2="1">
            {metric === "score_spearman" ? <><stop offset="0" stopColor="#c2410c" /><stop className="figure-stop-paper" offset="0.5" stopColor="#f8f9fa" /><stop offset="1" stopColor="#0f766e" /></> : <><stop className="figure-stop-soft" offset="0" stopColor="#e6f3f1" /><stop offset="1" stopColor="#0f766e" /></>}
          </linearGradient>
        </defs>
        <rect className="figure-paper" width={width} height={height} fill="#ffffff" />
        <text className="figure-ink" x={24} y={34} fill="#1a1f25" fontSize={22} fontWeight={750}>{title}</text>
        <text className="figure-muted" x={24} y={58} fill="#5d6670" fontSize={13}>{truncate(description, 100)}</text>
        <g transform={`translate(${width - legendWidth - 28} 78)`}>
          <rect width={legendWidth} height={10} rx={2} fill={`url(#legend-${safeId(metric)})`} />
          <text className="figure-muted" y={26} fill="#5d6670" fontSize={10}>{metric === "score_spearman" ? "-1 disagreement" : "0"}</text>
          <text className="figure-muted" x={legendWidth} y={26} fill="#5d6670" fontSize={10} textAnchor="end">{metric === "score_spearman" ? "+1 agreement" : axisValue(metric, maximum)}</text>
        </g>
        {labels.map((label, index) => {
          const x = left + index * cell + (cell - 4) / 2;
          const lines = matrixLabelLines(label, Math.floor((cell - 8) / 8));
          return <g key={`heading-${label}`}>
            <text className="figure-soft" x={left - 10} y={top + index * cell + cell / 2 + 4} fill="#3f4750" fontSize={11} fontWeight={650} textAnchor="end"><title>{label}</title>{truncate(label, 24)}</text>
            <text className="figure-soft" x={x} y={top - 8 - (lines.length - 1) * 13} fill="#3f4750" fontSize={11} fontWeight={650} textAnchor="middle">
              <title>{label}</title>
              {lines.map((line, lineIndex) => <tspan x={x} dy={lineIndex ? 13 : 0} key={lineIndex}>{line}</tspan>)}
            </text>
          </g>;
        })}
        {labels.flatMap((row, rowIndex) => labels.map((column, columnIndex) => {
          const x = left + columnIndex * cell;
          const y = top + rowIndex * cell;
          if (row === column) {
            return <g key={`${row}-${column}`}><rect className="figure-track" x={x} y={y} width={cell - 4} height={cell - 4} rx={4} fill="#eceef1" /><text className="figure-muted" x={x + (cell - 4) / 2} y={y + cell / 2} fill="#5d6670" fontSize={11} textAnchor="middle">Self</text></g>;
          }
          const record = pairs.get(pairKey(row, column));
          const valid = record?.status === "ok" && Number.isFinite(record.value);
          const value = valid ? Number(record?.value) : 0;
          return (
            <g key={`${row}-${column}`}>
              <rect className={valid ? undefined : "figure-invalid"} x={x} y={y} width={cell - 4} height={cell - 4} rx={4} fill={valid ? matrixColor(metric, value, maximum) : "#fdf0e8"} />
              <text className={valid && colorStrength(metric, value, maximum) > 0.56 ? undefined : valid ? "figure-ink" : "figure-warning"} x={x + (cell - 4) / 2} y={y + cell / 2} fill={valid && colorStrength(metric, value, maximum) > 0.56 ? "#ffffff" : valid ? "#1a1f25" : "#c2410c"} fontSize={11} fontWeight={700} textAnchor="middle">{valid ? displayValue(metric, value) : "N/A"}</text>
            </g>
          );
        }))}
      </svg>
    );
  },
);

function matrixLabelLines(label: string, limit: number): string[] {
  if (label.length <= limit) return [label];
  const breakAt = label.lastIndexOf(" ", limit);
  if (breakAt > 0) return [label.slice(0, breakAt), truncate(label.slice(breakAt + 1), limit)];
  return [truncate(label, limit)];
}

function pairKey(left: unknown, right: unknown): string {
  return [String(left), String(right)].sort().join("\u0000");
}

function displayValue(metric: string, value: number): string {
  return formatMetric(metric, value);
}

function axisValue(metric: string, value: number): string {
  return isRatioMetric(metric) ? `${Math.round(value * 100)}%` : formatMetric(metric, value);
}

function colorStrength(metric: string, value: number, maximum: number): number {
  if (metric === "score_spearman") return Math.abs(value);
  return Math.min(1, Math.max(0, value / maximum));
}

function matrixColor(metric: string, value: number, maximum: number): string {
  if (metric === "score_spearman") {
    const alpha = 0.12 + Math.abs(value) * 0.88;
    return value < 0 ? `rgb(194 65 12 / ${alpha})` : `rgb(15 118 110 / ${alpha})`;
  }
  return `rgb(15 118 110 / ${0.08 + colorStrength(metric, value, maximum) * 0.92})`;
}

function truncate(value: string, length: number): string {
  return value.length > length ? `${value.slice(0, length - 1)}…` : value;
}

function safeId(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]/g, "-");
}
