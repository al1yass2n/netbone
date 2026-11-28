import assert from "node:assert/strict";
import test from "node:test";
import { loadSource } from "./sourceModule.mjs";

const { backboneLabel, moveSavedBackbone, uniqueResultLabel } = await loadSource("/src/savedBackbones.ts");

test("saved labels name the method and the filter value in plain words", () => {
  const extraction = (filter, filter_parameters) => ({ extraction: { method: "doubly_stochastic", filter, filter_parameters } });
  assert.equal(backboneLabel(extraction("fraction", { fraction: 0.25 }), "Doubly Stochastic"), "Doubly Stochastic · 25%");
  assert.equal(backboneLabel(extraction("significance", { alpha: 0.05 }), "Doubly Stochastic"), "Doubly Stochastic · p < 0.05");
  assert.equal(backboneLabel(extraction("threshold", { value: 0.125 }), "Doubly Stochastic"), "Doubly Stochastic · cutoff 0.125");
  assert.equal(backboneLabel(extraction("default", {})), "Doubly stochastic");
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
