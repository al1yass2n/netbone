import { expect, test } from "@playwright/test";

test("the citation footer links to the published paper in both themes", async ({ page }) => {
  await page.goto("/");
  const footer = page.getByRole("contentinfo");
  const citation = footer.getByRole("link", { name: "Cite Netbone" });
  await expect(citation).toBeInViewport();
  await expect(citation).toHaveAttribute("href", "https://doi.org/10.1038/s41598-023-42076-3");
  await page.getByRole("button", { name: "Dark theme" }).click();
  await expect(citation).toBeInViewport();
  await expect(footer).toContainText("Yassin et al.");
});

test("the theme follows the system until someone picks the other one", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  const shell = page.locator(".app-shell");
  await expect(shell).toHaveAttribute("data-theme", "dark");
  // The page behind the app matches, so no light edge shows when scrolling past the end.
  await expect(page.locator("html")).toHaveCSS("background-color", "rgb(19, 21, 24)");
  await page.emulateMedia({ colorScheme: "light" });
  await expect(shell).toHaveAttribute("data-theme", "light");
  await expect(page.locator("html")).toHaveCSS("background-color", "rgb(244, 245, 247)");

  // A pick that differs from the system is remembered and wins over the system.
  await page.getByRole("button", { name: "Switch to dark theme" }).click();
  await expect(shell).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(shell).toHaveAttribute("data-theme", "dark");

  // Picking the system's own theme again goes back to following the system.
  await page.getByRole("button", { name: "Switch to light theme" }).click();
  await expect(shell).toHaveAttribute("data-theme", "light");
  expect(await page.evaluate(() => localStorage.getItem("netbone-theme"))).toBeNull();
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(shell).toHaveAttribute("data-theme", "dark");
});

test("the launcher keeps the full word visible and highlights it under reduced motion", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const graphic = page.getByRole("img", { name: /^A weighted network spells Netbone/ });
  await expect(graphic).toBeVisible();

  const lettering = await graphic.evaluate((element) => {
    const frame = element.getBoundingClientRect();
    const letters = [...element.querySelectorAll('.launcher-backbone-links [data-kind="letter"]')];
    const bounds = letters.map((letter) => letter.getBoundingClientRect());
    return {
      inset: Math.min(
        Math.min(...bounds.map(({ left }) => left)) - frame.left,
        frame.right - Math.max(...bounds.map(({ right }) => right)),
      ),
      width: Math.max(...bounds.map(({ right }) => right)) - Math.min(...bounds.map(({ left }) => left)),
      frameWidth: frame.width,
    };
  });
  expect(lettering.inset).toBeGreaterThan(12);
  expect(lettering.width).toBeGreaterThan(lettering.frameWidth * 0.45);
  const wordEdge = graphic.locator('.launcher-backbone-links [data-kind="letter"]').first();
  const routeEdge = graphic.locator('.launcher-backbone-links [data-kind="context"]').first();
  await expect(wordEdge).toHaveCSS("animation-name", "none");
  await expect(wordEdge).toHaveCSS("opacity", "1");
  expect(await wordEdge.evaluate((edge) => getComputedStyle(edge).stroke))
    .not.toBe(await routeEdge.evaluate((edge) => getComputedStyle(edge).stroke));
  await expect(page.getByRole("button", { name: "Open a network" })).toBeInViewport();
  await expect(page.getByText("Try an example", { exact: true })).toBeInViewport();
});
