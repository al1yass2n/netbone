import { useState } from "react";
import type { JsonRecord, MethodSpec } from "../types";
import { formatValue } from "../utils";
import "./ScoreDistribution.css";

interface ScoreDistributionProps {
  statistics: JsonRecord[];
  method: MethodSpec;
  boundary?: number;
  direction?: "higher" | "lower";
  operator?: string;
}

export function ScoreDistribution({
  statistics,
  method,
  boundary,
  direction = method.preferred_direction,
  operator,
}: ScoreDistributionProps) {
  const [requestedView, setRequestedView] = useState<"dense" | "full">("dense");
  const values = statistics
    .map((row) => row[method.primary_statistic])
    .filter((value): value is number => typeof value === "number" && Number.isFinite(value))
    .sort((left, right) => left - right);
  if (!values.length) {
    return <div className="chart-empty">Compute scores to inspect their distribution.</div>;
  }

  const fullMinimum = values[0] ?? 0;
  const fullMaximum = values.at(-1) ?? fullMinimum;
  const denseMinimum = quantile(values, 0.05);
  const denseMaximum = quantile(values, 0.95);
  const denseWidth = denseMaximum - denseMinimum;
  const denseAvailable = values.length >= 20
    && denseWidth > 0
    && fullMaximum - fullMinimum > denseWidth * 4;
  const view = denseAvailable ? requestedView : "full";
  const minimum = view === "dense" ? denseMinimum : fullMinimum;
  const maximum = view === "dense" ? denseMaximum : fullMaximum;
  const visibleValues = values.filter((value) => value >= minimum && value <= maximum);
  const hiddenCount = values.length - visibleValues.length;
  const binCount = Math.min(20, Math.max(6, Math.ceil(Math.sqrt(values.length) * 2)));
  const width = Math.max(maximum - minimum, Number.EPSILON);
  const cutoff = boundary !== undefined && Number.isFinite(boundary) ? boundary : undefined;
  const bins = Array.from({ length: binCount }, () => ({ passed: 0, excluded: 0 }));
  for (const value of visibleValues) {
    const index = Math.min(binCount - 1, Math.floor(((value - minimum) / width) * binCount));
    const bin = bins[index]!;
    if (cutoff === undefined || passesBoundary(value, cutoff, direction, operator)) bin.passed++;
    else bin.excluded++;
  }
  const tallest = Math.max(...bins.map(({ passed, excluded }) => passed + excluded), 1);
  const boundaryPosition = cutoff !== undefined && cutoff >= minimum && cutoff <= maximum
    ? maximum === minimum ? 100 : ((cutoff - minimum) / width) * 100
    : null;

  return (
    <figure className="distribution" aria-label={`${method.label} score distribution`}>
      {denseAvailable && (
        <div className="distribution__toolbar">
          <span>{hiddenCount > 0 ? `${hiddenCount} extreme ${hiddenCount === 1 ? "value" : "values"} outside this view` : "Full score range"}</span>
          <div className="segmented" aria-label="Score range view">
            <button aria-pressed={view === "dense"} onClick={() => setRequestedView("dense")}>Dense values</button>
            <button aria-pressed={view === "full"} onClick={() => setRequestedView("full")}>Full range</button>
          </div>
        </div>
      )}
      <div className="distribution__plot" aria-hidden="true">
        {bins.map(({ passed, excluded }, index) => (
          <div className="distribution__bar" key={index}>
            {passed > 0 && <span className="distribution__passed" style={{ height: `${passed / tallest * 100}%` }} />}
            {excluded > 0 && <span className="distribution__excluded" style={{ height: `${excluded / tallest * 100}%` }} />}
          </div>
        ))}
        {boundaryPosition !== null && <span className="distribution__boundary" style={{ left: `${boundaryPosition}%` }} />}
      </div>
      <figcaption>
        <div className="distribution__range">
          <span>{formatValue(minimum)}</span>
          <strong>{visibleValues.length} of {values.length} values</strong>
          <span>{formatValue(maximum)}</span>
        </div>
        {cutoff !== undefined && (
          <ul className="distribution__legend" aria-label="Score cutoff legend">
            <li><span className="distribution__passed" aria-hidden="true" />Passes cutoff</li>
            <li><span className="distribution__excluded" aria-hidden="true" />Excluded by cutoff</li>
            <li><span className="distribution__cutoff" aria-hidden="true" />Cutoff {formatValue(cutoff)}{boundaryPosition === null && " (outside this range)"}</li>
          </ul>
        )}
      </figcaption>
    </figure>
  );
}

function quantile(values: number[], fraction: number): number {
  const index = Math.round((values.length - 1) * fraction);
  return values[Math.min(values.length - 1, Math.max(0, index))] ?? 0;
}

function passesBoundary(
  value: number,
  boundary: number,
  direction: "higher" | "lower",
  operator?: string,
): boolean {
  if (operator === "greater") return value > boundary;
  if (operator === "greater_equal") return value >= boundary;
  if (operator === "less") return value < boundary;
  if (operator === "less_equal") return value <= boundary;
  if (operator === "equal") return value === boundary;
  if (operator === "not_equal") return value !== boundary;
  return direction === "lower" ? value <= boundary : value >= boundary;
}
