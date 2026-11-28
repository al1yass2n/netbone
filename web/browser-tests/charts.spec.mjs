import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { download } from "./downloads.mjs";

test("charts follow dark mode on screen and download with light colors", async ({ page }) => {
  test.setTimeout(60_000);
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  await page.locator('input[type="file"]').setInputFiles({
    name: "collaborations.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("source,target,weight\nalice,bob,4\nbob,carol,1\ncarol,dana,2\nalice,carol,3\n"),
  });
  const mapping = page.getByRole("dialog", { name: /Review network settings/ });
  await mapping.getByRole("radio", { name: /^Strength/ }).check();
  await mapping.getByRole("button", { name: "Use this mapping" }).click();
  await page.getByRole("dialog").getByRole("button", { name: /^Edge Weight / }).click();
  await page.getByRole("radiogroup", { name: "Filter" }).getByRole("radio", { name: "Keep a fraction" }).check();
  const fraction = page.getByRole("spinbutton", { name: "Retained fraction in percent" });
  const save = page.getByRole("button", { name: "Save this backbone" });
  for (const value of ["25", "75"]) {
    await fraction.fill(value);
    await fraction.press("Tab");
    await save.click();
    await expect(page.getByRole("button", { name: "Backbone saved" })).toBeVisible();
  }
  await page.getByRole("button", { name: "Compare 2 saved backbones" }).click();
  const chart = page.getByRole("img", { name: /Edge retention/ });
  await expect(chart).toBeVisible();

  // On screen the chart uses the dark panel and the dark theme's series colors.
  await expect(chart.locator(".figure-paper")).toHaveCSS("fill", "rgb(27, 30, 34)");
  await expect(chart.locator(".figure-series-0").first()).toHaveCSS("fill", "rgb(92, 194, 181)");
  const dot = page.locator(".saved-result.is-selected .saved-result__dot").first();
  await expect(dot).toHaveCSS("background-color", "rgb(92, 194, 181)");

  // The downloaded figure keeps its light colors, so it reads the same anywhere.
  const file = await download(page, page.getByRole("main"), "Figure (SVG)");
  const svg = await readFile(await file.path(), "utf8");
  expect(svg).toMatch(/class="figure-paper"[^>]*fill="#ffffff"/);
  expect(svg).toContain('fill="#0f766e"');
  expect(svg).not.toContain("var(");
});
