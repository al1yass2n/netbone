import { expect, test } from "@playwright/test";
import { expectZip } from "./downloads.mjs";

async function openMethods(page) {
  await page.getByRole("button", { name: "Choose method", exact: true }).click();
  return page.getByRole("dialog", { name: "Choose a scoring method" });
}

async function selectAndInspect(page, method, filter) {
  await method.click();
  await page.getByRole("dialog", { name: "Choose a filter" }).getByRole("button", { name: filter }).click();
  await expect(page.getByLabel("Retention preview").getByText("Backbone edges", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Inspect & export" }).click();
  return page.getByRole("dialog", { name: "Inspect & export" });
}

async function compareAndSweep(page) {
  const save = page.getByRole("button", { name: "Save this backbone" });
  const fraction = page.getByRole("spinbutton", { name: /Retained fraction/ });
  for (const value of ["0.25", "0.75"]) {
    await fraction.fill(value);
    await fraction.press("Tab");
    await save.click();
    await expect(page.getByRole("button", { name: "Backbone saved" })).toBeVisible();
  }
  await page.getByRole("button", { name: "Compare", exact: true }).click();
  await page.getByRole("button", { name: "Compare 2 backbones" }).click();
  const exportButton = page.getByRole("button", { name: "Export full experiment" });
  await expectZip(page, exportButton, "netbone-comparison-experiment.zip");
  await page.getByRole("button", { name: "Back to analysis" }).click();

  await page.getByRole("button", { name: /^Sweep:/ }).click();
  await page.getByRole("combobox", { name: "Setting 1" }).selectOption("filter.fraction");
  await page.getByRole("textbox", { name: /Values for retained fraction/ }).fill("25%, 75%");
  await page.getByRole("button", { name: "Review runs" }).click();
  const response = page.waitForResponse((result) =>
    new URL(result.url()).pathname === "/api/sweep" && result.request().postDataJSON().preview_only === false,
  );
  await page.getByRole("button", { name: "Run 2 configurations" }).click();
  const sweep = await (await response).json();
  expect(sweep.runs.map((run) => run.status)).toEqual(["ok", "ok"]);
  await expect(page.getByRole("heading", { name: "Sweep results" })).toBeVisible();
  await expectZip(page, exportButton, "netbone-sweep-experiment.zip");
}

test("an unweighted CSV blocks weight-only methods and extracts with Node Degree", async ({ page }) => {
  await page.goto("/");
  await page.locator('input[type="file"]').setInputFiles({
    name: "friendships.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("source,target\na,b\nb,c\nb,d\nc,d\n"),
  });
  const mapping = page.getByRole("dialog", { name: "Review network settings" });
  await expect(mapping.getByText("Unweighted", { exact: true })).toBeVisible();
  await mapping.getByRole("button", { name: "Use this mapping" }).click();

  const methods = page.getByRole("dialog", { name: "Choose a scoring method" });
  const weight = methods.getByRole("button", { name: /^Node Strength / });
  await expect(weight).toBeDisabled();
  await expect(weight).toContainText("Requires a weight column");
  await methods.getByText("Filters", { exact: true }).click();
  await methods.getByRole("checkbox", { name: "Compatible only" }).check();
  await expect(weight).toBeHidden();
  const inspect = await selectAndInspect(page, methods.getByRole("button", { name: /^Node Degree / }), /^Keep a fraction/);
  const table = inspect.getByRole("table", { name: "Method statistics" });
  await expect(table.getByRole("columnheader", { name: "Node", exact: true })).toBeVisible();
  await expect(table.getByRole("columnheader", { name: "Weight", exact: true })).toHaveCount(0);
  await inspect.getByRole("tab", { name: "Export" }).click();
  await expectZip(page, inspect.getByRole("button", { name: "Download ZIP" }), "netbone-node-degree-experiment.zip");
  await inspect.getByRole("button", { name: "Close" }).click();
  await compareAndSweep(page);
});

test("a directed temporal example aggregates events and enables Disparity", async ({ page }) => {
  await page.goto("/");
  await page.getByText("Try an example", { exact: true }).click();
  await page.getByRole("button", { name: /^Temporal interactions / }).click();
  await page.getByRole("button", { name: "Network settings" }).click();
  const settings = page.getByRole("dialog", { name: "Network settings" });
  await expect(settings.getByText("Temporal event list", { exact: true })).toBeVisible();
  await settings.getByRole("button", { name: "Change mapping" }).click();
  await settings.getByRole("checkbox", { name: /^Directed network/ }).check();
  await settings.getByRole("button", { name: "Done" }).click();
  const summary = page.getByLabel("Network summary");
  await expect(summary).toContainText("Directed");
  await expect(summary).toContainText("Temporal weights");

  const methods = await openMethods(page);
  const undirectedOnly = methods.getByRole("button", { name: /^Edge Betweenness / });
  await expect(undirectedOnly).toBeDisabled();
  await expect(undirectedOnly).toContainText("Not available for directed networks");
  const inspect = await selectAndInspect(page, methods.getByRole("button", { name: /^Disparity / }), /^Significance/);
  await expect(inspect.getByRole("columnheader", { name: "Weight", exact: true })).toBeVisible();
  await inspect.getByText("View run settings", { exact: true }).click();
  await expect(inspect.locator("pre")).toContainText('"temporal_aggregation"');
  await inspect.getByRole("tab", { name: "Export" }).click();
  await expectZip(page, inspect.getByRole("button", { name: "Download ZIP" }), "netbone-disparity-experiment.zip");
  await inspect.getByRole("button", { name: "Close" }).click();
  await page.getByRole("button", { name: "Change filter" }).click();
  await page.getByRole("dialog", { name: "Choose a filter" }).getByRole("button", { name: /^Keep a fraction/ }).click();
  await compareAndSweep(page);
});

test("Noise Corrected applies the published cutoff and allows it to be changed", async ({ page }) => {
  await page.goto("/");
  await page.getByText("Try an example", { exact: true }).click();
  await page.getByRole("button", { name: /^Weighted relationships / }).click();
  const methods = await openMethods(page);
  await methods.getByRole("button", { name: /^Noise Corrected / }).click();
  const filters = page.getByRole("dialog", { name: "Choose a filter" });
  await filters.getByRole("button", { name: /^Score cutoff Recommended/ }).click();
  const cutoff = page.getByRole("spinbutton", { name: "Standard deviation cutoff" });
  await expect(cutoff).toHaveValue("1.64");
  await cutoff.fill("2.32");
  await page.getByRole("button", { name: "Inspect & export" }).click();
  const inspect = page.getByRole("dialog", { name: "Inspect & export" });
  await inspect.getByText("View run settings", { exact: true }).click();
  const configuration = JSON.parse(await inspect.locator("pre").textContent());
  expect(configuration.filter.parameters).toMatchObject({ value: 2.32, operator: "greater" });
});

test("a CSV header with spaces after commas maps cleanly", async ({ page }) => {
  await page.goto("/");
  await page.locator('input[type="file"]').setInputFiles({
    name: "spaced.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("source, target, weight\na, b, 4\nb, c, 2\n"),
  });
  const mapping = page.getByRole("dialog", { name: "Review network settings" });
  await mapping.getByRole("radio", { name: /^Strength/ }).check();
  await expect(mapping.getByRole("button", { name: "Use this mapping" })).toBeEnabled();
});

test("negative weights disable methods that need positive weights", async ({ page }) => {
  await page.goto("/");
  await page.locator('input[type="file"]').setInputFiles({
    name: "signed.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("source,target,weight\na,b,-4\nb,c,2\nc,a,3\n"),
  });
  const mapping = page.getByRole("dialog", { name: "Review network settings" });
  await mapping.getByRole("radio", { name: /^Strength/ }).check();
  await mapping.getByRole("button", { name: "Use this mapping" }).click();
  const picker = page.getByRole("dialog", { name: "Choose a scoring method" });
  const card = (label) => picker.getByRole("button").filter({ has: page.getByText(label, { exact: true }) });
  await expect(card("Disparity")).toBeDisabled();
  await expect(card("Disparity")).toContainText("Requires positive weights");
  await expect(card("Primary Linkage")).toBeEnabled();
});
