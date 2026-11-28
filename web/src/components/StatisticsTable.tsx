import { useId, useState } from "react";
import { Check, ChevronLeft, ChevronRight } from "lucide-react";
import { downloadCsv } from "../api";
import type { JsonRecord } from "../types";
import { formatValue } from "../utils";

interface StatisticsTableProps {
  records: JsonRecord[];
  primaryStatistic?: string;
  heading?: string;
}

const PAGE_SIZE = 25;
const ID_COLUMNS = ["edge_id", "source_id", "target_id", "node_id"];

export function columnLabel(column: string): string {
  if (column === "retained") return "Status";
  const text = column.replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Columns in reading order: endpoints, weight, the main score, the kept flag, then the rest, ids last. */
export function statisticsColumns(records: JsonRecord[], primaryStatistic = "score"): string[] {
  const available = new Set(records.flatMap((record) => Object.keys(record)));
  const first = [...new Set(["source", "target", "node", "weight", primaryStatistic, "retained"])];
  return [...first, ...[...available].filter((column) => !first.includes(column) && !ID_COLUMNS.includes(column)), ...ID_COLUMNS]
    .filter((column) => available.has(column));
}

export function downloadStatistics(records: JsonRecord[], primaryStatistic: string, filename: string): void {
  downloadCsv(records, filename, statisticsColumns(records, primaryStatistic));
}

export function StatisticsTable({ records, primaryStatistic = "score", heading }: StatisticsTableProps) {
  const switchLabel = useId();
  const [showIds, setShowIds] = useState(false);
  const [page, setPage] = useState(0);
  const available = new Set(records.flatMap((record) => Object.keys(record)));
  const allColumns = statisticsColumns(records, primaryStatistic);
  const hasIds = allColumns.some((column) => ID_COLUMNS.includes(column));
  const columns = showIds ? allColumns : allColumns.filter((column) => !ID_COLUMNS.includes(column));
  const numeric = new Set(columns.filter((column) => column !== "retained" && records.every((record) => {
    const value = record[column];
    return value === null || value === undefined || typeof value === "number";
  })));
  const pages = Math.max(1, Math.ceil(records.length / PAGE_SIZE));
  const current = Math.min(page, pages - 1);
  const start = current * PAGE_SIZE;
  const rows = records.slice(start, start + PAGE_SIZE);
  const kept = records.filter((record) => record.retained === true).length;
  const hasRetained = available.has("retained");
  return (
    <div className="statistics-view">
      <header>
        <div>
          {heading && <h3>{heading}</h3>}
          <p className="statistics-count">{formatValue(records.length)} rows{hasRetained ? `, ${formatValue(kept)} kept` : ""}</p>
        </div>
        <div className="statistics-tools">
          {hasIds && <span className="switch-field">
            <button type="button" className="switch" role="switch" aria-checked={showIds} aria-labelledby={switchLabel} onClick={() => setShowIds(!showIds)}><span /></button>
            <span id={switchLabel}>Show id columns</span>
          </span>}
        </div>
      </header>
      <div className="table-wrap statistics-scroll" role="region" aria-label="Scrollable statistics" tabIndex={0}>
        <table aria-label="Method statistics">
          <thead><tr>{columns.map((column) => <th scope="col" key={column} className={numeric.has(column) ? "is-numeric" : undefined}>{columnLabel(column)}</th>)}</tr></thead>
          <tbody>{rows.map((record, index) => <tr className={record.retained ? "is-retained" : ""} key={start + index}>{columns.map((column) => (
            <td key={column} className={numeric.has(column) ? "is-numeric" : undefined}>
              {column === "retained"
                ? record.retained ? <span className="status-badge status-badge--kept"><Check size={12} strokeWidth={3} aria-hidden="true" />Kept</span> : <span className="status-badge">Dropped</span>
                : formatValue(record[column])}
            </td>
          ))}</tr>)}</tbody>
        </table>
      </div>
      {pages > 1 && <nav className="table-pager" aria-label="Table pages">
        <span>Showing {formatValue(start + 1)}–{formatValue(start + rows.length)} of {formatValue(records.length)}</span>
        <button type="button" className="icon-button" aria-label="Previous page" disabled={current === 0} onClick={() => setPage(current - 1)}><ChevronLeft size={18} aria-hidden="true" /></button>
        <button type="button" className="icon-button" aria-label="Next page" disabled={current >= pages - 1} onClick={() => setPage(current + 1)}><ChevronRight size={18} aria-hidden="true" /></button>
      </nav>}
    </div>
  );
}
