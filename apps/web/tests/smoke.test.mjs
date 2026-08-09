import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), "utf8");

test("frontend skeleton contains the required Milestone 1 foundations", async () => {
  const [app, router, client, boundary] = await Promise.all([
    read("src/App.tsx"),
    read("src/router/index.tsx"),
    read("src/api/client.ts"),
    read("src/components/ErrorBoundary.tsx"),
  ]);

  assert.match(app, /RouterProvider/);
  assert.match(app, /QueryClientProvider/);
  assert.match(router, /createBrowserRouter/);
  assert.match(client, /\/api\/v1\/health/);
  assert.match(client, /\/api\/v1\/version/);
  assert.match(boundary, /componentDidCatch/);
});
