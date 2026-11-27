import assert from "node:assert/strict";
import test from "node:test";
import { detectDelimiter, parseHeaders } from "../src/utils.ts";

test("a header separated by spaces is read with the space delimiter", () => {
  const text = "source  target weight\nalice bob 4\n";
  assert.equal(detectDelimiter("network.txt", text), " ");
  assert.deepEqual(parseHeaders(text, " "), ["source", "target", "weight"]);
});

test("the space delimiter treats tabs and runs of spaces as one separator", () => {
  assert.deepEqual(parseHeaders('source \t "target node"   weight\n', " "), ["source", "target node", "weight"]);
});

test("comma, tab and semicolon headers keep their delimiter", () => {
  assert.equal(detectDelimiter("edges.csv", "source,target,weight\n"), ",");
  assert.equal(detectDelimiter("edges.txt", "source\ttarget\tweight\n"), "\t");
  assert.equal(detectDelimiter("edges.csv", "source;target;weight\n"), ";");
  assert.equal(detectDelimiter("edges.csv", "first name,last name\n"), ",");
  assert.equal(detectDelimiter("edges.tsv", "source target\n"), "\t");
});
