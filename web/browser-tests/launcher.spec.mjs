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
