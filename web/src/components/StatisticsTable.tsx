import { Download } from "lucide-react";
import { downloadCsv } from "../api";
import type { JsonRecord } from "../types";
import { formatValue, labelize } from "../utils";

interface StatisticsTableProps {
  records: JsonRecord[];
  filename: string;
  primaryStatistic?: string;
  heading?: string;
}

export function StatisticsTable({ records, filename, primaryStatistic = "score", heading }: StatisticsTableProps) {
  const available = new Set(records.flatMap((record) => Object.keys(record)));
  const first = [...new Set(["source", "target", "node", "weight", primaryStatistic, "retained"])];
  const last = ["edge_id", "source_id", "target_id", "node_id"];
  const columns = [...first, ...[...available].filter((column) => !first.includes(column) && !last.includes(column)), ...last]
    .filter((column) => available.has(column));
  return (
    <div className="statistics-view">
      <header>
        {heading && <h3>{heading}</h3>}
        <button className="button button--export" onClick={() => downloadCsv(records, filename, columns)}><Download size={16} /> Download CSV</button>
      </header>
      <div className="table-wrap statistics-scroll" role="region" aria-label="Scrollable statistics" tabIndex={0}>
        <table aria-label="Method statistics">
          <thead><tr>{columns.map((column) => <th scope="col" key={column}>{labelize(column)}</th>)}</tr></thead>
          <tbody>{records.map((record, index) => <tr className={record.retained ? "is-retained" : ""} key={index}>{columns.map((column) => <td key={column}>{formatValue(record[column])}</td>)}</tr>)}</tbody>
        </table>
      </div>
    </div>
  );
}
