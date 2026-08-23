import { expect, test } from "bun:test";

import type { AgentStreamEvent } from "./agent-api";
import { streamAgentChat } from "./agent-api";

test("POST stream reader delivers fragmented events and preserves the abort signal", async () => {
  const encoder = new TextEncoder();
  const chunks = [
    'id: 1\nevent: model_status\ndata: {"event":"model_status","sequence":1,"status":"think',
    'ing"}\n\nid: 2\nevent: assistant_delta\ndata: {"event":"assistant_delta","sequence":2,"delta":"Hello"}\n\n',
  ];
  let captured: { url: string; init?: RequestInit } | null = null;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (input, init) => {
    captured = { url: String(input), init };
    return new Response(
      new ReadableStream({
        start(controller) {
          for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
          controller.close();
        },
      }),
      { status: 200, headers: { "Content-Type": "text/event-stream" } },
    );
  };
  const controller = new AbortController();
  const events: AgentStreamEvent[] = [];

  try {
    await streamAgentChat(
      {
        history: [],
        message: "Hello",
        objective: "Answer safely",
        web_research_enabled: false,
        revise_intent: false,
      },
      { onEvent: (event) => events.push(event) },
      controller.signal,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }

  expect(events.map((event) => event.event)).toEqual([
    "model_status",
    "assistant_delta",
  ]);
  expect(captured?.url).toBe("http://localhost:8000/agent/chat/stream");
  expect(captured?.init?.method).toBe("POST");
  expect(captured?.init?.signal).toBe(controller.signal);
  expect(JSON.parse(String(captured?.init?.body))).toEqual({
    history: [],
    message: "Hello",
    objective: "Answer safely",
    web_research_enabled: false,
    revise_intent: false,
  });
});
