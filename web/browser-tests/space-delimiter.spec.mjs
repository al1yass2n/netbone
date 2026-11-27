import { expect, test } from "@playwright/test";

test("a space-separated edge list is detected and loaded", async ({ page }) => {
  await page.goto("/");
  await page.locator('input[type="file"]').setInputFiles({
    name: "network.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("source   target weight\nalice bob 4\n\"New York\"\tbob 1\nbob carol 2\n"),
  });
  const mapping = page.getByRole("dialog", { name: /Review network settings/ });
  await expect(mapping.getByText("3 rows")).toBeVisible();
  await mapping.getByRole("radio", { name: /^Strength/ }).check();
  await mapping.getByRole("button", { name: "Change mapping" }).click();
  await expect(mapping.getByRole("combobox", { name: "Delimiter" })).toHaveValue(" ");
  await expect(mapping.getByRole("combobox", { name: "Source" })).toHaveValue("source");
  await expect(mapping.getByRole("combobox", { name: "Target" })).toHaveValue("target");
  await mapping.getByRole("button", { name: "Use this mapping" }).click();
  await expect(mapping).toBeHidden();
  const summary = page.getByLabel("Network summary");
  await expect(summary).toContainText(/Nodes\s*4/);
  await expect(summary).toContainText(/Edges\s*3/);
});
