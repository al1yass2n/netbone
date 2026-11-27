import assert from "node:assert/strict";
import test from "node:test";
import { methodCompatibilityReason } from "../src/utils.ts";

const method = (overrides = {}) => ({
  supports_directed: true,
  requires_weights: false,
  ...overrides,
});

test("positive-weight methods are blocked for zero or negative weights", () => {
  const disparity = method({ requires_weights: true, requires_positive_weights: true });
  for (const weightSign of ["nonnegative", "mixed"]) {
    assert.equal(
      methodCompatibilityReason(disparity, { directed: false, weighted: true, weightSign }),
      "Requires positive weights",
    );
  }
  assert.equal(
    methodCompatibilityReason(disparity, { directed: false, weighted: true, weightSign: "positive" }),
    "",
  );
});

test("non-negative methods allow zero weights but not negative ones", () => {
  const linkage = method({ requires_weights: true, requires_nonnegative_weights: true });
  assert.equal(methodCompatibilityReason(linkage, { directed: false, weighted: true, weightSign: "nonnegative" }), "");
  assert.equal(
    methodCompatibilityReason(linkage, { directed: false, weighted: true, weightSign: "mixed" }),
    "Requires non-negative weights",
  );
});

test("weight sign does not block unweighted runs of optional-weight methods", () => {
  const salience = method({ requires_positive_weights: true });
  assert.equal(methodCompatibilityReason(salience, { directed: false, weighted: false, weightSign: null }), "");
});
