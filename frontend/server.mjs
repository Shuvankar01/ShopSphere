/**
 * Production server for the TanStack Start SSR build.
 *
 * `vite build` (TanStack Start) emits two things:
 *   dist/client/...        -> hashed static assets (JS/CSS/fonts)
 *   dist/server/server.js  -> the SSR bundle
 *
 * The SSR bundle is a Web-standard `fetch` handler (its default export is
 * `{ fetch(request) }`), NOT a Node HTTP server — running it directly with
 * `node dist/server/server.js` just evaluates the module and exits.
 * `srvx` (already a transitive dependency of @tanstack/start-plugin-core)
 * provides the thin Node adapter that binds a port to that handler.
 *
 * Environment:
 *   PORT      port to listen on (default 3000)
 *   HOST      interface to bind     (default 0.0.0.0)
 */
import { fileURLToPath } from "node:url";

import { serve } from "srvx/node";
import { serveStatic } from "srvx/static";

import handler from "./dist/server/server.js";

const port = Number(process.env.PORT ?? 3000);
const hostname = process.env.HOST ?? "0.0.0.0";
const clientDir = fileURLToPath(new URL("./dist/client/", import.meta.url));

if (typeof handler?.fetch !== "function") {
  console.error(
    "dist/server/server.js does not export a fetch handler — run `npm run build` first.",
  );
  process.exit(1);
}

const server = serve({
  fetch: handler.fetch,
  port,
  hostname,
  middleware: [serveStatic({ dir: clientDir })],
});

await server.ready();
console.log(`ShopSphere frontend listening on http://${hostname}:${port}`);
