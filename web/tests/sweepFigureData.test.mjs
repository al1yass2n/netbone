import assert from "node:assert/strict";
import test from "node:test";
import { numericSweepParameters, sweepRunLabels, tradeoffRows, trajectoryRows } from "../src/sweepFigureData.ts";

const sweep = {
  setup_names: { first_a: "First setup", first_b: "First setup", second_a: "Second setup", second_b: "Second setup" },
  runs: [
    { run_id: 1, pipeline_name: "first_a", status: "ok", varied_parameters: { method_parameters: {}, filter_parameters: { fraction: 0.2 } } },
    { run_id: 2, pipeline_name: "first_b", status: "ok", varied_parameters: { method_parameters: {}, filter_parameters: { fraction: 0.4 } } },
    { run_id: 3, pipeline_name: "second_a", status: "ok", varied_parameters: { method_parameters: {}, filter_parameters: { fraction: 0.2 } } },
    { run_id: 4, pipeline_name: "second_b", status: "failed", explanation: "Filter failed", varied_parameters: { method_parameters: {}, filter_parameters: { fraction: 0.4 } } },
  ],
  metrics: [
    { run_id: 2, metric: "edge_retention", status: "ok", value: 0.5 },
    { run_id: 1, metric: "edge_retention", status: "ok", value: 0.25 },
    { run_id: 3, metric: "edge_retention", status: "undefined", value: null, explanation: "No edges" },
    { run_id: 4, metric: null, status: "failed", value: null, explanation: "Filter failed" },
    { run_id: 2, metric: "connected_component_count", status: "ok", value: 1 },
    { run_id: 1, metric: "connected_component_count", status: "ok", value: 2 },
    { run_id: 3, metric: "connected_component_count", status: "ok", value: 3 },
  ],
};

test("numeric sweep parameter discovery and trajectory preserve named setups", () => {
  assert.deepEqual(numericSweepParameters(sweep.runs), ["filter.fraction"]);
  const rows = trajectoryRows(sweep, "filter.fraction", "edge_retention");
  assert.deepEqual(rows.map((row) => [row.setup, row.x, row.y]), [
    ["First setup", 0.2, 0.25], ["First setup", 0.4, 0.5],
    ["Second setup", 0.2, null], ["Second setup", 0.4, null],
  ]);
  assert.equal(rows[2].status, "undefined");
  assert.equal(rows[2].explanation, "No edges");
  assert.equal(rows[3].status, "failed");
  assert.deepEqual(trajectoryRows(sweep, "filter.fraction", "edge_retention", "First setup").map((row) => row.runId), [1, 2]);
});

test("trade-off joins metrics by run and never plots invalid values", () => {
  const rows = tradeoffRows(sweep, "edge_retention", "connected_component_count");
  assert.deepEqual(rows.map((row) => [row.x, row.y]), [[0.25, 2], [0.5, 1], [null, 3], [null, null]]);
  assert.equal(rows[2].status, "undefined");
  assert.match(rows[2].explanation, /No edges/);
  assert.deepEqual(tradeoffRows(sweep, "edge_retention", "connected_component_count", "Second setup").map((row) => row.runId), [3, 4]);
});

test("another varied parameter creates separate trajectory series", () => {
  const changed = structuredClone(sweep);
  changed.runs[1].varied_parameters.method_parameters = { c: 2 };
  changed.runs[0].varied_parameters.method_parameters = { c: 1 };
  const rows = trajectoryRows(changed, "filter.fraction", "edge_retention", "First setup");
  assert.notEqual(rows[0].series, rows[1].series);
});

test("run names include both changing settings and omit settings fixed within each setup", () => {
  const changed = structuredClone(sweep);
  for (const [index, run] of changed.runs.entries()) {
    run.varied_parameters.method_parameters = { endpoint_rule: index === 1 ? "maximum" : "minimum", weight: "weight" };
  }
  const labels = sweepRunLabels(changed);
  assert.equal(labels.get(1), "First setup · endpoint rule = minimum · retained fraction = 20%");
  assert.equal(labels.get(2), "First setup · endpoint rule = maximum · retained fraction = 40%");
  assert.equal(labels.get(3), "Second setup · retained fraction = 20%");
  assert.equal(trajectoryRows(changed, "filter.fraction", "edge_retention")[0].runLabel, labels.get(1));
  assert.equal(tradeoffRows(changed, "edge_retention", "connected_component_count")[1].runLabel, labels.get(2));
});
