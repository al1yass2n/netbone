import { defineConfig } from "@playwright/test";

const port = Number(process.env.NETBONE_BROWSER_PORT || 8795);
const preview = `http://127.0.0.1:${port}`;
const channel = process.env.NETBONE_BROWSER_CHANNEL;

export default defineConfig({
  testDir: "./browser-tests",
  use: {
    baseURL: preview,
    actionTimeout: 8_000,
    ...(channel ? { channel } : {}),
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { viewport: { width: 1280, height: 900 } } },
    { name: "narrow", use: { viewport: { width: 390, height: 844 }, hasTouch: true } },
  ],
  webServer: {
    command: `${process.env.NETBONE_WEB_COMMAND || "python -m netbone.webapp"} --host 127.0.0.1 --port ${port}`,
    url: preview,
    reuseExistingServer: false,
  },
});
