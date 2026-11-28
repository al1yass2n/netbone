import { downloadExperiment, downloadGraph, downloadJson } from "../api";
import { describeConfiguration } from "../labels";
import type { ConfigurationDescription } from "../labels";
import type { ExtractionResponse, JsonRecord, UiSchema } from "../types";
import { formatValue } from "../utils";
import { DownloadMenu } from "./DownloadMenu";
import { downloadStatistics, StatisticsTable } from "./StatisticsTable";

/** One backbone: what it kept, its statistics, its settings, and one menu for every download. */
export function BackboneDetails({ result, schema, label }: { result: ExtractionResponse; schema: UiSchema; label?: string }) {
  const method = String(result.extraction.method ?? "backbone");
  const primaryStatistic = String(result.extraction.primary_statistic ?? "score");
  const stem = slug(label ?? "") || method.replaceAll("_", "-");
  const summary = result.summary;
  const nodes = result.extraction.target === "node";
  const kept = nodes ? summary.backbone_node_count : summary.backbone_edge_count;
  const total = nodes ? summary.original_node_count : summary.original_edge_count;
  const described = describeConfiguration(result.resolved_config, schema);
  return (
    <div className="backbone-details">
      <div className="backbone-details-bar">
        <p><strong>{described.method}</strong> · {described.filter}<br /><span>{formatValue(kept)} of {formatValue(total)} {nodes ? "nodes" : "edges"} kept</span></p>
        <DownloadMenu items={[
          { label: "Statistics (CSV)", onSelect: () => downloadStatistics(result.statistics, primaryStatistic, `netbone-${stem}-statistics.csv`) },
          { label: "Backbone (GraphML)", onSelect: () => downloadGraph(result.result_id, "graphml", "backbone") },
          { label: "Backbone (GEXF)", onSelect: () => downloadGraph(result.result_id, "gexf", "backbone") },
          { label: "Full network with scores (GraphML)", onSelect: () => downloadGraph(result.result_id, "graphml", "annotated") },
          { label: "Full network with scores (GEXF)", onSelect: () => downloadGraph(result.result_id, "gexf", "annotated") },
          { label: "Settings (JSON)", onSelect: () => downloadJson(result.resolved_config, label ? `netbone-${stem}-pipeline.json` : "netbone-pipeline.json") },
          { label: "Full experiment (ZIP)", onSelect: () => downloadExperiment(result.result_id) },
        ]} />
      </div>
      <StatisticsTable heading="Method statistics" records={result.statistics} primaryStatistic={primaryStatistic} />
      <details className="advanced-options result-run-settings">
        <summary>Run settings</summary>
        <RunSettings config={result.resolved_config} schema={schema} />
      </details>
    </div>
  );
}

/** A pipeline's method, filter and settings in plain words. */
export function RunSettings({ config, schema }: { config: JsonRecord | undefined; schema: UiSchema }) {
  return <SettingsList described={describeConfiguration(config, schema)} />;
}

export function SettingsList({ described }: { described: ConfigurationDescription }) {
  return (
    <dl className="run-settings">
      <div className="run-settings-group"><dt>Method</dt><dd>{described.method}</dd></div>
      {described.methodSettings.map((row) => <div key={`method-${row.label}`}><dt>{row.label}</dt><dd>{row.value}</dd></div>)}
      <div className="run-settings-group"><dt>Filter</dt><dd>{described.filter}</dd></div>
      {described.filterSettings.map((row) => <div key={`filter-${row.label}`}><dt>{row.label}</dt><dd>{row.value}</dd></div>)}
      {described.extra.map((section) => [
        <div className="run-settings-group" key={section.title}><dt>{section.title}</dt><dd /></div>,
        ...section.rows.map((row) => <div key={`${section.title}-${row.label}`}><dt>{row.label}</dt><dd>{row.value}</dd></div>),
      ])}
    </dl>
  );
}

function slug(value: string): string {
  return value.normalize("NFKD").replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-|-$/g, "").toLowerCase();
}
