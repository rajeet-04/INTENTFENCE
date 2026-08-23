import { afterEach } from "bun:test";
import { cleanup } from "@testing-library/react";

globalThis.fetch = (async () =>
  new Response(JSON.stringify({ detail: "offline in unit tests" }), {
    status: 503,
    headers: { "Content-Type": "application/json" },
  })) as typeof fetch;

afterEach(() => cleanup());
