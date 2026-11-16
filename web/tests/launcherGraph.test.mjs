import assert from "node:assert/strict";
import test from "node:test";
import { createLauncherGraph, launcherFrame } from "../src/launcherGraph.ts";

const edgeNodes = ({ from, to }) => [from, to];

function connectedNodes(edges, start = edges[0].from) {
  const neighbors = new Map();
  for (const { from, to } of edges) {
    if (!neighbors.has(from)) neighbors.set(from, []);
    if (!neighbors.has(to)) neighbors.set(to, []);
    neighbors.get(from).push(to);
    neighbors.get(to).push(from);
  }
  const seen = new Set([start]);
  for (const node of seen) {
    neighbors.get(node).forEach((neighbor) => seen.add(neighbor));
  }
  return seen;
}

function components(edges, nodes) {
  const remaining = new Set(edges.flatMap(edgeNodes));
  const groups = [];
  for (const start of remaining) {
    const members = connectedNodes(edges, start);
    for (const node of members) remaining.delete(node);
    const points = Array.from(members, (node) => nodes[node]);
    groups.push({
      members,
      edges: edges.filter(({ from }) => members.has(from)),
      left: Math.min(...points.map(([x]) => x)),
      right: Math.max(...points.map(([x]) => x)),
      top: Math.min(...points.map(([, y]) => y)),
      baseline: Math.max(...points.map(([, y]) => y)),
    });
  }
  return groups.sort((a, b) => a.left - b.left);
}

test("the launcher uses the same weighted word and surrounding network on every visit", () => {
  assert.deepEqual(createLauncherGraph(), createLauncherGraph());
});

test("the weighted network is sparse and connected, with room at the frame edges", () => {
  const { nodes, edges, degrees } = createLauncherGraph();
  const { left, top, width, height } = launcherFrame;
  assert.ok(nodes.every(([x, y]) => x > left + 20 && x < left + width - 20
    && y > top + 20 && y < top + height - 20));
  assert.ok(edges.every(({ from, to, weight }) =>
    from >= 0 && to < nodes.length && from < to && weight >= 1 && weight <= 5));
  assert.equal(new Set(edges.map(({ from, to }) => `${from}-${to}`)).size, edges.length);
  assert.equal(connectedNodes(edges).size, nodes.length);
  assert.ok(edges.length < nodes.length * 1.3);
  assert.deepEqual(degrees, nodes.map((_, index) =>
    edges.filter(({ from, to }) => from === index || to === index).length));
  assert.ok(new Set(degrees).size >= 4);
  assert.equal(new Set(edges.map(({ weight }) => weight)).size, 5);
});

test("the seven highlighted glyphs form a centered mixed-case Netbone", () => {
  const { nodes, lettering } = createLauncherGraph();
  const glyphs = components(lettering, nodes);
  assert.equal(glyphs.length, 7);
  const [capitalN, firstE, t, b, o, lowercaseN, lastE] = glyphs;
  const center = (capitalN.left + lastE.right) / 2;
  const frameCenter = launcherFrame.left + launcherFrame.width / 2;
  assert.ok(Math.abs(center - frameCenter) < 25);
  assert.ok(glyphs.every((glyph) => Math.abs(glyph.baseline - capitalN.baseline) <= 4));
  assert.ok(glyphs.slice(1).every((glyph, index) => glyph.left - glyphs[index].right >= 20));
  assert.equal(capitalN.top, b.top);
  assert.ok(capitalN.top < t.top && t.top < o.top);
  assert.ok([firstE, lowercaseN, lastE].every((glyph) => glyph.top === o.top));

  for (const x of [capitalN.left, capitalN.right]) {
    const upright = capitalN.edges.filter((edge) =>
      edgeNodes(edge).every((node) => nodes[node][0] === x));
    const ys = Array.from(connectedNodes(upright), (node) => nodes[node][1]);
    assert.equal(Math.min(...ys), capitalN.top);
    assert.equal(Math.max(...ys), capitalN.baseline);
  }
  const diagonal = capitalN.edges.filter(({ from, to }) => nodes[from][0] !== nodes[to][0]);
  const diagonalPoints = Array.from(connectedNodes(diagonal), (node) => nodes[node]);
  assert.ok(diagonalPoints.some(([x, y]) => x === capitalN.left && y === capitalN.top));
  assert.ok(diagonalPoints.some(([x, y]) => x === capitalN.right && y === capitalN.baseline));

  for (const letter of [firstE, b, o, lastE]) {
    assert.equal(letter.edges.length, letter.members.size);
  }
  for (const letter of [capitalN, t, lowercaseN]) {
    assert.equal(letter.edges.length, letter.members.size - 1);
  }
  for (const e of [firstE, lastE]) {
    const crossbar = e.edges.find(({ from, to }) => {
      const [[x1, y1], [x2, y2]] = [nodes[from], nodes[to]];
      return x1 === e.left && x2 === e.right && y1 === y2 && y1 > e.top && y1 < e.baseline;
    });
    assert.ok(crossbar);
  }
});

test("subdued connectors join the glyphs and both margin clusters in one bridge", () => {
  const { nodes, edges, lettering, bridge, backbones } = createLauncherGraph();
  const allEdges = new Set(edges);
  const highlighted = new Set([...lettering, ...bridge]);
  assert.ok([...highlighted].every((edge) => allEdges.has(edge)));
  assert.equal(highlighted.size, lettering.length + bridge.length);
  assert.ok(Math.max(...bridge.map(({ weight }) => weight)) < Math.min(...lettering.map(({ weight }) => weight)));

  const glyphs = components(lettering, nodes);
  const first = glyphs[0];
  const last = glyphs.at(-1);
  const routeEdges = new Set([...backbones.upper, ...backbones.lower]);
  const clusters = components(edges.filter((edge) =>
    edgeNodes(edge).every((node) => nodes[node][0] < first.left) ||
    edgeNodes(edge).every((node) => nodes[node][0] > last.right)
  ), nodes);
  assert.equal(clusters.length, 2);
  const [left, right] = clusters;
  const leftClusterXs = left.edges.filter((edge) => !routeEdges.has(edge)).flatMap(edgeNodes).map((node) => nodes[node][0]);
  const rightClusterXs = right.edges.filter((edge) => !routeEdges.has(edge)).flatMap(edgeNodes).map((node) => nodes[node][0]);
  assert.ok(first.left - Math.max(...leftClusterXs) >= 100);
  assert.ok(Math.min(...rightClusterXs) - last.right >= 100);
  assert.ok(clusters.every((cluster) => cluster.top < 100 && cluster.baseline > 300));

  const sections = [left, ...glyphs, right];
  assert.equal(bridge.length, sections.length - 1);
  for (const [index, section] of sections.slice(0, -1).entries()) {
    const next = sections[index + 1];
    assert.ok(section.right < next.left);
    assert.equal(bridge.filter(({ from, to }) => section.members.has(from) && next.members.has(to)).length, 1);
  }
});

test("the three backbones retain different connected edge sets with a common approach", () => {
  const { nodes, edges, lettering, bridge, backbones } = createLauncherGraph();
  const allEdges = new Set(edges);
  const [word, upper, lower] = [backbones.word, backbones.upper, backbones.lower].map((selection) => new Set(selection));
  const selections = [word, upper, lower];
  const allXs = nodes.map(([x]) => x);
  for (const backbone of Object.values(backbones)) {
    const retained = new Set(backbone.flatMap(edgeNodes));
    assert.equal(new Set(backbone).size, backbone.length);
    assert.ok(backbone.every((edge) => allEdges.has(edge)));
    assert.deepEqual(connectedNodes(backbone), retained);
    const xs = [...retained].map((node) => nodes[node][0]);
    assert.equal(Math.min(...xs), Math.min(...allXs));
    assert.equal(Math.max(...xs), Math.max(...allXs));
  }
  const wordBridge = [...lettering, ...bridge];
  assert.ok(wordBridge.every((edge) => word.has(edge) && !upper.has(edge) && !lower.has(edge)));
  assert.ok([...word].some((edge) => upper.has(edge) && lower.has(edge)));
  for (const selection of selections) {
    assert.ok([...selection].some((edge) =>
      selections.every((other) => other === selection || !other.has(edge))));
  }
});

test("the upper and lower backbones leave a clear band around the word", () => {
  const { nodes, lettering, backbones } = createLauncherGraph();
  const letterPoints = lettering.flatMap(edgeNodes).map((node) => nodes[node]);
  const left = Math.min(...letterPoints.map(([x]) => x));
  const right = Math.max(...letterPoints.map(([x]) => x));
  const top = Math.min(...letterPoints.map(([, y]) => y));
  const baseline = Math.max(...letterPoints.map(([, y]) => y));

  function crossingHeights(selection) {
    return selection.flatMap(({ from, to }) => {
      const [[x1, y1], [x2, y2]] = [nodes[from], nodes[to]].sort(([a], [b]) => a - b);
      if (x2 < left || x1 > right) return [];
      if (x1 === x2) return [y1, y2];
      return [Math.max(x1, left), Math.min(x2, right)]
        .map((x) => y1 + (y2 - y1) * (x - x1) / (x2 - x1));
    });
  }

  const upper = crossingHeights(backbones.upper);
  const lower = crossingHeights(backbones.lower);
  assert.ok(upper.length >= 10 && upper.every((y) => y <= top - 50));
  assert.ok(lower.length >= 10 && lower.every((y) => y >= baseline + 65));
});
