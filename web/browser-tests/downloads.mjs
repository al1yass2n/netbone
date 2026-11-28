import { readFile } from "node:fs/promises";
import { expect } from "@playwright/test";

/** Opens the Download menu inside `scope`, picks one file and returns the finished download. */
export async function download(page, scope, item) {
  const menu = scope.locator("details.download-menu");
  await menu.locator("summary").click();
  const pending = page.waitForEvent("download");
  await menu.getByRole("button", { name: item, exact: true }).click();
  const file = await pending;
  expect(await file.failure()).toBeNull();
  return file;
}

/** Downloads the full experiment from the Download menu inside `scope` and checks the archive. */
export async function expectZip(page, scope, filename) {
  const file = await download(page, scope, "Full experiment (ZIP)");
  expect(file.suggestedFilename()).toBe(filename);
  const zip = await readFile(await file.path());
  expect(zip.subarray(0, 4)).toEqual(Buffer.from([0x50, 0x4b, 0x03, 0x04]));
  expect(zip.includes(Buffer.from("manifest.json"))).toBe(true);
}

/** The settings a backbone was made with, read back from its Settings (JSON) download. */
export async function downloadedSettings(page, scope) {
  const file = await download(page, scope, "Settings (JSON)");
  return JSON.parse(await readFile(await file.path(), "utf8"));
}
