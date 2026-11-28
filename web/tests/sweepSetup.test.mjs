import assert from "node:assert/strict";
import test from "node:test";
import { loadSource } from "./sourceModule.mjs";

const { compileSweep, defaultRange, newSweepDraft, plannedRuns, settingRange, sweepSettings, withDirectedOnlyOptions } = await loadSource("/src/sweepSetup.ts");

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

test("a new sweep starts with a range of retained fractions it can run at once", () => {
  const draft = newSweepDraft(1, method, "fraction", schema, environment, resolved);
  assert.equal(draft.name, "Current settings");
  assert.deepEqual(draft.variations, [{
    id: 1, key: "filter.fraction", mode: "range", range: { from: "10", to: "90", step: "20" }, text: "10%, 30%, 50%, 70%, 90%",
  }]);
  const plan = compileSweep([draft], schema, environment);
  assert.equal(plan.error, "");
  assert.equal(plan.count, 5);
  assert.deepEqual(plan.configurations[0].filter.parameters.fraction, [0.1, 0.3, 0.5, 0.7, 0.9]);
  assert.deepEqual(plannedRuns([draft], schema, environment), ["Retained fraction: 10%", "Retained fraction: 30%", "Retained fraction: 50%", "Retained fraction: 70%", "Retained fraction: 90%"]);
});

test("a range is checked against the setting's limits in the units it is typed in", () => {
  const settings = sweepSettings(newSweepDraft(1, method, "fraction", schema, environment), schema, environment);
  const fraction = settings.find((setting) => setting.key === "filter.fraction");
  const trees = settings.find((setting) => setting.key === "method.n_estimators");
  assert.equal(settingRange({ from: "20", to: "120", step: "50" }, fraction).error, "Use values from 0% to 100%.");
  assert.equal(settingRange({ from: "50", to: "40", step: "5" }, fraction).error, "To must be at least From.");
  assert.equal(settingRange({ from: "50", to: "50", step: "5" }, fraction).error, "This range makes only one value.");
  assert.equal(settingRange({ from: "1", to: "", step: "1" }, fraction).error, "Enter a number for From, To and Step.");
  assert.equal(settingRange({ from: "10", to: "20", step: "2.5" }, trees).error, "Use whole numbers.");
  assert.equal(settingRange({ from: "0", to: "60", step: "30" }, trees).error, "Use values of 1 or more.");
  assert.deepEqual(settingRange({ from: "50", to: "150", step: "50" }, trees), { values: [50, 100, 150], text: "50, 100, 150", error: "" });
  assert.deepEqual(defaultRange(trees, "100"), { from: "100", to: "200", step: "25" });
  const draft = newSweepDraft(1, method, "fraction", schema, environment);
  draft.variations[0] = { ...draft.variations[0], range: { from: "20", to: "120", step: "50" } };
  assert.equal(compileSweep([draft], schema, environment).error, "Retained fraction: Use values from 0% to 100%.");
  const other = { ...draft, id: 2, name: "Wide range" };
  assert.equal(compileSweep([draft, other], schema, environment).error, "Setup 1: Retained fraction: Use values from 0% to 100%.");
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
      name: "Current settings",
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
  draft.variations[0].mode = "list";
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
  // A cutoff has no fixed bounds, so it starts at 0 and steps by a quarter.
  assert.equal(draft.variations[0].text, "0, 0.25, 0.5, 0.75, 1");
  draft.variations[0] = { ...draft.variations[0], mode: "list", text: "-2, 3000" };
  const plan = compileSweep([draft], schema, unweighted);
  assert.equal(plan.count, 2);
  assert.deepEqual(plan.configurations[0].filter.parameters, { value: [-2, 3000] });
});

test("outgoing and incoming aggregation are offered only on directed networks", () => {
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

test("the random seed appears only when ties are broken at random", () => {
  const tieSchema = {
    ...schema,
    controls: {
      ...schema.controls,
      filters: {
        fraction: [
          { name: "fraction", label: "Retained fraction", control: "range", default: 0.1, min: 0, max: 1 },
          { name: "tie_policy", label: "Ties at the cutoff", control: "select", default: "include_all_ties",
            options: [{ value: "include_all_ties", label: "keep all ties" }, { value: "random_seeded", label: "random, seeded" }] },
          { name: "random_seed", label: "Random seed", control: "number", default: 0, min: 0, step: 1, advanced: true,
            shown_when: { tie_policy: "random_seeded" } },
        ],
      },
    },
  };
  const keys = (draft) => sweepSettings(draft, tieSchema, environment).map((setting) => setting.key);
  const draft = newSweepDraft(1, method, "fraction", tieSchema, environment);
  assert.ok(!keys(draft).includes("filter.random_seed"));
  draft.fixed["filter.tie_policy"] = "random_seeded";
  assert.ok(keys(draft).includes("filter.random_seed"));
  draft.fixed["filter.random_seed"] = "7";
  draft.variations = [{ id: 1, key: "filter.fraction", text: "0.2, 0.4" }];
  assert.deepEqual(compileSweep([draft], tieSchema, environment).configurations[0].filter.parameters,
    { fraction: [0.2, 0.4], tie_policy: "random_seeded", random_seed: 7 });
  // Varying the tie policy can pick the random one, so the seed stays available.
  const varied = { ...draft, fixed: {}, variations: [{ id: 1, key: "filter.tie_policy", text: "include_all_ties, random_seeded" }] };
  assert.ok(keys(varied).includes("filter.random_seed"));
});
