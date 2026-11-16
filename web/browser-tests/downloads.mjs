import { readFile } from "node:fs/promises";
import { expect } from "@playwright/test";

export async function expectZip(page, button, filename) {
  const pendingDownload = page.waitForEvent("download");
  await button.click();
  const download = await pendingDownload;
  expect(download.suggestedFilename()).toBe(filename);
  expect(await download.failure()).toBeNull();
  const zip = await readFile(await download.path());
  expect(zip.subarray(0, 4)).toEqual(Buffer.from([0x50, 0x4b, 0x03, 0x04]));
  expect(zip.includes(Buffer.from("manifest.json"))).toBe(true);
}
