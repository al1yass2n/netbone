type Point = readonly [number, number];
type WeightedEdge = { from: number; to: number; weight: number };
type Section = {
  x: number;
  points: readonly Point[];
  links: readonly (readonly [number, number, number])[];
  entry: number;
  exit: number;
};

export const launcherFrame = { left: -110, top: -8, width: 1420, height: 424 };

const leftCluster: Section = {
  x: -96,
  points: [
    [35, 189], [62, 106], [84, 274], [112, 52], [135, 144], [115, 201],
    [130, 321], [163, 101], [176, 248], [195, 156], [212, 214], [194, 307], [57, 328],
  ],
  links: [
    [0, 1, 2], [0, 5, 3], [1, 3, 1], [1, 4, 2], [2, 5, 3], [2, 6, 2],
    [2, 12, 1], [3, 7, 2], [4, 7, 2], [4, 9, 1], [5, 8, 2], [6, 11, 2],
    [7, 9, 3], [8, 10, 4], [8, 11, 1], [9, 10, 3],
  ],
  entry: 0,
  exit: 10,
};

const rightCluster: Section = {
  x: 96,
  points: [
    [967, 249], [984, 174], [1007, 301], [1021, 91], [1048, 230], [1044, 348],
    [1092, 146], [1096, 270], [1095, 322], [1141, 79], [1153, 192], [1170, 244],
    [1149, 345],
  ],
  links: [
    [0, 1, 3], [0, 2, 4], [0, 4, 2], [1, 3, 2], [1, 4, 2], [2, 5, 2],
    [3, 6, 1], [4, 6, 3], [4, 7, 2], [5, 8, 1], [6, 9, 2], [6, 10, 2],
    [7, 8, 2], [7, 11, 3], [8, 12, 1], [10, 11, 2],
  ],
  entry: 0,
  exit: 11,
};

const lowercaseE: Omit<Section, "x"> = {
  points: [
    [0, 213], [0, 188], [20, 163], [56, 163], [79, 187], [79, 213],
    [0, 239], [23, 265], [60, 265], [79, 252],
  ],
  links: [
    [0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 4, 4], [4, 5, 4], [0, 5, 5],
    [0, 6, 4], [6, 7, 4], [7, 8, 4], [8, 9, 4],
  ],
  entry: 6,
  exit: 9,
};

const letters: readonly Section[] = [
  {
    // N
    x: 253,
    points: [[0, 267], [0, 197], [0, 119], [45, 193], [90, 267], [90, 193], [90, 119]],
    links: [[0, 1, 4], [1, 2, 4], [2, 3, 5], [3, 4, 5], [4, 5, 4], [5, 6, 4]],
    entry: 1,
    exit: 4,
  },
  { x: 369, ...lowercaseE },
  {
    // t
    x: 470,
    points: [[23, 143], [23, 183], [0, 183], [53, 183], [23, 241], [36, 264], [53, 264]],
    links: [[0, 1, 4], [1, 2, 4], [1, 3, 4], [1, 4, 5], [4, 5, 4], [5, 6, 4]],
    entry: 4,
    exit: 6,
  },
  {
    // b
    x: 548,
    points: [
      [0, 119], [0, 186], [0, 242], [0, 267], [22, 163],
      [50, 163], [76, 187], [76, 239], [52, 265], [22, 265],
    ],
    links: [
      [0, 1, 4], [1, 2, 5], [2, 3, 4], [1, 4, 4], [4, 5, 4], [5, 6, 4],
      [6, 7, 4], [7, 8, 4], [8, 9, 4], [2, 9, 4],
    ],
    entry: 3,
    exit: 7,
  },
  {
    // o
    x: 647,
    points: [[0, 188], [22, 163], [53, 163], [78, 188], [78, 240], [54, 265], [24, 265], [0, 240]],
    links: [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 4, 4], [4, 5, 4], [5, 6, 4], [6, 7, 4], [0, 7, 4]],
    entry: 7,
    exit: 4,
  },
  {
    // n
    x: 747,
    points: [[0, 267], [0, 186], [0, 163], [24, 163], [55, 163], [80, 190], [80, 267]],
    links: [[0, 1, 5], [1, 2, 4], [1, 3, 4], [3, 4, 4], [4, 5, 4], [5, 6, 4]],
    entry: 0,
    exit: 6,
  },
  { x: 851, ...lowercaseE },
];

const upperRoute: readonly Point[] = [
  [229, 67], [350, 39], [461, 55], [547, 23], [630, 47],
  [735, 28], [835, 52], [934, 34], [1000, 65],
];

const lowerRoute: readonly Point[] = [
  [222, 353], [333, 376], [436, 343], [534, 380], [635, 354],
  [727, 387], [833, 347], [937, 377], [1003, 341],
];

function edgeKey(first: number, second: number) {
  return `${Math.min(first, second)}-${Math.max(first, second)}`;
}

/** Build one fixed weighted network with a word bridge and two alternate routes. */
export function createLauncherGraph() {
  const nodes: Point[] = [];
  const edges: WeightedEdge[] = [];
  const edgesByNodes = new Map<string, WeightedEdge>();
  const lettering: WeightedEdge[] = [];
  const bridge: WeightedEdge[] = [];
  const sections = [leftCluster, ...letters, rightCluster];
  let previousExit: number | undefined;

  function addEdge(start: number, end: number, weight: number) {
    const edge = { from: Math.min(start, end), to: Math.max(start, end), weight };
    edges.push(edge);
    edgesByNodes.set(edgeKey(start, end), edge);
    return edge;
  }

  function pathEdges(path: readonly number[]) {
    return path.slice(1).map((node, index) => edgesByNodes.get(edgeKey(path[index]!, node))!);
  }

  for (const [index, section] of sections.entries()) {
    const offset = nodes.length;
    for (const [x, y] of section.points) nodes.push([section.x + x, y]);

    for (const [start, end, weight] of section.links) {
      const edge = addEdge(offset + start, offset + end, weight);
      if (index > 0 && index < sections.length - 1) lettering.push(edge);
    }
    if (previousExit !== undefined) {
      bridge.push(addEdge(previousExit, offset + section.entry, 2));
    }
    previousExit = offset + section.exit;
  }

  const rightOffset = nodes.length - rightCluster.points.length;
  const rightNode = (index: number) => rightOffset + index;
  const sharedRight = [4, 7, rightCluster.exit].map(rightNode);

  function addAlternateRoute(points: readonly Point[], approach: readonly number[], exit: readonly number[]) {
    const offset = nodes.length;
    nodes.push(...points);
    const crossing = [approach.at(-1)!, ...points.map((_, index) => offset + index), rightNode(exit[0]!)];
    const crossingEdges = crossing.slice(1).map((node, index) =>
      addEdge(crossing[index]!, node, 1 + (index + approach.length) % 3));
    return [
      ...pathEdges(approach),
      ...crossingEdges,
      ...pathEdges([...exit.map(rightNode), ...sharedRight]),
    ];
  }

  const backbones = {
    word: [
      ...pathEdges([leftCluster.entry, 5, 8, leftCluster.exit]),
      ...lettering,
      ...bridge,
      ...pathEdges([rightNode(rightCluster.entry), ...sharedRight]),
    ],
    upper: addAlternateRoute(upperRoute, [leftCluster.entry, 1, 3, 7], [1]),
    lower: addAlternateRoute(lowerRoute, [leftCluster.entry, 5, 2, 6, 11], [2, rightCluster.entry]),
  };

  const degrees = nodes.map(() => 0);
  for (const { from, to } of edges) {
    degrees[from] = degrees[from]! + 1;
    degrees[to] = degrees[to]! + 1;
  }
  return { nodes, edges, degrees, lettering, bridge, backbones };
}
