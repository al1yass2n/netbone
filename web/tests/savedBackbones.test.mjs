import assert from "node:assert/strict";
import test from "node:test";
import { moveSavedBackbone, shortBackboneLabel, uniqueResultLabel } from "../src/savedBackbones.ts";

test("saved labels summarize the method and filter in a few characters", () => {
  assert.equal(shortBackboneLabel({ extraction: { method: "doubly_stochastic", filter: "fraction", filter_parameters: { fraction: 0.25 } } }), "DS 25%");
  assert.equal(shortBackboneLabel({ extraction: { method: "disparity", filter: "significance", filter_parameters: { alpha: 0.05 } } }), "DF α0.05");
});

test("label suggestions skip case-insensitive collisions and preserve the server limit", () => {
  assert.equal(uniqueResultLabel("DS", [{ resultId: "1", label: "ds" }, { resultId: "2", label: "DS (2)" }], "3"), "DS (3)");
  const long = "A".repeat(120);
  assert.equal(uniqueResultLabel(long, [{ resultId: "1", label: long }], "2"), `${"A".repeat(116)} (2)`);
});

test("moving a backbone preserves selection and leaves the original list intact", () => {
  const saved = [{ resultId: "1", selected: true }, { resultId: "2", selected: false }, { resultId: "3", selected: true }];
  assert.deepEqual(moveSavedBackbone(saved, "3", 0), [saved[2], saved[0], saved[1]]);
  assert.deepEqual(moveSavedBackbone(saved, "1", 2), [saved[1], saved[2], saved[0]]);
  assert.deepEqual(moveSavedBackbone(saved, "2", 2), [saved[0], saved[2], saved[1]]);
  assert.deepEqual(saved.map((item) => item.resultId), ["1", "2", "3"]);
  assert.equal(moveSavedBackbone(saved, "1", -1), saved);
  assert.equal(moveSavedBackbone(saved, "3", 3), saved);
  assert.equal(moveSavedBackbone(saved, "3", 2), saved);
  assert.equal(moveSavedBackbone(saved, "missing", 1), saved);
});
