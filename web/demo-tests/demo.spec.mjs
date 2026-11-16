import { expect, test } from "@playwright/test";

test("the real workbench compares, changes and exports precomputed Karate Club runs", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  const apiRequests = [];
  const errors = [];
  page.on("request", (request) => {
    if (request.method() !== "GET" || new URL(request.url()).pathname.includes("/api/")) {
      apiRequests.push(request.url());
    }
  });
  page.on("pageerror", (error) => errors.push(error.message));

  await page.goto("./browser/sample-demo/");
  await page.getByRole("link", { name: "Open the web demo" }).click();
  await expect(page.getByRole("heading", { name: "Zachary’s Karate Club" })).toBeVisible();
  await page.getByRole("button", { name: "Copy BibTeX" }).click();
  await expect(page.getByText("BibTeX copied", { exact: true })).toBeVisible();
  const citation = await page.evaluate(() => navigator.clipboard.readText());
  expect(citation).toMatch(/^@article\{yassin2023netbone,/);
  expect(citation).toContain("doi = {10.1038/s41598-023-42076-3}");
  await expect(page.getByRole("button", { name: "Network settings" })).toHaveCount(0);
  await expect(page.getByLabel("Retained fraction")).toHaveValue("0.25");
  const retention = page.getByLabel("Retention preview");
  await expect(retention.getByText("Backbone edges", { exact: true })).toBeVisible();
  await expect(retention).toContainText("20");

  await page.getByRole("button", { name: "Compare", exact: true }).click();
  await page.getByRole("button", { name: "Compare 2 backbones" }).click();
  await page.getByRole("button", { name: "Overlap & agreement" }).click();
  await page.getByRole("combobox", { name: "Metric", exact: true }).selectOption("edge_overlap");
  await page.getByRole("button", { name: "Table", exact: true }).click();
  await expect(page.getByRole("table").getByRole("cell", { name: "6", exact: true })).toBeVisible();

  const comparisonZip = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export full experiment" }).click();
  expect((await comparisonZip).suggestedFilename()).toMatch(/\.zip$/);

  await page.getByRole("button", { name: "Back to analysis" }).click();
  await page.getByRole("button", { name: "Change method" }).click();
  await page.getByRole("dialog", { name: "Choose a scoring method" }).getByRole("button", { name: /^Edge Betweenness / }).click();
  await page.getByLabel("Retained fraction").selectOption("0.5");
  await expect(retention).toContainText("39");
  await page.getByRole("button", { name: "Inspect & export" }).click();
  const inspection = page.getByRole("dialog", { name: "Inspect & export" });
  await expect(inspection.getByRole("table", { name: "Method statistics" })).toBeVisible();
  const inspectTab = inspection.getByRole("tab", { name: "Inspect" });
  await expect(inspectTab).toHaveAttribute("aria-selected", "true");
  await inspection.getByText("View run settings", { exact: true }).click();
  const settings = page.waitForEvent("download");
  await inspection.getByRole("button", { name: "Download settings (JSON)" }).click();
  expect((await settings).suggestedFilename()).toBe("netbone-pipeline.json");
  await inspectTab.press("ArrowRight");
  await expect(inspection.getByRole("tab", { name: "Export" })).toBeFocused();
  await expect(inspection.getByRole("table", { name: "Method statistics" })).toBeHidden();
  await expect(inspection.getByRole("combobox", { name: "Graph", exact: true })).toHaveValue("backbone");
  const graph = page.waitForEvent("download");
  await inspection.getByRole("button", { name: "Download GraphML" }).click();
  expect((await graph).suggestedFilename()).toMatch(/\.graphml$/);
  const extractionZip = page.waitForEvent("download");
  await inspection.getByRole("button", { name: "Download ZIP" }).click();
  expect((await extractionZip).suggestedFilename()).toMatch(/\.zip$/);

  expect(apiRequests).toEqual([]);
  expect(errors).toEqual([]);
});
