import { expect, test } from "@playwright/test";

test("the app copies its paper citation as BibTeX", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.goto("/");
  await page.getByRole("button", { name: "Copy BibTeX" }).click();
  await expect(page.getByText("BibTeX copied", { exact: true })).toBeVisible();
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  expect(copied).toMatch(/^@article\{yassin2023netbone,/);
  expect(copied).toContain("Yassin, Ali and Haidar, Abbas and Cherifi, Hocine and Seba, Hamida and Togni, Olivier");
  expect(copied).toContain("pages = {17000}");
  expect(copied).toContain("doi = {10.1038/s41598-023-42076-3}");
});

test("the app offers selectable BibTeX when the clipboard is unavailable", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "clipboard", { value: undefined });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Copy BibTeX" }).click();
  const citation = page.getByRole("textbox", { name: "BibTeX citation" });
  await expect(citation).toHaveValue(/doi = \{10\.1038\/s41598-023-42076-3\}/);
  await expect(citation).toBeFocused();
  const selection = await citation.evaluate((element) => element.value.slice(element.selectionStart, element.selectionEnd));
  expect(selection).toMatch(/^@article\{yassin2023netbone,/);
});
