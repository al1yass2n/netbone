import assert from "node:assert/strict";
import { readdirSync } from "node:fs";
import test from "node:test";
import { methodGoalDetails } from "../src/methodGoals.ts";

test("every documented method has a distinct goal and explains both retained item types", () => {
  const catalog = readdirSync(new URL("../../docs/methods/", import.meta.url))
    .filter((file) => file.endsWith(".md"))
    .map((file) => {
      const name = file.slice(0, -3);
      return { name, label: name.replaceAll("_", " "), target: name.startsWith("node_") ? "node" : "edge" };
    });
  assert.ok(catalog.length >= 19);
  const goals = new Set();
  for (const method of catalog) {
    const details = methodGoalDetails(method);
    assert.ok(details, method.name);
    assert.ok(details.edges && details.nodes, method.name);
    assert.ok(!goals.has(details.goal), details.goal);
    goals.add(details.goal);
    if (method.target === "node") assert.match(details.edges, /between retained nodes/);
    else assert.match(details.nodes, /remain as isolates/);
  }
});
