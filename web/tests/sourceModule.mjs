import { fileURLToPath } from "node:url";
import { createServer } from "vite";

/** Loads a source module through Vite, so its imports resolve as they do in the app. */
export async function loadSource(path) {
  const server = await createServer({
    root: fileURLToPath(new URL("../", import.meta.url)),
    server: { middlewareMode: true, ws: false, watch: null },
    appType: "custom",
    logLevel: "silent",
  });
  try {
    return await server.ssrLoadModule(path);
  } finally {
    await server.close();
  }
}
