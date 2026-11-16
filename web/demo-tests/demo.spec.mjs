import { expect, test } from "@playwright/test";

test("the real workbench compares, changes and exports precomputed Karate Club runs", async ({ page }) => {
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
  await expect(page.getByRole("button", { name: "Network settings" })).toHaveCount(0);
  await expect(page.getByLabel("Retained fraction")).toHaveValue("0.25");
  const networkPreview = page.getByRole("region", { name: "Network preview" });
  await expect(networkPreview.getByText("Backbone edges", { exact: true })).toBeVisible();
  await expect(networkPreview).toContainText("20");

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
  await expect(networkPreview).toContainText("39");
  await page.getByRole("button", { name: "Inspect & export" }).click();
  const inspection = page.getByRole("dialog", { name: "Inspect & export" });
  await expect(inspection.getByRole("table", { name: "Method statistics" })).toBeVisible();
  await inspection.getByRole("combobox", { name: "Graph", exact: true }).selectOption("backbone");
  const graph = page.waitForEvent("download");
  await inspection.getByRole("button", { name: "Download GraphML" }).click();
  expect((await graph).suggestedFilename()).toMatch(/\.graphml$/);

  expect(apiRequests).toEqual([]);
  expect(errors).toEqual([]);
});
