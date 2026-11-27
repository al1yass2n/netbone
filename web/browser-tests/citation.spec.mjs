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

test("a chosen method links to the paper that defines it", async ({ page }) => {
  await page.goto("/");
  await page.getByText("Try an example", { exact: true }).click();
  await page.getByRole("button", { name: /^Temporal interactions / }).click();
  await page.getByRole("button", { name: "Choose method", exact: true }).click();
  await page.getByRole("dialog", { name: "Choose a scoring method" }).getByRole("button", { name: /^Node Betweenness / }).click();
  const paper = page.getByRole("link", { name: "Paper for Node Betweenness (opens in a new tab)" });
  await expect(paper).toHaveAttribute("href", "https://doi.org/10.2307/3033543");
  await expect(paper).toHaveAttribute("target", "_blank");
  await expect(paper).toHaveAttribute("title", /^Freeman, L\. C\. \(1977\)/);
});

test("a temporal weighting links to the paper that defines it", async ({ page }) => {
  await page.goto("/");
  await page.getByText("Try an example", { exact: true }).click();
  await page.getByRole("button", { name: /^Temporal interactions / }).click();
  await expect(page.getByRole("button", { name: "Choose method", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Network settings" }).click();
  const change = page.getByRole("button", { name: "Change mapping" });
  if (await change.isVisible()) await change.click();
  const weighting = page.getByRole("combobox", { name: /^Weighting/ });
  await weighting.selectOption("asf");
  const paper = page.getByRole("link", { name: "Paper for ASF (opens in a new tab)" });
  await expect(paper).toHaveAttribute("href", "https://doi.org/10.1109/COMPENG69955.2026.11766128");
  await expect(paper).toHaveAttribute("title", /^Yassin, A\., Cherifi, H\., Seba, H\., & Togni, O\. \(2026\)/);
  await weighting.selectOption("baseline");
  await expect(page.getByRole("link", { name: /^Paper for / })).toHaveCount(0);
});
