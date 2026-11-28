import { expect, test } from "@playwright/test";
import { downloadedSettings, expectZip } from "./downloads.mjs";

async function openMethods(page) {
  await page.getByRole("button", { name: "Choose method", exact: true }).click();
  return page.getByRole("dialog", { name: "Choose a scoring method" });
}

function chooseFilter(page, name) {
  return page.getByRole("radiogroup", { name: "Filter" }).getByRole("radio", { name }).check();
}

async function selectAndInspect(page, method, filter) {
  await method.click();
  await chooseFilter(page, filter);
  await expect(page.getByLabel("Retention preview").getByText("Backbone edges", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Inspect & export" }).click();
  return page.getByRole("dialog", { name: "Inspect & export" });
}

async function compareAndSweep(page) {
  const save = page.getByRole("button", { name: "Save this backbone" });
  const fraction = page.getByRole("spinbutton", { name: /Retained fraction/ });
  for (const value of ["25", "75"]) {
    await fraction.fill(value);
    await fraction.press("Tab");
    await save.click();
    await expect(page.getByRole("button", { name: "Backbone saved" })).toBeVisible();
  }
  // The comparison runs as soon as the page opens with two saved backbones.
  await page.getByRole("button", { name: "Compare 2 saved backbones" }).click();
  await expect(page.getByRole("button", { name: "Overlap & agreement" })).toBeVisible();
  await expectZip(page, page.getByRole("main"), "netbone-comparison-experiment.zip");
  await page.getByRole("button", { name: "Back to analysis" }).click();

  await page.getByRole("button", { name: /^Sweep:/ }).click();
  // A sweep starts by varying the retained fraction, so only the range needs typing.
  await expect(page.getByRole("combobox", { name: "Setting", exact: true })).toHaveValue("filter.fraction");
  await page.getByRole("spinbutton", { name: /^From/ }).fill("25");
  await page.getByRole("spinbutton", { name: /^To/ }).fill("75");
  await page.getByRole("spinbutton", { name: /^Step/ }).fill("50");
  await expect(page.getByText("2 values: 25%, 75%")).toBeVisible();
  const response = page.waitForResponse((result) => new URL(result.url()).pathname === "/api/sweep");
  await page.getByRole("button", { name: "Run sweep" }).click();
  const sweep = await (await response).json();
  expect(sweep.runs.map((run) => run.status)).toEqual(["ok", "ok"]);
  await expect(page.getByRole("heading", { name: "Sweep results" })).toBeVisible();
  await expectZip(page, page.getByRole("main"), "netbone-sweep-experiment.zip");
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
  await expectZip(page, inspect, "netbone-node-degree-experiment.zip");
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
  expect(JSON.stringify(await downloadedSettings(page, inspect))).toContain('"temporal_aggregation"');
  await expectZip(page, inspect, "netbone-disparity-experiment.zip");
  await inspect.getByRole("button", { name: "Close" }).click();
  await chooseFilter(page, "Keep a fraction");
  await compareAndSweep(page);
});

test("Noise Corrected applies the published cutoff and allows it to be changed", async ({ page }) => {
  await page.goto("/");
  await page.getByText("Try an example", { exact: true }).click();
  await page.getByRole("button", { name: /^Weighted relationships / }).click();
  const methods = await openMethods(page);
  await methods.getByRole("button", { name: /^Noise Corrected / }).click();
  await expect(page.getByRole("radio", { name: "Score cutoff" })).toBeChecked();
  await expect(page.locator(".filter-description")).toContainText("Recommended");
  const cutoff = page.getByRole("spinbutton", { name: "Standard deviation cutoff" });
  await expect(cutoff).toHaveValue("1.64");
  await cutoff.fill("2.32");
  await page.getByRole("button", { name: "Inspect & export" }).click();
  const inspect = page.getByRole("dialog", { name: "Inspect & export" });
  const configuration = await downloadedSettings(page, inspect);
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

test("Node Strength offers in, out and total strength on directed networks", async ({ page }) => {
  await page.goto("/");
  await page.getByText("Try an example", { exact: true }).click();
  await page.getByRole("button", { name: /^Weighted relationships / }).click();
  const methods = await openMethods(page);
  await methods.getByRole("button", { name: /^Node Strength / }).click();
  await chooseFilter(page, "Keep a fraction");
  const status = page.locator("span.visually-hidden[role=status][aria-atomic=true]");
  const openScoringSettings = async () => {
    const details = page.locator("details.analysis-score-settings");
    if (await details.count() && !(await details.evaluate((element) => element.open))) await details.locator("summary").click();
  };
  await expect(status).toHaveText(/node scores are ready/);
  await openScoringSettings();
  await expect(page.getByRole("radio", { name: /^in-strength/ })).toBeDisabled();
  await expect(page.getByText("Undirected graphs have a single strength per node.")).toBeVisible();

  await page.getByRole("button", { name: "Network settings" }).click();
  const settings = page.getByRole("dialog", { name: "Network settings" });
  await settings.getByRole("button", { name: "Change mapping" }).click();
  await settings.getByRole("checkbox", { name: /^Directed network/ }).check();
  await settings.getByRole("button", { name: "Done" }).click();
  await expect(page.getByLabel("Network summary")).toContainText("Directed");
  // Changing direction clears the scores, so the status must stop announcing them.
  await expect(page.getByRole("button", { name: "Compute scores" })).toBeVisible();
  await expect(status).toHaveText("");
  await openScoringSettings();
  const inStrength = page.getByRole("radio", { name: /^in-strength/ });
  await expect(inStrength).toBeEnabled();
  await inStrength.check();
  await page.getByRole("button", { name: "Compute scores" }).click();
  // New scores keep the filter that was chosen before.
  await expect(page.getByRole("radio", { name: "Keep a fraction" })).toBeChecked();
  await expect(page.getByLabel("Retention preview").getByText("Backbone edges", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Inspect & export" }).click();
  const inspect = page.getByRole("dialog", { name: "Inspect & export" });
  const configuration = await downloadedSettings(page, inspect);
  expect(configuration.method.parameters).toMatchObject({ direction: "in" });
});

test("outgoing-only and incoming-only aggregation unlock on directed networks", async ({ page }) => {
  await page.goto("/");
  await page.getByText("Try an example", { exact: true }).click();
  await page.getByRole("button", { name: /^Weighted relationships / }).click();
  const methods = await openMethods(page);
  await methods.getByRole("button", { name: /^Disparity / }).click();
  await chooseFilter(page, "Significance");
  const status = page.locator("span.visually-hidden[role=status][aria-atomic=true]");
  const openScoringSettings = async () => {
    const details = page.locator("details.analysis-score-settings");
    if (await details.count() && !(await details.evaluate((element) => element.open))) await details.locator("summary").click();
    const advanced = page.locator("details.advanced-method-settings");
    if (await advanced.count() && !(await advanced.evaluate((element) => element.open))) await advanced.locator("summary").click();
  };
  await expect(status).toHaveText(/edge scores are ready/);
  await openScoringSettings();
  await expect(page.getByRole("radio", { name: /^outgoing only/ })).toBeDisabled();
  await expect(page.getByRole("radio", { name: /^incoming only/ })).toBeDisabled();
  await expect(page.getByRole("radio", { name: /^minimum/ })).toBeEnabled();

  await page.getByRole("button", { name: "Network settings" }).click();
  const settings = page.getByRole("dialog", { name: "Network settings" });
  await settings.getByRole("button", { name: "Change mapping" }).click();
  await settings.getByRole("checkbox", { name: /^Directed network/ }).check();
  await settings.getByRole("button", { name: "Done" }).click();
  await expect(page.getByLabel("Network summary")).toContainText("Directed");
  await expect(page.getByRole("button", { name: "Compute scores" })).toBeVisible();
  await expect(status).toHaveText("");
  await openScoringSettings();
  const incoming = page.getByRole("radio", { name: /^incoming only/ });
  await expect(incoming).toBeEnabled();
  await incoming.check();
  await page.getByRole("button", { name: "Compute scores" }).click();
  await expect(page.getByRole("radio", { name: "Significance" })).toBeChecked();
  await expect(page.getByLabel("Retention preview").getByText("Backbone edges", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Inspect & export" }).click();
  const inspect = page.getByRole("dialog", { name: "Inspect & export" });
  const configuration = await downloadedSettings(page, inspect);
  expect(configuration.method.parameters).toMatchObject({ pvalue_aggregation: "in" });
});

test("seeded random ties show a seed box and Holm correction is offered", async ({ page }) => {
  await page.goto("/");
  await page.getByText("Try an example", { exact: true }).click();
  await page.getByRole("button", { name: /^Weighted relationships / }).click();
  const methods = await openMethods(page);
  await methods.getByRole("button", { name: /^Edge Weight / }).click();
  await chooseFilter(page, "Keep a fraction");
  const openAdvancedFilters = async () => {
    const advanced = page.locator("details.advanced-options").filter({ hasText: "Advanced filter options" });
    if (!(await advanced.evaluate((element) => element.open))) await advanced.locator("summary").click();
  };
  await openAdvancedFilters();
  const seed = page.getByRole("spinbutton", { name: /^Random seed/ });
  await expect(seed).toHaveCount(0);
  await page.getByRole("combobox", { name: "Tie policy" }).selectOption("random_seeded");
  await expect(seed).toBeVisible();
  await seed.fill("7");
  await expect(page.getByLabel("Retention preview").getByText("Backbone edges", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Inspect & export" }).click();
  const inspect = page.getByRole("dialog", { name: "Inspect & export" });
  const configuration = await downloadedSettings(page, inspect);
  expect(configuration.filter.parameters).toMatchObject({ tie_policy: "random_seeded", random_seed: 7 });
  await inspect.getByRole("button", { name: "Close" }).click();

  await page.getByRole("combobox", { name: "Tie policy" }).selectOption("exact_stable");
  await expect(seed).toHaveCount(0);
  await page.getByRole("button", { name: "Change method" }).click();
  await page.getByRole("dialog", { name: "Choose a scoring method" }).getByRole("button", { name: /^Disparity / }).click();
  await chooseFilter(page, "Significance");
  await openAdvancedFilters();
  const correction = page.getByRole("combobox", { name: "Correction" });
  await correction.selectOption("holm");
  await expect(correction).toHaveValue("holm");
});
