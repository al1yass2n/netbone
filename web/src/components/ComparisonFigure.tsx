import { forwardRef } from "react";
import type { MetricRecord } from "../types";
import { formatPercent, formatValue } from "../utils";

interface ComparisonFigureProps {
  records: MetricRecord[];
  metric: string;
  scope: "single" | "pairwise";
  labels: string[];
  title: string;
  description: string;
}

const colors = ["#0072b2", "#e69f00", "#009e73", "#cc79a7", "#56b4e9", "#d55e00"];

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
    const maximum = isRatio(metric) ? 1 : Math.max(1, ...validValues);
    const plotWidth = width - margin.left - margin.right;
    const ticks = Array.from({ length: 5 }, (_, index) => (maximum * index) / 4);
    const titleId = `comparison-${safeId(metric)}-title`;
    const descriptionId = `comparison-${safeId(metric)}-description`;

    return (
      <svg ref={ref} className="comparison-figure" viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby={`${titleId} ${descriptionId}`}>
        <title id={titleId}>{title}</title>
        <desc id={descriptionId}>{description}</desc>
        <rect width={width} height={height} fill="#ffffff" />
        <text x={24} y={34} fill="#172033" fontSize={22} fontWeight={750}>{title}</text>
        <text x={24} y={58} fill="#64748b" fontSize={13}>{truncate(description, 110)}</text>
        <line x1={margin.left} y1={margin.top - 8} x2={margin.left} y2={height - margin.bottom} stroke="#94a3b8" />
        {ticks.map((tick) => {
          const x = margin.left + (tick / maximum) * plotWidth;
          return (
            <g key={tick}>
              <line x1={x} y1={margin.top - 8} x2={x} y2={height - margin.bottom} stroke="#e2e8f0" />
              <text x={x} y={height - 28} fill="#64748b" fontSize={11} textAnchor="middle">{axisValue(metric, tick)}</text>
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
              <text x={margin.left - 12} y={y + 22} fill="#334155" fontSize={13} fontWeight={650} textAnchor="end">{truncate(String(record.result || "Result"), 31)}</text>
              {valid ? (
                <>
                  <rect x={margin.left} y={y + 6} width={barWidth} height={25} rx={3} fill={colors[index % colors.length]} />
                  <text x={margin.left + barWidth + 9} y={y + 23} fill="#172033" fontSize={12} fontWeight={700}>{displayValue(metric, value)}</text>
                </>
              ) : (
                <>
                  <rect x={margin.left} y={y + 6} width={plotWidth} height={25} rx={3} fill="#f1f5f9" />
                  <text x={margin.left + 9} y={y + 23} fill="#9a3412" fontSize={12}>{record.status}: {truncate(record.explanation || "Unavailable", 62)}</text>
                </>
              )}
            </g>
          );
        })}
        <text x={margin.left + plotWidth / 2} y={height - 8} fill="#475569" fontSize={12} fontWeight={650} textAnchor="middle">{isRatio(metric) ? "Proportion" : title}</text>
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
    const maximum = isRatio(metric) || metric === "score_spearman" ? 1 : Math.max(1, ...validValues);

    return (
      <svg ref={ref} className="comparison-figure" viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby={`${titleId} ${descriptionId}`}>
        <title id={titleId}>{title}</title>
        <desc id={descriptionId}>{description}</desc>
        <defs>
          <linearGradient id={`legend-${safeId(metric)}`} x1="0" x2="1">
            {metric === "score_spearman" ? <><stop offset="0" stopColor="#e69f00" /><stop offset="0.5" stopColor="#f8fafc" /><stop offset="1" stopColor="#0072b2" /></> : <><stop offset="0" stopColor="#eef7fb" /><stop offset="1" stopColor="#0072b2" /></>}
          </linearGradient>
        </defs>
        <rect width={width} height={height} fill="#ffffff" />
        <text x={24} y={34} fill="#172033" fontSize={22} fontWeight={750}>{title}</text>
        <text x={24} y={58} fill="#64748b" fontSize={13}>{truncate(description, 100)}</text>
        <g transform={`translate(${width - legendWidth - 28} 78)`}>
          <rect width={legendWidth} height={10} rx={2} fill={`url(#legend-${safeId(metric)})`} />
          <text y={26} fill="#64748b" fontSize={10}>{metric === "score_spearman" ? "-1 disagreement" : "0"}</text>
          <text x={legendWidth} y={26} fill="#64748b" fontSize={10} textAnchor="end">{metric === "score_spearman" ? "+1 agreement" : axisValue(metric, maximum)}</text>
        </g>
        {labels.map((label, index) => {
          const x = left + index * cell + (cell - 4) / 2;
          const lines = matrixLabelLines(label, Math.floor((cell - 8) / 8));
          return <g key={`heading-${label}`}>
            <text x={left - 10} y={top + index * cell + cell / 2 + 4} fill="#334155" fontSize={11} fontWeight={650} textAnchor="end"><title>{label}</title>{truncate(label, 24)}</text>
            <text x={x} y={top - 8 - (lines.length - 1) * 13} fill="#334155" fontSize={11} fontWeight={650} textAnchor="middle">
              <title>{label}</title>
              {lines.map((line, lineIndex) => <tspan x={x} dy={lineIndex ? 13 : 0} key={lineIndex}>{line}</tspan>)}
            </text>
          </g>;
        })}
        {labels.flatMap((row, rowIndex) => labels.map((column, columnIndex) => {
          const x = left + columnIndex * cell;
          const y = top + rowIndex * cell;
          if (row === column) {
            return <g key={`${row}-${column}`}><rect x={x} y={y} width={cell - 4} height={cell - 4} rx={4} fill="#e2e8f0" /><text x={x + (cell - 4) / 2} y={y + cell / 2} fill="#64748b" fontSize={11} textAnchor="middle">Self</text></g>;
          }
          const record = pairs.get(pairKey(row, column));
          const valid = record?.status === "ok" && Number.isFinite(record.value);
          const value = valid ? Number(record?.value) : 0;
          return (
            <g key={`${row}-${column}`}>
              <rect x={x} y={y} width={cell - 4} height={cell - 4} rx={4} fill={valid ? matrixColor(metric, value, maximum) : "#fff7ed"} />
              <text x={x + (cell - 4) / 2} y={y + cell / 2} fill={valid && colorStrength(metric, value, maximum) > 0.56 ? "#ffffff" : valid ? "#172033" : "#9a3412"} fontSize={11} fontWeight={700} textAnchor="middle">{valid ? displayValue(metric, value) : "N/A"}</text>
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

function isRatio(metric: string): boolean {
  return metric.includes("retention") || metric.includes("jaccard") || metric.includes("coefficient");
}

function displayValue(metric: string, value: number): string {
  return isRatio(metric) ? formatPercent(value) : formatValue(value);
}

function axisValue(metric: string, value: number): string {
  return isRatio(metric) ? `${Math.round(value * 100)}%` : formatValue(value);
}

function colorStrength(metric: string, value: number, maximum: number): number {
  if (metric === "score_spearman") return Math.abs(value);
  return Math.min(1, Math.max(0, value / maximum));
}

function matrixColor(metric: string, value: number, maximum: number): string {
  if (metric === "score_spearman") {
    const alpha = 0.12 + Math.abs(value) * 0.88;
    return value < 0 ? `rgb(230 159 0 / ${alpha})` : `rgb(0 114 178 / ${alpha})`;
  }
  return `rgb(0 114 178 / ${0.08 + colorStrength(metric, value, maximum) * 0.92})`;
}

function truncate(value: string, length: number): string {
  return value.length > length ? `${value.slice(0, length - 1)}…` : value;
}

function safeId(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]/g, "-");
}
