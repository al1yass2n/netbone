import type { CSSProperties } from "react";
import { createLauncherGraph, launcherFrame } from "../launcherGraph";
import "./LauncherBackdrop.css";

type BackboneOpacity = CSSProperties & {
  "--backbone-word": number;
  "--backbone-upper": number;
  "--backbone-lower": number;
};

const { nodes, edges, degrees, lettering, bridge, backbones } = createLauncherGraph();
const { left, top, width, height } = launcherFrame;
const letterEdges = new Set(lettering);
const bridgeEdges = new Set(bridge);
const letterNodes = new Set(lettering.flatMap(({ from, to }) => [from, to]));
const word = new Set(backbones.word);
const upper = new Set(backbones.upper);
const lower = new Set(backbones.lower);
const links = edges.map((edge) => {
  const { from, to, weight } = edge;
  const [x1, y1] = nodes[from]!;
  const [x2, y2] = nodes[to]!;
  const kind = letterEdges.has(edge) ? "letter" : bridgeEdges.has(edge) ? "bridge" : "context";
  const isSelected = word.has(edge) || upper.has(edge) || lower.has(edge);
  const opacity: BackboneOpacity = {
    "--backbone-word": word.has(edge) ? (kind === "letter" ? 1 : 0.46) : 0,
    "--backbone-upper": upper.has(edge) ? 0.82 : 0,
    "--backbone-lower": lower.has(edge) ? 0.82 : 0,
  };
  return { key: `${from}-${to}`, coordinates: { x1, y1, x2, y2 }, weight, kind, isSelected, opacity };
});

/** Draw the weighted illustration on the home page. */
export default function LauncherBackdrop() {
  return (
    <div className="launcher-backdrop" role="img" aria-label="A weighted network spells Netbone. The lettering, upper route, and lower route show three backbones.">
      <svg className="launcher-backdrop-graph" viewBox={`${left} ${top} ${width} ${height}`} aria-hidden="true" focusable="false">
        <g className="launcher-base-links">
          {links.map(({ key, coordinates, weight, kind }) => (
            <line key={key} {...coordinates} data-kind={kind} strokeWidth={(kind === "letter" ? 0.85 : 0.45) + weight * 0.24} />
          ))}
        </g>
        <g className="launcher-backbone-links">
          {links.filter(({ isSelected }) => isSelected).map(({ key, coordinates, weight, kind, opacity }) => (
            <line key={key} {...coordinates} data-kind={kind} strokeWidth={(kind === "letter" ? 1.8 : 0.95) + weight * 0.25} style={opacity} />
          ))}
        </g>
        {nodes.map(([cx, cy], index) => {
          const isLetter = letterNodes.has(index);
          const radius = 2.1 + degrees[index]! * (isLetter ? 0.64 : 0.92);
          return <circle key={index} className="launcher-node-core" data-letter={isLetter} cx={cx} cy={cy} r={radius} />;
        })}
      </svg>
    </div>
  );
}
