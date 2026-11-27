import { RotateCcw, ZoomIn, ZoomOut } from "lucide-react";
import { forwardRef, useEffect, useRef, useState } from "react";
import type { AlignmentRecord, MetricRecord } from "../types";
import { formatValue } from "../utils";

interface ScoreAlignmentFigureProps {
  alignment: AlignmentRecord;
  spearman?: MetricRecord;
  overlap?: MetricRecord;
}

export const ScoreAlignmentFigure = forwardRef<SVGSVGElement, ScoreAlignmentFigureProps>(
  function ScoreAlignmentFigure({ alignment, spearman, overlap }, ref) {
    const width = 920;
    const height = 620;
    const margin = { top: 108, right: 54, bottom: 92, left: 94 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const maximum = Math.max(
      1,
      ...alignment.points.flatMap((point) => [point.importance_rank_a, point.importance_rank_b]),
    );
    const [view, setView] = useState({ xMin: 1, xMax: maximum, yMin: 1, yMax: maximum });
    const drag = useRef<{ x: number; y: number; view: typeof view } | null>(null);
    useEffect(() => setView({ xMin: 1, xMax: maximum, yMin: 1, yMax: maximum }), [alignment, maximum]);
    const xTicks = ticks(view.xMin, view.xMax);
    const yTicks = ticks(view.yMin, view.yMax);
    const titleId = "score-alignment-title";
    const descriptionId = "score-alignment-description";
    const title = `${alignment.result_a} and ${alignment.result_b}`;
    const description = "Each mark is one aligned item. Points near the diagonal have similar importance ranks in both methods.";
    const scaleX = (rank: number) => margin.left + ((rank - view.xMin) / Math.max(1, view.xMax - view.xMin)) * plotWidth;
    const scaleY = (rank: number) => margin.top + plotHeight - ((rank - view.yMin) / Math.max(1, view.yMax - view.yMin)) * plotHeight;

    function zoom(factor: number, centerX = (view.xMin + view.xMax) / 2, centerY = (view.yMin + view.yMax) / 2) {
      if (maximum <= 1) return;
      const [xMin, xMax] = zoomAxis(view.xMin, view.xMax, centerX, factor, maximum);
      const [yMin, yMax] = zoomAxis(view.yMin, view.yMax, centerY, factor, maximum);
      setView({
        xMin,
        xMax,
        yMin,
        yMax,
      });
    }

    function reset() {
      setView({ xMin: 1, xMax: maximum, yMin: 1, yMax: maximum });
    }

    return (
      <div className="score-alignment-figure">
        <div className="plot-controls" aria-label="Score alignment navigation">
          <button className="icon-button" title="Zoom in" disabled={maximum <= 1} onClick={() => zoom(0.75)}><ZoomIn size={16} /></button>
          <button className="icon-button" title="Zoom out" disabled={maximum <= 1} onClick={() => zoom(1.35)}><ZoomOut size={16} /></button>
          <button className="icon-button" title="Reset view" disabled={maximum <= 1} onClick={reset}><RotateCcw size={16} /></button>
        </div>
        <svg
          ref={ref}
          className="comparison-figure comparison-figure--interactive"
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-labelledby={`${titleId} ${descriptionId}`}
          onWheel={(event) => {
            event.preventDefault();
            const bounds = event.currentTarget.getBoundingClientRect();
            const x = ((event.clientX - bounds.left) / bounds.width) * width;
            const y = ((event.clientY - bounds.top) / bounds.height) * height;
            if (x < margin.left || x > margin.left + plotWidth || y < margin.top || y > margin.top + plotHeight) return;
            const centerX = view.xMin + ((x - margin.left) / plotWidth) * (view.xMax - view.xMin);
            const centerY = view.yMax - ((y - margin.top) / plotHeight) * (view.yMax - view.yMin);
            zoom(event.deltaY < 0 ? 0.8 : 1.25, centerX, centerY);
          }}
          onPointerDown={(event) => {
            drag.current = { x: event.clientX, y: event.clientY, view };
            event.currentTarget.setPointerCapture(event.pointerId);
          }}
          onPointerMove={(event) => {
            if (!drag.current || maximum <= 1) return;
            const bounds = event.currentTarget.getBoundingClientRect();
            const dx = ((event.clientX - drag.current.x) / bounds.width) * width;
            const dy = ((event.clientY - drag.current.y) / bounds.height) * height;
            const start = drag.current.view;
            const [xMin, xMax] = panAxis(start.xMin, start.xMax, -(dx / plotWidth) * (start.xMax - start.xMin), maximum);
            const [yMin, yMax] = panAxis(start.yMin, start.yMax, (dy / plotHeight) * (start.yMax - start.yMin), maximum);
            setView({
              xMin,
              xMax,
              yMin,
              yMax,
            });
          }}
          onPointerUp={(event) => { drag.current = null; event.currentTarget.releasePointerCapture(event.pointerId); }}
        >
        <title id={titleId}>{title}</title>
        <desc id={descriptionId}>{description}</desc>
        <rect width={width} height={height} fill="#ffffff" />
        <text x={24} y={34} fill="#16302b" fontSize={22} fontWeight={750}>Importance-rank alignment</text>
        <text x={24} y={59} fill="#586863" fontSize={13}>{title}</text>
        <text x={24} y={82} fill="#41534e" fontSize={12}>
          {alignment.points.length} aligned {alignment.target === "node" ? "nodes" : "edges"}
          {spearman?.status === "ok" && Number.isFinite(spearman.value) ? ` · Spearman ${formatValue(spearman.value)}` : ""}
          {overlap?.status === "ok" && Number.isFinite(overlap.value) ? ` · Backbone Jaccard ${formatValue(overlap.value)}` : ""}
        </text>
        {xTicks.map((tick) => {
          const x = scaleX(tick);
          return (
            <g key={`x-${tick}`}>
              <line x1={x} y1={margin.top} x2={x} y2={margin.top + plotHeight} stroke="#e6edea" />
              <text x={x} y={margin.top + plotHeight + 24} fill="#586863" fontSize={11} textAnchor="middle">{formatValue(tick)}</text>
            </g>
          );
        })}
        {yTicks.map((tick) => {
          const y = scaleY(tick);
          return (
            <g key={`y-${tick}`}>
              <line x1={margin.left} y1={y} x2={margin.left + plotWidth} y2={y} stroke="#e6edea" />
              <text x={margin.left - 14} y={y + 4} fill="#586863" fontSize={11} textAnchor="end">{formatValue(tick)}</text>
            </g>
          );
        })}
        <defs><clipPath id="alignment-plot-clip"><rect x={margin.left} y={margin.top} width={plotWidth} height={plotHeight} /></clipPath></defs>
        <g clipPath="url(#alignment-plot-clip)">
          <line x1={scaleX(Math.max(view.xMin, view.yMin))} y1={scaleY(Math.max(view.xMin, view.yMin))} x2={scaleX(Math.min(view.xMax, view.yMax))} y2={scaleY(Math.min(view.xMax, view.yMax))} stroke="#c3cfcb" strokeDasharray="6 6" />
          {alignment.points.map((point, index) => (
            <circle key={index} cx={scaleX(point.importance_rank_a)} cy={scaleY(point.importance_rank_b)} r={5.5} fill="#136b56" fillOpacity={0.66} stroke="#ffffff" strokeWidth={1}>
              <title>{pointLabel(point)}; {alignment.result_a}: value {formatValue(point.value_a)}, rank {formatValue(point.importance_rank_a)}; {alignment.result_b}: value {formatValue(point.value_b)}, rank {formatValue(point.importance_rank_b)}</title>
            </circle>
          ))}
        </g>
        <text x={margin.left + plotWidth / 2} y={height - 28} fill="#41534e" fontSize={13} fontWeight={650} textAnchor="middle">{alignment.result_a} importance rank</text>
        <text transform={`translate(27 ${margin.top + plotHeight / 2}) rotate(-90)`} fill="#41534e" fontSize={13} fontWeight={650} textAnchor="middle">{alignment.result_b} importance rank</text>
        <text x={margin.left + plotWidth} y={height - 8} fill="#586863" fontSize={11} textAnchor="end">Higher rank means greater importance</text>
        </svg>
      </div>
    );
  },
);

function ticks(minimum: number, maximum: number): number[] {
  if (minimum === maximum) return [minimum];
  return Array.from({ length: 6 }, (_, index) => minimum + ((maximum - minimum) * index) / 5);
}

function zoomAxis(minimum: number, maximum: number, center: number, factor: number, limit: number): [number, number] {
  const minimumRange = Math.max(1, (limit - 1) / 100);
  const range = Math.min(limit - 1, Math.max(minimumRange, (maximum - minimum) * factor));
  const ratio = (center - minimum) / Math.max(minimumRange, maximum - minimum);
  let nextMinimum = center - range * ratio;
  nextMinimum = Math.max(1, Math.min(limit - range, nextMinimum));
  return [nextMinimum, nextMinimum + range];
}

function panAxis(minimum: number, maximum: number, delta: number, limit: number): [number, number] {
  const range = maximum - minimum;
  const nextMinimum = Math.max(1, Math.min(limit - range, minimum + delta));
  return [nextMinimum, nextMinimum + range];
}

function pointLabel(point: AlignmentRecord["points"][number]): string {
  if (point.node !== undefined) return `Node ${String(point.node)}`;
  return `Edge ${String(point.source)} to ${String(point.target)}`;
}
