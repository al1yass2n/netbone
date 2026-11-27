import { expect, test } from "@playwright/test";

test("find a guide in the sidebar and follow its outline and page navigation", async ({ page }, testInfo) => {
  const narrow = testInfo.project.name === "narrow";
  await page.goto("./");

  const header = page.locator(".navbar");
  const article = page.getByRole("main");
  const navigation = page.getByRole("navigation", { name: "Documentation", exact: true });
  await expect(article.getByRole("heading", { name: "Netbone", level: 1, exact: true })).toBeVisible();
  await expect(header.getByRole("link", { name: "Try the demo" })).toBeVisible();
  await expect(header.locator('a[rel="prev"], a[rel="next"], .dropdown-menu')).toHaveCount(0);
  await expect(page.getByRole("navigation", { name: "Page navigation" })).toHaveCount(0);

  if (narrow) {
    await expect(navigation).toBeHidden();
    await page.getByRole("button", { name: "Browse docs" }).click();
  }
  await expect(navigation.getByRole("link", { name: "Home" })).toHaveAttribute("aria-current", "page");
  await navigation.getByText("Getting started", { exact: true }).click();
  await navigation.getByRole("link", { name: "Install Netbone", exact: true }).click();
  await expect(article.getByRole("heading", { name: "Install Netbone", exact: true })).toBeVisible();
  await expect.poll(() => page.evaluate(async () => {
    await document.fonts.ready;
    return [...document.fonts].filter((font) => font.status === "loaded").map((font) => font.family);
  })).toEqual(expect.arrayContaining(["Inter", "JetBrains Mono"]));

  if (narrow) {
    await page.getByRole("button", { name: "Browse docs" }).click();
  }
  await expect(navigation.getByRole("link", { name: "Install Netbone", exact: true })).toHaveAttribute("aria-current", "page");
  if (narrow) {
    await page.keyboard.press("Escape");
    await expect(navigation).toBeHidden();
    await page.getByRole("button", { name: "On this page" }).click();
  } else {
    const mainBox = await article.boundingBox();
    const sideBox = await navigation.boundingBox();
    const outlineBox = await page.getByRole("navigation", { name: "On this page" }).boundingBox();
    expect(sideBox.x + sideBox.width).toBeLessThan(mainBox.x);
    expect(outlineBox.x).toBeGreaterThan(mainBox.x + mainBox.width);
  }

  const outline = page.getByRole("navigation", { name: "On this page" });
  await outline.getByRole("link", { name: "Optional tools" }).click();
  await expect(page).toHaveURL(/#optional-tools$/);
  await expect(article.getByRole("heading", { name: "Optional tools" })).toBeInViewport();
  if (narrow) await expect(outline).toBeHidden();

  const pager = article.getByRole("navigation", { name: "Page navigation" });
  await expect(pager.getByRole("link", { name: "Previous Home" })).toHaveAttribute("rel", "prev");
  await pager.getByRole("link", { name: "Next Extract your first backbone" }).click();
  await expect(article.getByRole("heading", { name: "Extract your first backbone" })).toBeVisible();
  await page.keyboard.press("p");
  await expect(article.getByRole("heading", { name: "Install Netbone", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(testInfo.project.use.viewport.width);
});

test("search finds API reference pages from the header", async ({ page }) => {
  await page.goto("./");
  await page.getByRole("button", { name: "Search documentation" }).click();
  const search = page.getByRole("dialog", { name: "Search" });
  await search.getByRole("searchbox").pressSequentially("BackboneResult");
  const result = search.getByRole("link", { name: "BackboneResult", exact: true });
  await expect(result).toBeVisible();
  await page.route("**/assets/fonts/*.woff2", async (route) => {
    // Exercise fragment alignment when fonts finish loading after navigation.
    await new Promise((resolve) => setTimeout(resolve, 350));
    await route.continue();
  });
  await result.click();
  await expect(page).toHaveURL(/reference\/pipelines\/#netbone.BackboneResult$/);
  const heading = page.getByRole("main").getByRole("heading", { name: /^BackboneResult\b/, level: 2 });
  await expect(heading).toBeInViewport();
  await expect.poll(() => heading.evaluate((element) =>
    element.getBoundingClientRect().top >= document.querySelector(".navbar").getBoundingClientRect().bottom,
  )).toBe(true);
});

test("choose light or dark and reset the docs theme to the system setting", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("./");
  const theme = page.getByRole("combobox", { name: "Color theme" });
  const html = page.locator("html");
  await expect(theme).toHaveValue("system");
  await expect(html).toHaveAttribute("data-bs-theme", "dark");
  await expect(page.locator(".navbar")).toHaveCSS("background-color", "rgb(21, 25, 29)");

  await theme.selectOption("light");
  await expect(html).toHaveAttribute("data-bs-theme", "light");
  await expect(page.locator(".navbar")).toHaveCSS("background-color", "rgb(255, 255, 255)");
  await page.goto("./start/install/");
  await expect(theme).toHaveValue("light");
  await expect(html).toHaveAttribute("data-bs-theme", "light");

  await theme.selectOption("dark");
  await page.emulateMedia({ colorScheme: "light" });
  await page.reload();
  await expect(theme).toHaveValue("dark");
  await expect(html).toHaveAttribute("data-bs-theme", "dark");
  await expect(page.locator(".codehilite").first()).toHaveCSS("background-color", "rgb(28, 34, 39)");
  await expect(page.locator(".codehilite .s2").first()).toHaveCSS("color", "rgb(230, 219, 116)");

  await theme.selectOption("system");
  await expect(html).toHaveAttribute("data-bs-theme", "light");
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(html).toHaveAttribute("data-bs-theme", "dark");
});
