// Regenerate the web app screenshots shown in the browser guides (docs/browser).
//
// Run from the repository root with Netbone installed and the demo built:
//
//   npm run build:demo --prefix web
//   python examples/build_sample_demo.py docs/demo/data
//   npm run screenshots --prefix web
//
// The script starts the local web app, serves the static demo, follows the
// steps the guides describe, and writes PNG files to docs/assets/screens.
// NETBONE_PYTHON picks the Python interpreter, NETBONE_SCREENSHOT_PORT the
// app's port (8793 by default), and NETBONE_BROWSER_EXECUTABLE or
// NETBONE_BROWSER_CHANNEL the browser.

import { chromium } from "@playwright/test";
import { execFileSync, spawn } from "node:child_process";
import { createReadStream, existsSync, mkdirSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize, sep } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../..", import.meta.url));
const output = join(root, "docs", "assets", "screens");
const demoDir = join(root, "docs", "demo");
const python = process.env.NETBONE_PYTHON || "python";
const appPort = Number(process.env.NETBONE_SCREENSHOT_PORT || 8793);
const appUrl = `http://127.0.0.1:${appPort}/`;
const viewport = { width: 1040, height: 760 };

const collaborations = "source,target,weight\nalice,bob,4\nbob,carol,1\ncarol,dana,2\nalice,carol,3\n";

if (!existsSync(join(demoDir, "index.html")) || !existsSync(join(demoDir, "data", "snapshot.json"))) {
  console.error("Build the demo first: npm run build:demo --prefix web && python examples/build_sample_demo.py docs/demo/data");
  process.exit(1);
}
mkdirSync(output, { recursive: true });

const app = spawn(python, ["-m", "netbone.webapp", "--host", "127.0.0.1", "--port", String(appPort)], {
  cwd: root,
  stdio: ["ignore", "ignore", "inherit"],
});
const demo = await serveDirectory(demoDir);
let browser;

try {
  browser = await chromium.launch({
    ...(process.env.NETBONE_BROWSER_EXECUTABLE ? { executablePath: process.env.NETBONE_BROWSER_EXECUTABLE } : {}),
    ...(process.env.NETBONE_BROWSER_CHANNEL ? { channel: process.env.NETBONE_BROWSER_CHANNEL } : {}),
  });
  await waitForServer(appUrl);
  const context = await browser.newContext({ viewport, deviceScaleFactor: 2, colorScheme: "light", reducedMotion: "reduce" });
  const page = await context.newPage();

  // Run the local web app: the start screen.
  await page.goto(appUrl);
  await page.getByRole("button", { name: "Open a network" }).waitFor();
  await capture(page, page, "app-start");

  // Extract a backbone in the browser: method picker, preview, inspection.
  await page.getByText("Try an example", { exact: true }).click();
  await page.getByRole("button", { name: /^Weighted relationships / }).click();
  await useMapping(page);
  const methods = await openMethods(page);
  await methods.getByText(/Checking network compatibility/).waitFor({ state: "hidden" });
  await captureDialog(page, methods, "app-choose-method");
  await methods.getByRole("button", { name: /^Edge Weight / }).click();
  await keepFraction(page, "0.5");
  await capturePage(page, "app-backbone-preview");
  await page.getByRole("button", { name: "Inspect & export" }).click();
  const inspect = page.getByRole("dialog", { name: "Inspect & export" });
  await inspect.getByRole("table", { name: "Method statistics" }).waitFor();
  await captureDialog(page, inspect, "app-inspect");

  // Import a network in the browser: the settings review for an edge list.
  await page.goto(appUrl);
  await page.locator('input[type="file"]').setInputFiles({
    name: "collaborations.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(collaborations),
  });
  const settings = page.getByRole("dialog", { name: /Review network settings/ });
  await settings.getByText(/Checking mapping/).waitFor({ state: "hidden" });
  await settings.getByRole("radio", { name: /^Strength/ }).check();
  await captureDialog(page, settings, "app-network-settings");

  // Compare and sweep: two saved Karate Club backbones, then a fraction sweep.
  const karate = execFileSync(python, [
    "-c",
    "import networkx as nx; print('\\n'.join(nx.generate_graphml(nx.karate_club_graph())))",
  ]);
  await page.goto(appUrl);
  await page.locator('input[type="file"]').setInputFiles({
    name: "karate-club.graphml",
    mimeType: "application/xml",
    buffer: karate,
  });
  await useMapping(page);
  await openMethods(page);
  for (const method of ["Edge Weight", "Edge Betweenness"]) {
    if (method !== "Edge Weight") await page.getByRole("button", { name: "Change method" }).click();
    await page
      .getByRole("dialog", { name: "Choose a scoring method" })
      .getByRole("button", { name: new RegExp(`^${method} `) })
      .click();
    await keepFraction(page, "0.25");
    await page.getByRole("button", { name: "Save this backbone" }).click();
    await page.getByRole("button", { name: "Backbone saved" }).waitFor();
  }
  await page.getByRole("button", { name: "Compare", exact: true }).click();
  await page.getByRole("button", { name: "Compare 2 backbones" }).click();
  await page.getByRole("button", { name: "Overlap & agreement" }).click();
  await page.getByRole("combobox", { name: "Metric", exact: true }).selectOption("edge_overlap");
  await capturePage(page, "app-compare");

  await page.getByRole("navigation", { name: "Workspace" }).getByRole("button", { name: "Analysis" }).click();
  await page.getByRole("button", { name: /^Sweep:/ }).click();
  await page.getByRole("combobox", { name: "Setting 1" }).selectOption("filter.fraction");
  await page.getByRole("textbox", { name: /Values for retained fraction/ }).fill("10%, 30%, 50%, 70%, 90%");
  await page.getByRole("button", { name: "Review runs" }).click();
  await page.getByRole("button", { name: "Run 5 configurations" }).click();
  await page.getByRole("heading", { name: "Sweep results" }).waitFor();
  await page.getByRole("combobox", { name: "Measured property" }).selectOption({ label: "Connected Component Count" });
  const figures = page.locator("section").filter({ has: page.getByRole("heading", { name: "Sweep figures" }) });
  await capture(page, figures.last(), "app-sweep");

  // Try the web demo: the precomputed Karate Club workbench.
  await page.goto(demo.url);
  await page.getByRole("heading", { name: "Zachary’s Karate Club" }).waitFor();
  await page.getByLabel("Retention preview").getByText("Backbone edges", { exact: true }).waitFor();
  await capturePage(page, "demo-workbench");

  await context.close();
} finally {
  await browser?.close();
  demo.server.close();
  app.kill();
}

async function captureDialog(page, dialog, name) {
  // Clear the dimmed backdrop so the rounded corners show the page, not a dark frame.
  const style = await page.addStyleTag({
    content: "dialog::backdrop, .dialog-backdrop { background: transparent !important; }",
  });
  await capture(page, dialog, name);
  await style.evaluate((element) => element.remove());
}

async function capturePage(page, name) {
  // Grow the window to the whole page so the sticky action bar sits below the
  // content, then keep the header and the main area.
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.setViewportSize({ width: viewport.width, height });
  const bottom = await page.evaluate(() => {
    window.scrollTo(0, 0);
    const main = document.querySelector("main").getBoundingClientRect();
    // Stop above the citation footer that follows the main area.
    const below = [...document.querySelectorAll("body *")]
      .map((element) => element.getBoundingClientRect())
      .filter((box) => box.height > 0 && box.top >= main.bottom)
      .map((box) => box.top);
    return Math.ceil(Math.min(main.bottom + 24, ...below));
  });
  await capture(page, page, name, { clip: { x: 0, y: 0, width: viewport.width, height: bottom } });
  await page.setViewportSize(viewport);
}

async function capture(page, target, name, options = {}) {
  await page.mouse.move(0, 0);
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
  });
  await page.waitForTimeout(400);
  const path = join(output, `${name}.png`);
  await target.screenshot({ path, animations: "disabled", ...options });
  console.log(`${path.slice(root.length)} (${Math.round(statSync(path).size / 1024)} kB)`);
}

async function useMapping(page) {
  const review = page.getByRole("dialog", { name: /Review network settings/ });
  const choose = page.getByRole("button", { name: "Choose method", exact: true });
  await review.or(choose).first().waitFor();
  if (!(await review.isVisible())) return;
  await review.getByText(/Checking mapping/).waitFor({ state: "hidden" });
  const strength = review.getByRole("radio", { name: /^Strength/ });
  if (await strength.count()) await strength.check();
  await review.getByRole("button", { name: /^Use this (mapping|network)/ }).click();
  await review.waitFor({ state: "hidden" });
}

async function openMethods(page) {
  // The app opens the method picker by itself once a new network is accepted.
  const methods = page.getByRole("dialog", { name: "Choose a scoring method" });
  await page.waitForTimeout(500);
  if (!(await methods.isVisible())) await page.getByRole("button", { name: "Choose method", exact: true }).click();
  return methods;
}

async function keepFraction(page, value) {
  const filters = page.getByRole("dialog", { name: "Choose a filter" });
  await filters.getByRole("button", { name: /^Keep a fraction/ }).click();
  const fraction = page.getByRole("spinbutton", { name: /Retained fraction/ });
  await fraction.fill(value);
  await fraction.press("Tab");
  await page.waitForTimeout(300);
  await page.locator(".analysis-dock-status").filter({ hasText: /Preview ready|saved|counts ready/ }).waitFor();
}

async function waitForServer(url) {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      if ((await fetch(url)).ok) return;
    } catch {
      // The server is still starting.
    }
    await new Promise((done) => setTimeout(done, 200));
  }
  throw new Error(`The web app did not start at ${url}`);
}

function serveDirectory(directory) {
  const types = {
    ".css": "text/css",
    ".html": "text/html",
    ".js": "text/javascript",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".zip": "application/zip",
  };
  const server = createServer((request, response) => {
    const path = decodeURIComponent(new URL(request.url, "http://localhost").pathname);
    let file = normalize(join(directory, path));
    if (file !== directory && !file.startsWith(directory + sep)) {
      response.writeHead(403).end();
      return;
    }
    if (existsSync(file) && statSync(file).isDirectory()) file = join(file, "index.html");
    if (!existsSync(file)) {
      response.writeHead(404).end();
      return;
    }
    response.writeHead(200, { "Content-Type": types[extname(file)] || "application/octet-stream" });
    createReadStream(file).pipe(response);
  });
  return new Promise((done) => {
    server.listen(0, "127.0.0.1", () => done({ server, url: `http://127.0.0.1:${server.address().port}/` }));
  });
}
