import { useId, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { RefObject } from "react";
import { LockKeyhole } from "lucide-react";
import { SERIES_COLORS, seriesColor } from "../chart";
import type { ExtractionResponse, JsonValue } from "../types";

interface NetworkPreviewProps {
  graph: ExtractionResponse["graph"];
}

export const COMPONENT_COLORS = SERIES_COLORS;

export function componentColor(component: number): string {
  return seriesColor(component);
}

type Point = { x: number; y: number };

export function NetworkPreview({ graph }: NetworkPreviewProps) {
  const markerId = useId();
  const svg = useRef<SVGSVGElement>(null);
  const large = graph.truncated || graph.nodes.length > 80;
  const { width, height } = useBoxSize(svg, !large);
  const layout = useMemo(() => large ? new Map<string, Point>() : forceLayout(graph), [graph, large]);
  const labelled = graph.nodes.length <= 24;
  const labelSpace = labelled ? Math.min(112, 7 * Math.max(0, ...graph.nodes.map((node) => shortLabel(node.id).length))) + 16 : 0;
  const positions = useMemo(() => fitLayout(layout, width, height, labelSpace), [layout, width, height, labelSpace]);
  if (large) {
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
  const componentOrder = [...new Set(nodes.filter((node) => !node.isolated && node.component != null).map((node) => Number(node.component)))].sort((a, b) => a - b);
  const arcs = graph.directed ? new Set(edges.map((edge) => arcKey(edge.source, edge.target))) : null;

  return (
    <div className="graph-preview">
      <svg ref={svg} viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Backbone graph preview">
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
              <circle r="9" className={node.isolated ? "graph-node is-isolated" : node.retained ? "graph-node is-retained" : "graph-node"} style={node.isolated || node.component == null ? undefined : { fill: componentColor(componentOrder.indexOf(Number(node.component))) }}>
                <title>{shortLabel(node.id)}{node.isolated ? " · Isolated in backbone" : node.component != null ? ` · Component ${node.component}` : ""}</title>
              </circle>
              {labelled && <text x="10" y="-10">{shortLabel(node.id)}</text>}
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

/** Deterministic Fruchterman-Reingold layout. fitLayout turns and scales it into the drawing. */
export function forceLayout(graph: NetworkPreviewProps["graph"]): Map<string, Point> {
  const ids = graph.nodes.map((node) => String(node.id));
  const index = new Map(ids.map((id, i) => [id, i]));
  const links = graph.edges
    .map((edge) => [index.get(String(edge.source)), index.get(String(edge.target))] as const)
    .filter((pair): pair is readonly [number, number] => pair[0] !== undefined && pair[1] !== undefined && pair[0] !== pair[1]);
  const count = ids.length;
  const size = 440;
  const k = Math.sqrt((size * size) / Math.max(count, 1)) * 0.75;
  const x = ids.map((_, i) => Math.cos((i / Math.max(count, 1)) * Math.PI * 2 - Math.PI / 2) * size * 0.4);
  const y = ids.map((_, i) => Math.sin((i / Math.max(count, 1)) * Math.PI * 2 - Math.PI / 2) * size * 0.4);
  let temperature = size / 8;
  for (let step = 0; step < 300 && count > 1; step += 1) {
    const dx = new Array<number>(count).fill(0);
    const dy = new Array<number>(count).fill(0);
    for (let a = 0; a < count; a += 1) {
      for (let b = a + 1; b < count; b += 1) {
        const ox = x[a]! - x[b]!;
        const oy = y[a]! - y[b]!;
        const distance = Math.max(Math.hypot(ox, oy), 0.01);
        const force = (k * k) / distance;
        add(dx, a, (ox / distance) * force); add(dy, a, (oy / distance) * force);
        add(dx, b, -((ox / distance) * force)); add(dy, b, -((oy / distance) * force));
      }
    }
    for (const [a, b] of links) {
      const ox = x[a]! - x[b]!;
      const oy = y[a]! - y[b]!;
      const distance = Math.max(Math.hypot(ox, oy), 0.01);
      const force = (distance * distance) / k;
      add(dx, a, -((ox / distance) * force)); add(dy, a, -((oy / distance) * force));
      add(dx, b, (ox / distance) * force); add(dy, b, (oy / distance) * force);
    }
    for (let i = 0; i < count; i += 1) {
      // Gentle pull to the centre keeps separate components on screen.
      const px = x[i]!;
      const py = y[i]!;
      const fx = dx[i]! - px * 0.002 * k;
      const fy = dy[i]! - py * 0.002 * k;
      const length = Math.max(Math.hypot(fx, fy), 0.01);
      x[i] = px + (fx / length) * Math.min(length, temperature);
      y[i] = py + (fy / length) * Math.min(length, temperature);
    }
    temperature *= 0.985;
  }
  return new Map(ids.map((id, i) => [id, { x: x[i]!, y: y[i]! }]));
}

/**
 * Places a layout in a width × height drawing, one unit per screen pixel, so
 * labels keep their size. The layout is turned so its longest spread runs
 * along the longer side, then scaled evenly to fit.
 */
export function fitLayout(layout: Map<string, Point>, width: number, height: number, labelSpace = 0): Map<string, Point> {
  const points = [...layout.values()];
  if (!points.length) return new Map();
  const margin = 22;
  const left = margin;
  const right = Math.max(left + 1, width - margin - labelSpace);
  // Labels sit above their node, so the top keeps room for one line.
  const top = margin + (labelSpace ? 12 : 0);
  const bottom = Math.max(top + 1, height - margin);
  if (points.length === 1) return new Map([...layout.keys()].map((id) => [id, { x: (left + right) / 2, y: (top + bottom) / 2 }]));
  const meanX = points.reduce((sum, point) => sum + point.x, 0) / points.length;
  const meanY = points.reduce((sum, point) => sum + point.y, 0) / points.length;
  let xx = 0, yy = 0, xy = 0;
  for (const point of points) {
    xx += (point.x - meanX) ** 2;
    yy += (point.y - meanY) ** 2;
    xy += (point.x - meanX) * (point.y - meanY);
  }
  const angle = 0.5 * Math.atan2(2 * xy, xx - yy) - (height > width ? Math.PI / 2 : 0);
  const cos = Math.cos(-angle);
  const sin = Math.sin(-angle);
  const turned = new Map([...layout].map(([id, point]) => {
    const dx = point.x - meanX;
    const dy = point.y - meanY;
    return [id, { x: dx * cos - dy * sin, y: dx * sin + dy * cos }];
  }));
  const xs = [...turned.values()].map((point) => point.x);
  const ys = [...turned.values()].map((point) => point.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  // Small networks keep close to their natural size instead of stretching across a wide panel.
  const scale = Math.min(1.5, (right - left) / Math.max(maxX - minX, 1e-9), (bottom - top) / Math.max(maxY - minY, 1e-9));
  const offsetX = (left + right) / 2 - ((minX + maxX) / 2) * scale;
  const offsetY = (top + bottom) / 2 - ((minY + maxY) / 2) * scale;
  return new Map([...turned].map(([id, point]) => [id, { x: point.x * scale + offsetX, y: point.y * scale + offsetY }]));
}

/** The element's size in CSS pixels, rounded to 4 px so tiny shifts do not redraw it. */
function useBoxSize(ref: RefObject<Element | null>, shown: boolean): { width: number; height: number } {
  const [size, setSize] = useState({ width: 520, height: 360 });
  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return;
    const measure = () => {
      const box = element.getBoundingClientRect();
      if (!box.width || !box.height) return;
      const width = Math.max(160, Math.round(box.width / 4) * 4);
      const height = Math.max(160, Math.round(box.height / 4) * 4);
      setSize((current) => current.width === width && current.height === height ? current : { width, height });
    };
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [ref, shown]);
  return size;
}

function add(values: number[], index: number, amount: number): void {
  values[index] = (values[index] ?? 0) + amount;
}

function arcKey(source: JsonValue, target: JsonValue): string {
  return JSON.stringify([source, target]);
}

function shortLabel(value: JsonValue): string {
  const text = String(value);
  return text.length > 16 ? `${text.slice(0, 13)}...` : text;
}
