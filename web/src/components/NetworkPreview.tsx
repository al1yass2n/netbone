import { useId } from "react";
import { LockKeyhole } from "lucide-react";
import type { ExtractionResponse, JsonValue } from "../types";

interface NetworkPreviewProps {
  graph: ExtractionResponse["graph"];
}

export function NetworkPreview({ graph }: NetworkPreviewProps) {
  const markerId = useId();
  if (graph.truncated || graph.nodes.length > 80) {
    return (
      <div className="graph-preview-locked" role="status">
        <LockKeyhole size={22} aria-hidden="true" />
        <strong>Preview unavailable for large networks</strong>
        <p>The counts above cover the full network. Use Inspect &amp; export to download the graph.</p>
      </div>
    );
  }
  const nodes = graph.nodes;
  const visibleIds = new Set(nodes.map((node) => String(node.id)));
  const edges = graph.edges.filter(
    (edge) => visibleIds.has(String(edge.source)) && visibleIds.has(String(edge.target)),
  );
  const arcs = graph.directed ? new Set(edges.map((edge) => arcKey(edge.source, edge.target))) : null;
  const center = 260;
  const radius = Math.min(205, 118 + nodes.length * 2.1);
  const positions = new Map<string, { x: number; y: number }>();
  nodes.forEach((node, index) => {
    const angle = (index / Math.max(nodes.length, 1)) * Math.PI * 2 - Math.PI / 2;
    positions.set(String(node.id), {
      x: center + Math.cos(angle) * radius,
      y: center + Math.sin(angle) * radius,
    });
  });

  return (
    <div className="graph-preview">
      <svg viewBox="0 0 520 520" role="img" aria-label="Backbone graph preview">
        {graph.directed && (
          <defs>
            <marker id={`${markerId}-context`} viewBox="0 0 10 10" markerUnits="userSpaceOnUse" markerWidth="9" markerHeight="9" refX="9" refY="5" orient="auto">
              <path d="M0,0 L0,10 L10,5 z" className="graph-arrow" />
            </marker>
            <marker id={`${markerId}-retained`} viewBox="0 0 10 10" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto">
              <path d="M0,0 L0,10 L10,5 z" className="graph-arrow is-retained" />
            </marker>
          </defs>
        )}
        {edges.map((edge, index) => {
          const source = positions.get(String(edge.source));
          const target = positions.get(String(edge.target));
          if (!source || !target) return null;
          const key = `${arcKey(edge.source, edge.target)}-${index}`;
          const className = edge.retained ? "graph-edge is-retained" : "graph-edge";
          if (graph.directed) {
            const reciprocal = arcs?.has(arcKey(edge.target, edge.source));
            const dx = target.x - source.x;
            const dy = target.y - source.y;
            const length = Math.hypot(dx, dy) || 1;
            const bend = reciprocal ? Math.min(42, length * 0.24) : 0;
            const control = { x: (source.x + target.x) / 2 - (dy / length) * bend, y: (source.y + target.y) / 2 + (dx / length) * bend };
            const endDistance = Math.hypot(control.x - target.x, control.y - target.y) || 1;
            const end = { x: target.x + ((control.x - target.x) / endDistance) * 12, y: target.y + ((control.y - target.y) / endDistance) * 12 };
            return <path key={key} className={className} d={`M ${source.x} ${source.y} Q ${control.x} ${control.y} ${end.x} ${end.y}`} fill="none" markerEnd={`url(#${markerId}-${edge.retained ? "retained" : "context"})`} />;
          }
          return (
            <line
              key={key}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              className={className}
            />
          );
        })}
        {nodes.map((node) => {
          const position = positions.get(String(node.id));
          if (!position) return null;
          return (
            <g key={String(node.id)} transform={`translate(${position.x} ${position.y})`}>
              <circle r="9" className={node.isolated ? "graph-node is-isolated" : node.retained ? "graph-node is-retained" : "graph-node"} style={node.isolated || node.component == null ? undefined : { fill: `hsl(${(node.component * 137.508) % 360} 65% 36%)` }}>
                <title>{shortLabel(node.id)}{node.isolated ? " · Isolated in backbone" : node.component != null ? ` · Component ${node.component}` : ""}</title>
              </circle>
              {nodes.length <= 24 && <text x="13" y="4">{shortLabel(node.id)}</text>}
            </g>
          );
        })}
      </svg>
      <div className="graph-legend" role="group" aria-label="Graph legend">
        <span><i className="legend-line is-retained" aria-hidden="true" /> Backbone edges</span>
        <span><i className="legend-line" aria-hidden="true" /> Excluded edges</span>
        {nodes.some((node) => node.component != null && !node.isolated) && (
          <span title={graph.directed ? "Node colors identify weakly connected components" : "Node colors identify connected components"}>
            <i className="legend-components" aria-hidden="true" /> Component colors
          </span>
        )}
        {nodes.some((node) => node.isolated) && <span><i className="legend-isolate" aria-hidden="true" /> Isolated nodes</span>}
      </div>
    </div>
  );
}

function arcKey(source: JsonValue, target: JsonValue): string {
  return JSON.stringify([source, target]);
}

function shortLabel(value: JsonValue): string {
  const text = String(value);
  return text.length > 16 ? `${text.slice(0, 13)}...` : text;
}
