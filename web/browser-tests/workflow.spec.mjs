import { expect, test } from "@playwright/test";
import { expectZip } from "./downloads.mjs";

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
  const filters = page.getByRole("dialog", { name: "Choose a filter" });
  await expect(filters.getByRole("button", { name: /^Score cutoff Recommended/ })).toBeFocused();
  await filters.getByRole("button", { name: /^Keep a fraction/ }).click();
  await page.getByRole("button", { name: "Change filter" }).click();
  await expect(filters.getByRole("button", { name: /^Keep a fraction/ })).toBeFocused();
  await page.keyboard.press("Escape");

  await page.getByRole("button", { name: "Inspect & export" }).click();
  const inspect = page.getByRole("dialog", { name: "Inspect & export" });
  const table = inspect.getByRole("table", { name: "Method statistics" });
  await expect(table.getByRole("columnheader", { name: "Source", exact: true })).toBeVisible();
  await expect(table.getByRole("columnheader", { name: "Target", exact: true })).toBeVisible();
  await expect(table.getByRole("columnheader", { name: "Weight", exact: true })).toBeVisible();
  const inspectTab = inspect.getByRole("tab", { name: "Inspect" });
  const exportTab = inspect.getByRole("tab", { name: "Export" });
  await expect(inspectTab).toHaveAttribute("aria-selected", "true");
  await expect(inspect.getByRole("button", { name: "Download ZIP" })).toBeHidden();
  await inspect.getByText("View run settings", { exact: true }).click();
  const settingsDownload = page.waitForEvent("download");
  await inspect.getByRole("button", { name: "Download settings (JSON)" }).click();
  expect((await settingsDownload).suggestedFilename()).toBe("netbone-pipeline.json");
  await inspectTab.press("ArrowRight");
  await expect(exportTab).toBeFocused();
  await expect(table).toBeHidden();
  await expectZip(page, inspect.getByRole("button", { name: "Download ZIP" }), "netbone-edge-weight-experiment.zip");
  await page.keyboard.press("Escape");
  await expect(inspect).toBeHidden();

  const fraction = page.getByRole("spinbutton", { name: /Retained fraction/ });
  const save = page.getByRole("button", { name: "Save this backbone" });
  await page.mouse.move(0, 0);
  await expect(save).toHaveCSS("background-color", "rgb(19, 107, 86)");
  const saveColors = await save.evaluate((button) => {
    const style = getComputedStyle(button);
    return { background: style.backgroundColor, foreground: style.color };
  });
  for (const value of ["0.25", "0.75"]) {
    await fraction.fill(value);
    await fraction.press("Tab");
    await save.click();
    await expect(page.getByRole("button", { name: "Backbone saved" })).toBeVisible();
  }
  await page.getByRole("button", { name: "Compare", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Compare backbones" })).toBeVisible();
  const exportExperiment = page.getByRole("button", { name: "Export full experiment" });
  const compare = page.getByRole("button", { name: "Compare 2 backbones" });
  await expect(compare).toHaveCSS("background-color", saveColors.background);
  await expect(compare).toHaveCSS("color", saveColors.foreground);
  await compare.click();
  await expect(exportExperiment).toHaveCSS("background-color", saveColors.background);
  await expectZip(page, exportExperiment, "netbone-comparison-experiment.zip");

  await page.getByRole("navigation", { name: "Workspace" }).getByRole("button", { name: "Analysis" }).click();
  await page.getByRole("button", { name: /^Sweep:/ }).click();
  await page.getByRole("combobox", { name: "Setting 1" }).selectOption("filter.fraction");
  await page.getByRole("textbox", { name: /Values for retained fraction/ }).fill("25%, 75%");
  const review = page.getByRole("button", { name: "Review runs" });
  await expect(review).toHaveCSS("background-color", saveColors.background);
  await review.click();
  const run = page.getByRole("button", { name: "Run 2 configurations" });
  await expect(run).toHaveCSS("background-color", saveColors.background);
  await run.click();
  await expect(page.getByRole("heading", { name: "Sweep results" })).toBeVisible();
  await expect(exportExperiment).toHaveCSS("background-color", saveColors.background);
  await expectZip(page, exportExperiment, "netbone-sweep-experiment.zip");
});
