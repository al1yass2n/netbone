import type { DataDraft, NetworkContext } from "./types";

export interface GuidedExample {
  name: string;
  label: string;
  description: string;
  data: DataDraft;
  context: NetworkContext;
}

const baseDraft: DataDraft = {
  mode: "static",
  text: "",
  filename: "",
  delimiter: ",",
  source: "source",
  target: "target",
  weight: "",
  time: "time",
  eventWeight: "",
  directed: false,
  directionMode: "preserve",
  reciprocalMerge: "sum",
  temporalWeighting: "baseline",
  temporalParameters: {},
  evaluationTime: "",
  timeUnit: "",
  snapshotSize: "",
  snapshotOrigin: "",
  zeroWeightPolicy: "drop",
};

export const emptyDataDraft: DataDraft = { ...baseDraft };

export const defaultContext: NetworkContext = {
  dataset: "Network analysis",
  nodes: "entities",
  edges: "relationships",
  weight: "edge weight",
  weightSemantics: "",
  time: "observation time",
};

export const guidedExamples: GuidedExample[] = [
  {
    name: "weighted",
    label: "Weighted relationships",
    description: "Researchers linked by how often they publish together.",
    data: {
      ...baseDraft,
      filename: "weighted-relationships.csv",
      weight: "weight",
      text: "source,target,weight\nalice,bob,4\nbob,carol,1\ncarol,dana,2\nalice,carol,3\n",
    },
    context: {
      dataset: "Research collaboration network",
      nodes: "researchers",
      edges: "collaborations",
      weight: "number of joint publications",
      weightSemantics: "strength",
      time: "observation time",
    },
  },
  {
    name: "unweighted",
    label: "Unweighted relationships",
    description: "Friendships where every connection counts equally.",
    data: {
      ...baseDraft,
      filename: "unweighted-relationships.csv",
      text: "source,target\nalice,bob\nbob,carol\ncarol,dana\nalice,carol\n",
    },
    context: {
      dataset: "Friendship network",
      nodes: "people",
      edges: "friendships",
      weight: "edge weight",
      weightSemantics: "strength",
      time: "observation time",
    },
  },
  {
    name: "temporal",
    label: "Temporal interactions",
    description: "Repeated interactions recorded over time.",
    data: {
      ...baseDraft,
      mode: "temporal",
      filename: "temporal-interactions.csv",
      time: "time",
      eventWeight: "magnitude",
      temporalWeighting: "asf",
      temporalParameters: { p: 3, q: 0, a: 5 },
      text: "source,target,time,magnitude\nalice,bob,0,2\nbob,alice,1,3\nalice,carol,2,1\ncarol,dana,3,2\nalice,bob,4,1\n",
    },
    context: {
      dataset: "Temporal interaction network",
      nodes: "people",
      edges: "interactions",
      weight: "aggregated interaction magnitude",
      weightSemantics: "strength",
      time: "observation time",
    },
  },
];
