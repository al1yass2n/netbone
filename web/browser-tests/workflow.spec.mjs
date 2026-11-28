import { expect, test } from "@playwright/test";
import { download, expectZip } from "./downloads.mjs";

test("extract, compare and sweep backbones and download their experiments", async ({ page }) => {
  test.setTimeout(60_000);
  await page.goto("/");
  await page.locator('input[type="file"]').setInputFiles({
    name: "collaborations.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("source,target,weight\nalice,bob,4\nbob,carol,1\ncarol,dana,2\nalice,carol,3\n"),
  });
  const mapping = page.getByRole("dialog", { name: /Review network settings/ });
  const useMapping = mapping.getByRole("button", { name: "Use this mapping" });
  await expect(useMapping).toBeDisabled();
  await mapping.getByRole("radio", { name: /^Strength/ }).check();
  await useMapping.click();
  await page.getByRole("dialog").getByRole("button", { name: /^Edge Weight / }).click();
  // Keyboard focus moves on to the filter, whose recommended choice starts selected.
  await expect(page.getByRole("heading", { name: "Filter", exact: true })).toBeFocused();
  const filters = page.getByRole("radiogroup", { name: "Filter" });
  await expect(filters.getByRole("radio", { name: "Score cutoff" })).toBeChecked();
  await expect(page.locator(".filter-description")).toContainText("Recommended");
  await filters.getByRole("radio", { name: "Keep a fraction" }).check();
  const fraction = page.getByRole("spinbutton", { name: "Retained fraction in percent" });
  await expect(fraction).toBeVisible();

  await page.getByRole("button", { name: "Inspect & export" }).click();
  const inspect = page.getByRole("dialog", { name: "Inspect & export" });
  const table = inspect.getByRole("table", { name: "Method statistics" });
  await expect(table.getByRole("columnheader", { name: "Source", exact: true })).toBeVisible();
  await expect(table.getByRole("columnheader", { name: "Target", exact: true })).toBeVisible();
  await expect(table.getByRole("columnheader", { name: "Weight", exact: true })).toBeVisible();
  // Run settings read in plain words, and one menu holds every file.
  await inspect.getByText("Run settings", { exact: true }).click();
  await expect(inspect.locator(".run-settings")).toContainText("Keep a fraction");
  const settings = await download(page, inspect, "Settings (JSON)");
  expect(settings.suggestedFilename()).toBe("netbone-pipeline.json");
  // Escape closes an open menu and leaves the dialog open.
  const menuButton = inspect.locator("details.download-menu summary");
  await menuButton.click();
  await expect(inspect.getByRole("button", { name: "Backbone (GraphML)" })).toBeVisible();
  // The list opens toward the side with room, so it stays on screen on phones too.
  const list = await inspect.getByRole("group", { name: "Download options" }).boundingBox();
  expect(list.x).toBeGreaterThanOrEqual(0);
  expect(list.x + list.width).toBeLessThanOrEqual(page.viewportSize().width);
  await page.keyboard.press("Escape");
  await expect(inspect.getByRole("button", { name: "Backbone (GraphML)" })).toBeHidden();
  await expect(menuButton).toBeFocused();
  await expect(inspect).toBeVisible();
  await expectZip(page, inspect, "netbone-edge-weight-experiment.zip");
  await page.keyboard.press("Escape");
  await expect(inspect).toBeHidden();

  const save = page.getByRole("button", { name: "Save this backbone" });
  await page.mouse.move(0, 0);
  await expect(save).toHaveCSS("background-color", "rgb(15, 118, 110)");
  const saveColors = await save.evaluate((button) => {
    const style = getComputedStyle(button);
    return { background: style.backgroundColor, foreground: style.color };
  });
  for (const value of ["25", "75"]) {
    await fraction.fill(value);
    await fraction.press("Tab");
    await save.click();
    await expect(page.getByRole("button", { name: "Backbone saved" })).toBeVisible();
  }
  // Two saved backbones are compared as soon as the page opens.
  await page.getByRole("button", { name: "Compare 2 saved backbones" }).click();
  await expect(page.getByRole("heading", { name: "Compare backbones" })).toBeFocused();
  await expect(page.getByRole("button", { name: "Overlap & agreement" })).toBeVisible();
  // A wide chart scrolls inside its panel instead of widening the page.
  await expect(page.getByRole("img", { name: /Edge retention/ })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(page.viewportSize().width);
  await expectZip(page, page.getByRole("main"), "netbone-comparison-experiment.zip");

  await page.getByRole("button", { name: "Back to analysis" }).click();
  await expect(page.getByRole("heading", { name: "collaborations", level: 1 })).toBeFocused();
  await page.getByRole("button", { name: /^Sweep:/ }).click();
  await expect(page.getByRole("heading", { name: "Test a range of settings" })).toBeFocused();
  await expect(page.getByRole("combobox", { name: "Setting", exact: true })).toHaveValue("filter.fraction");
  await page.getByRole("button", { name: "List", exact: true }).click();
  await page.getByRole("textbox", { name: /Values for retained fraction/ }).fill("25%, 75%");
  await expect(page.getByLabel("Sweep actions").getByText("2 runs", { exact: true })).toBeVisible();
  const run = page.getByRole("button", { name: "Run sweep" });
  await expect(run).toHaveCSS("background-color", saveColors.background);
  await expect(run).toHaveCSS("color", saveColors.foreground);
  await run.click();
  await expect(page.getByRole("heading", { name: "Sweep results" })).toBeVisible();
  await expectZip(page, page.getByRole("main"), "netbone-sweep-experiment.zip");
});
