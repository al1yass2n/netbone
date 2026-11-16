import assert from "node:assert/strict";
import test from "node:test";
import { defaultContext, emptyDataDraft, guidedExamples } from "../src/examples.ts";
import { contextSummary } from "../src/utils.ts";

test("a new weighted input has no inferred strength or distance meaning", () => {
  const data = { ...emptyDataDraft, weight: "weight" };
  assert.equal(defaultContext.weightSemantics, "");
  assert.match(contextSummary(data, defaultContext, false), /Weight represents edge weight/);
  assert.doesNotMatch(contextSummary(data, defaultContext, false), /Larger weights mean/);
});

test("the context describes the selected meaning and omits it for unweighted inputs", () => {
  const data = { ...emptyDataDraft, weight: "weight" };
  const strength = { ...defaultContext, weightSemantics: "strength" };
  const distance = { ...defaultContext, weightSemantics: "distance" };
  assert.match(contextSummary(data, strength, false), /stronger or more frequent/);
  assert.match(contextSummary(data, distance, false), /greater distance or cost/);
  assert.doesNotMatch(contextSummary(emptyDataDraft, strength, false), /Weight represents/);
  for (const example of guidedExamples) {
    if (example.data.mode === "temporal" || example.data.weight) assert.ok(example.context.weightSemantics);
  }
});
