import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";

const published = process.env.NETBONE_DEMO_URL;
const port = 8798;
const local = `http://127.0.0.1:${port}/`;
const channel = process.env.NETBONE_BROWSER_CHANNEL;

export default defineConfig({
  testDir: "./demo-tests",
  use: {
    baseURL: published || local,
    actionTimeout: 8_000,
    ...(channel ? { channel } : {}),
  },
  projects: [
    { name: "desktop", use: { viewport: { width: 1280, height: 900 } } },
    { name: "narrow", use: { viewport: { width: 390, height: 844 }, hasTouch: true } },
  ],
  webServer: published ? undefined : {
    command: `"${process.env.NETBONE_DEMO_PYTHON || "python"}" -m http.server ${port} --bind 127.0.0.1 --directory site`,
    cwd: fileURLToPath(new URL("..", import.meta.url)),
    url: local,
    reuseExistingServer: false,
  },
});
