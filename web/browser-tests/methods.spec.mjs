import { expect, test } from "@playwright/test";

const edges = [
  ["a", "b"], ["a", "c"], ["b", "c"], ["b", "d"], ["c", "d"], ["c", "e"],
  ["d", "e"], ["d", "f"], ["e", "f"], ["e", "g"], ["f", "g"], ["a", "g"],
];

for (const input of ["weighted", "unweighted", "temporal"]) {
  for (const directed of [false, true]) {
    test(`every method on ${directed ? "directed" : "undirected"} ${input} input`, async ({ page }) => {
      test.setTimeout(90_000);
      const schemaResponse = await page.request.get("/api/ui-schema");
      expect(schemaResponse.ok()).toBe(true);
      const { methods } = await schemaResponse.json();
      expect(methods.length).toBeGreaterThan(0);

      await page.goto("/");
      if (input === "temporal") {
        await page.getByText("Try an example", { exact: true }).click();
        await page.getByRole("button", { name: /^Temporal interactions / }).click();
        if (!directed) {
          await page.getByRole("button", { name: "Choose method", exact: true }).click();
          const picker = page.getByRole("dialog", { name: "Choose a scoring method" });
          const marginal = picker.getByRole("button", { name: /^Marginal Likelihood / });
          await expect(marginal).toBeDisabled();
          await expect(marginal).toContainText("Requires positive whole-number weights");
          await picker.getByRole("button", { name: "Close" }).click();
        }
        await page.getByRole("button", { name: "Network settings" }).click();
        const settings = page.getByRole("dialog", { name: "Network settings" });
        await settings.getByRole("combobox", { name: "Weighting" }).selectOption("baseline");
        if (directed) {
          await settings.getByRole("button", { name: "Change mapping" }).click();
          await settings.getByRole("checkbox", { name: /^Directed network/ }).check();
        }
        await settings.getByRole("button", { name: "Done" }).click();
      } else {
        const weighted = input === "weighted";
        const lines = [weighted ? "source,target,weight" : "source,target"];
        for (const [index, [source, target]] of edges.entries()) {
          lines.push(weighted ? `${source},${target},${index + 1}` : `${source},${target}`);
        }
        await page.locator('input[type="file"]').setInputFiles({
          name: `${input}.csv`,
          mimeType: "text/csv",
          buffer: Buffer.from(lines.join("\n")),
        });
        const mapping = page.getByRole("dialog", { name: "Review network settings" });
        if (directed) {
          await mapping.getByRole("button", { name: "Change mapping" }).click();
          await mapping.getByRole("checkbox", { name: /^Directed network/ }).check();
        }
        if (weighted) await mapping.getByRole("radio", { name: /^Strength/ }).check();
        await mapping.getByRole("button", { name: "Use this mapping" }).click();
      }
      if (input === "temporal") await page.getByRole("button", { name: "Choose method", exact: true }).click();
      const picker = page.getByRole("dialog", { name: "Choose a scoring method" });
      const filters = page.getByRole("dialog", { name: "Choose a filter" });

      for (const method of methods) {
        await test.step(method.label, async () => {
          const card = picker.getByRole("button").filter({
            has: page.getByText(method.label, { exact: true }),
          });
          const reason = directed && !method.supports_directed
            ? "Not available for directed networks"
            : input === "unweighted" && method.requires_weights ? "Requires a weight column" : "";
          if (reason) {
            await expect(card).toBeDisabled();
            await expect(card).toContainText(reason);
            return;
          }
          await expect(card).toBeEnabled();
          const scoring = page.waitForResponse(
            (response) => new URL(response.url()).pathname === "/api/score",
            { timeout: 25_000 },
          );
          await card.click();
          const scored = await scoring;
          const score = await scored.json();
          expect(scored.ok(), score.message).toBe(true);
          expect(score.pipeline.method.name).toBe(method.name);
          await filters.getByRole("button", { name: /Recommended/ }).click();
          await page.getByRole("button", { name: "Inspect & export" }).click();
          const inspect = page.getByRole("dialog", { name: "Inspect & export" });
          await expect(inspect.getByRole("table", { name: "Method statistics" }).getByRole("row").nth(1)).toBeVisible();
          await inspect.getByRole("button", { name: "Close" }).click();
          await page.getByRole("button", { name: "Change method" }).click();
        });
      }
    });
  }
}
