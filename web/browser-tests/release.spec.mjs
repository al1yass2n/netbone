import { expect, test } from "@playwright/test";

async function uploadCsv(page, name, data) {
  await page.locator('input[type="file"]').setInputFiles({
    name,
    mimeType: "text/csv",
    buffer: Buffer.from(data),
  });
}

async function tabTo(page, target) {
  for (let index = 0; index < 30; index += 1) {
    if (await target.evaluate((element) => element === document.activeElement)) return;
    await page.keyboard.press("Tab");
  }
  await expect(target).toBeFocused();
}

test("keyboard users can confirm mapping and leave a dialog with focus restored", async ({ page }) => {
  await page.goto("/");
  await uploadCsv(page, "keyboard.csv", "source,target,weight\na,b,4\nb,c,2\n");
  const mapping = page.getByRole("dialog", { name: "Review network settings" });
  const strength = mapping.getByRole("radio", { name: /^Strength/ });
  await tabTo(page, strength);
  await page.keyboard.press("Space");
  await expect(strength).toBeChecked();
  const confirm = mapping.getByRole("button", { name: "Use this mapping" });
  await expect(confirm).toBeEnabled();
  await tabTo(page, confirm);
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog").getByRole("searchbox")).toBeVisible();
  await page.keyboard.press("Escape");
  const openMethods = page.getByRole("button", { name: "Choose method" });
  await tabTo(page, openMethods);
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog").getByRole("searchbox")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(openMethods).toBeFocused();
});

test("invalid input identifies the bad row and can be replaced", async ({ page }) => {
  await page.goto("/");
  await uploadCsv(page, "invalid.csv", "source,target,weight\na,b,broken\n");
  const mapping = page.getByRole("dialog", { name: "Review network settings" });
  await expect(mapping.getByText(/row 2.*weight.*broken.*not numeric/i)).toBeVisible();
  const confirm = mapping.getByRole("button", { name: "Use this mapping" });
  await expect(confirm).toBeDisabled();
  const chooser = page.waitForEvent("filechooser");
  await mapping.getByRole("button", { name: "Replace file" }).click();
  await (await chooser).setFiles({
    name: "corrected.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("source,target\na,b\nb,c\n"),
  });
  await expect(mapping.getByText("corrected.csv", { exact: false })).toBeVisible();
  await expect(confirm).toBeEnabled();
});

test("large networks keep counts and downloads available without a graph preview", async ({ page }, testInfo) => {
  const nodes = 1_500;
  const rows = ["source,target,weight"];
  for (let source = 0; source < nodes; source += 1) {
    for (let step = 1; step <= 4; step += 1) {
      rows.push(`${source},${(source + step) % nodes},${1 + (source + step) % 10}`);
    }
  }

  await page.goto("/");
  await uploadCsv(page, "large-network.csv", rows.join("\n"));
  const mapping = page.getByRole("dialog", { name: "Review network settings" });
  await mapping.getByRole("radio", { name: /^Strength/ }).check();
  await mapping.getByRole("button", { name: "Use this mapping" }).click();
  const scoringStarted = performance.now();
  await page.getByRole("dialog").getByRole("button", { name: /^Edge Weight / }).click();
  await page.getByRole("dialog", { name: "Choose a filter" }).getByRole("button", { name: /^Keep a fraction/ }).click();
  const preview = page.getByRole("region", { name: "Network preview" });
  await expect(preview.getByText("Preview unavailable for large networks")).toBeVisible();
  await expect(preview.getByText("Backbone edges", { exact: true })).toBeVisible();
  testInfo.annotations.push({
    type: "large-network preview",
    description: `${Math.round(performance.now() - scoringStarted)} ms from method selection to counts`,
  });
  await page.getByRole("button", { name: "Inspect & export" }).click();
  const inspect = page.getByRole("dialog", { name: "Inspect & export" });
  await expect(inspect.getByRole("table", { name: "Method statistics" })).toBeVisible();
  if (testInfo.project.name === "narrow") {
    const statistics = inspect.getByRole("region", { name: "Scrollable statistics" });
    await tabTo(page, statistics);
    await page.keyboard.press("ArrowRight");
    await expect.poll(() => statistics.evaluate((element) => element.scrollLeft)).toBeGreaterThan(0);
  }
  await inspect.getByRole("tab", { name: "Export" }).click();
  await expect(inspect.getByRole("combobox", { name: "Graph", exact: true })).toHaveValue("backbone");
  const pendingDownload = page.waitForEvent("download");
  await inspect.getByRole("button", { name: "Download GraphML" }).click();
  const download = await pendingDownload;
  expect(download.suggestedFilename()).toBe("netbone-edge-weight-backbone.graphml");
  expect(await download.failure()).toBeNull();
});

test("edge betweenness shows progress and opens the filter when scores are ready", async ({ page }, testInfo) => {
  test.setTimeout(60_000);
  const nodes = 700;
  const rows = ["source,target,weight"];
  for (let source = 0; source < nodes; source += 1) {
    for (const step of [1, 2, 7, 31]) {
      rows.push(`${source},${(source + step) % nodes},${1 + (source + step) % 10}`);
    }
  }
  await page.goto("/");
  await uploadCsv(page, "shortest-paths.csv", rows.join("\n"));
  const mapping = page.getByRole("dialog", { name: "Review network settings" });
  await mapping.getByRole("radio", { name: /^Strength/ }).check();
  await mapping.getByRole("button", { name: "Use this mapping" }).click();

  let releaseScore;
  const scoreGate = new Promise((resolve) => { releaseScore = resolve; });
  let computeMs;
  await page.route("**/api/score", async (route) => {
    const start = performance.now();
    const response = await route.fetch({ timeout: 45_000 });
    computeMs = Math.round(performance.now() - start);
    await scoreGate;
    await route.fulfill({ response });
  });
  try {
    await page.getByRole("dialog").getByRole("button", { name: /^Edge Betweenness / }).click();
    const actions = page.getByLabel("Analysis actions");
    await expect(actions.getByText(/Computing Edge Betweenness.* scores/)).toBeVisible();
    await expect(page.getByRole("status").filter({ hasText: /Computing Edge Betweenness.* scores/ })).toHaveCount(1);
    await expect(actions.getByRole("button", { name: /^Sweep:/ })).toBeDisabled();
  } finally {
    releaseScore();
  }
  const filter = page.getByRole("dialog", { name: "Choose a filter" });
  await expect(filter).toBeVisible({ timeout: 45_000 });
  await expect(filter).toMatchAriaSnapshot(`
    - dialog "Choose a filter":
      - heading "Choose a filter" [level=2]
      - button "Close"
      - button /Keep a fraction.*Recommended/
  `);
  await filter.getByRole("button", { name: /^Keep a fraction/ }).click();
  await expect(page.getByRole("region", { name: "Network preview" }).getByText("Backbone edges", { exact: true })).toBeVisible();
  testInfo.annotations.push({ type: "edge betweenness", description: `${computeMs} ms for the scoring request` });
});
