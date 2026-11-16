import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

test("a histogram bin can contain scores on both sides of a strict cutoff", async () => {
  const server = await createServer({
    root: fileURLToPath(new URL("../", import.meta.url)),
    server: { middlewareMode: true, ws: false, watch: null },
    appType: "custom",
  });
  try {
    const { ScoreDistribution } = await server.ssrLoadModule("/src/components/ScoreDistribution.tsx");
    const markup = renderToStaticMarkup(createElement(ScoreDistribution, {
      method: { label: "Edge weight", primary_statistic: "weight", preferred_direction: "higher" },
      statistics: [0, 4, 4.1, 4.2, 4.3, 12, null].map((weight) => ({ weight })),
      boundary: 4.2,
      operator: "greater",
    }));
    assert.match(markup, /class="distribution__passed" style="height:25%"><\/span><span class="distribution__excluded" style="height:75%"/);
    assert.match(markup, /class="distribution__boundary" style="left:35%"/);
    assert.match(markup, /6 of 6 values/);
  } finally {
    await server.close();
  }
});
