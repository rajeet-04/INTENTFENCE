import { describe, expect, test } from "bun:test";

import * as api from "./api";

const comparison = {
  scenario_id: "hotel-indirect-injection-v1",
  disabled: {
    mode: "DISABLED",
    tool_sequence: ["read_file", "http_request", "write_file"],
    decisions: ["ALLOW", "ALLOW", "ALLOW"],
    secret_read_executed: true,
    exfiltration_executed: true,
    legitimate_workflow_completed: true,
  },
  enabled: {
    mode: "ENABLED",
    tool_sequence: ["read_file", "http_request", "write_file"],
    decisions: ["BLOCK", "BLOCK", "ALLOW"],
    secret_read_executed: false,
    exfiltration_executed: false,
    legitimate_workflow_completed: true,
  },
};

describe("fetchHotelAttackDemo", () => {
  test("requests the controlled comparison from the configured API", async () => {
    const fetchHotelAttackDemo = (
      api as typeof api & {
        fetchHotelAttackDemo?: (
          request: typeof fetch,
          baseUrl: string,
        ) => Promise<typeof comparison>;
      }
    ).fetchHotelAttackDemo;

    expect(fetchHotelAttackDemo).toBeFunction();

    const calls: Array<[RequestInfo | URL, RequestInit | undefined]> = [];
    const request = (async (input: RequestInfo | URL, init?: RequestInit) => {
      calls.push([input, init]);
      return Response.json(comparison);
    }) as typeof fetch;

    await expect(fetchHotelAttackDemo!(request, "http://localhost:8000")).resolves.toEqual(
      comparison,
    );
    expect(calls).toEqual([
      ["http://localhost:8000/demo/hotel-attack", { method: "POST" }],
    ]);
  });

  test("reports a failed demo response without trying to render it", async () => {
    const request = (async () => new Response("unavailable", { status: 503 })) as typeof fetch;

    await expect(api.fetchHotelAttackDemo(request, "http://localhost:8000")).rejects.toThrow(
      "Demo API returned 503",
    );
  });
});
