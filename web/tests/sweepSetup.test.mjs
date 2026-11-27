import assert from "node:assert/strict";
import test from "node:test";
import { compileSweep, newSweepDraft, sweepSettings } from "../src/sweepSetup.ts";

const environment = { directed: false, weighted: true };
const method = "link_prediction_iforest";
const schema = {
  methods: [{ name: method, target: "edge", preferred_direction: "higher" }],
  controls: {
    methods: {
      [method]: [
        { name: "n_estimators", label: "Isolation trees", control: "number", default: 100, min: 1, step: 1 },
        { name: "distance_transform", label: "Weight means", control: "select", default: "inverse",
          options: [{ value: "inverse", label: "Strength" }, { value: "identity", label: "Distance" }] },
      ],
    },
    filters: {
      fraction: [{ name: "fraction", label: "Retained fraction", control: "range", default: 0.1, min: 0, max: 1 }],
      threshold: [{ name: "threshold_value", label: "Cutoff", control: "range", default: 0, min: 0, max: 1 }],
    },
  },
};
const resolved = {
  pipeline: {
    method: { name: method, parameters: { weight: null, similarities: ["preferential_attachment", "shortest_path"], n_estimators: 30 } },
    filter: { name: "fraction", parameters: { fraction: 0.5, direction: "lower" } },
  },
};

test("the current setting is visible but does not create an unconfirmed sweep", () => {
  const draft = newSweepDraft(1, method, "fraction", schema, environment, resolved);
  assert.equal(draft.name, "Current extraction");
  assert.deepEqual(draft.variations, [{ id: 1, key: "filter.fraction", text: "0.5" }]);
  const incomplete = compileSweep([draft], schema, environment);
  assert.match(incomplete.error, /two or more different values for retained fraction/);
  assert.equal(incomplete.count, 0);
  assert.deepEqual(incomplete.configurations, []);
});

test("varying settings cross within a setup and separate fixed setups add one run", () => {
  const draft = newSweepDraft(1, method, "fraction", schema, environment, resolved);
  draft.variations = [
    { id: 1, key: "filter.fraction", text: "25%, 0.5, 75%" },
    { id: 2, key: "method.n_estimators", text: "30, 60" },
  ];
  const baseline = { ...draft, id: 2, name: "Fixed baseline", variations: [] };
  const plan = compileSweep([draft, baseline], schema, environment);
  assert.equal(plan.count, 7);
  assert.equal(plan.error, "");
  assert.deepEqual(plan.configurations, [
    {
      name: "Current extraction",
      method: { name: method, parameters: { weight: null, similarities: [["preferential_attachment", "shortest_path"]], n_estimators: [30, 60] } },
      filter: { name: "fraction", parameters: { fraction: [0.25, 0.5, 0.75], direction: "lower" } },
    },
    {
      name: "Fixed baseline",
      method: { name: method, parameters: { weight: null, similarities: [["preferential_attachment", "shortest_path"]], n_estimators: 30 } },
      filter: { name: "fraction", parameters: { fraction: 0.5, direction: "lower" } },
    },
  ]);
});

test("invalid fractions, integer settings, and identical fractions are rejected", () => {
  const draft = newSweepDraft(1, method, "fraction", schema, environment, resolved);
  for (const text of ["50%, 110%", "0.25, 50", "0.25, NaN", "0.25, %"]) {
    draft.variations[0].text = text;
    assert.match(compileSweep([draft], schema, environment).error, /valid values for retained fraction/);
  }
  draft.variations[0].text = "0.5, 50%";
  assert.match(compileSweep([draft], schema, environment).error, /two or more different values/);
  draft.variations[0].text = "25%, 50%";
  draft.variations.push({ id: 2, key: "method.n_estimators", text: "10, 12.5" });
  assert.match(compileSweep([draft], schema, environment).error, /valid values for isolation trees/);
});

test("cutoffs follow score units and weight-only settings are omitted for unweighted data", () => {
  const unweighted = { ...environment, weighted: false };
  const draft = newSweepDraft(1, method, "threshold", schema, unweighted);
  assert.deepEqual(sweepSettings(draft, schema, unweighted).map((setting) => setting.key), ["filter.value", "method.n_estimators"]);
  draft.variations[0].text = "-2, 3000";
  const plan = compileSweep([draft], schema, unweighted);
  assert.equal(plan.count, 2);
  assert.deepEqual(plan.configurations[0].filter.parameters, { value: [-2, 3000] });
});

test("outgoing and incoming aggregation are offered only on directed networks", async () => {
  const { withDirectedOnlyOptions } = await import("../src/sweepSetup.ts");
  const control = {
    name: "pvalue_aggregation",
    label: "Endpoint p-value",
    control: "select",
    default: "min",
    options: [
      { value: "min", label: "minimum" },
      { value: "out", label: "outgoing only", directed_only: true },
      { value: "in", label: "incoming only", directed_only: true },
    ],
  };
  const undirected = withDirectedOnlyOptions(control, false);
  assert.deepEqual(undirected.options.filter((option) => option.disabled).map((option) => option.value), ["out", "in"]);
  assert.equal(withDirectedOnlyOptions(control, true), control);
});
