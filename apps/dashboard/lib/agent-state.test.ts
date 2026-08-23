import { expect, test } from "bun:test";

import {
  agentReducer,
  initialAgentConversationState,
} from "./agent-state";

test("submission creates real user and pending assistant messages", () => {
  const state = agentReducer(initialAgentConversationState, {
    type: "submit",
    userId: "user-1",
    assistantId: "assistant-1",
    content: "Find current agent security news",
  });

  expect(state.streaming).toBe(true);
  expect(state.messages.map(({ role, content, status }) => ({ role, content, status }))).toEqual([
    { role: "user", content: "Find current agent security news", status: "complete" },
    { role: "assistant", content: "", status: "streaming" },
  ]);
});

test("stream events accumulate answer, activity, sources, and contract", () => {
  let state = agentReducer(initialAgentConversationState, {
    type: "submit",
    userId: "user-1",
    assistantId: "assistant-1",
    content: "Research IntentFence",
  });
  state = agentReducer(state, {
    type: "event",
    event: {
      event: "session",
      sequence: 1,
      contract: {
        session_id: "session-1",
        intent_id: "intent-1",
        previous_intent_id: null,
        contract_version: 1,
        objective: "Research IntentFence",
        web_research_enabled: true,
      },
    },
  });
  state = agentReducer(state, {
    type: "event",
    event: {
      event: "tool_proposed",
      sequence: 2,
      tool: "web_search",
      argument_summary: { query_present: true, query_length: 11 },
    },
  });
  state = agentReducer(state, {
    type: "event",
    event: {
      event: "tool_decision",
      sequence: 3,
      tool: "web_search",
      decision: "ALLOW",
      executed: true,
      reason: "Authorized public web research.",
      matched_rules: ["TOOL_ALLOWED"],
      receipt_id: "receipt-12345678",
      latency_ms: 3,
    },
  });
  const source = {
    title: "IntentFence",
    url: "https://example.com/intentfence",
    snippet: "Public source",
  };
  state = agentReducer(state, {
    type: "event",
    event: { event: "source", sequence: 4, source },
  });
  state = agentReducer(state, {
    type: "event",
    event: { event: "source", sequence: 5, source },
  });
  state = agentReducer(state, {
    type: "event",
    event: { event: "assistant_delta", sequence: 6, delta: "Verified answer" },
  });
  state = agentReducer(state, {
    type: "event",
    event: {
      event: "assistant_done",
      sequence: 7,
      source_count: 1,
      tool_count: 1,
      contract: state.contract!,
    },
  });

  const assistant = state.messages[1];
  expect(assistant.content).toBe("Verified answer");
  expect(assistant.status).toBe("complete");
  expect(assistant.sources).toEqual([source]);
  expect(assistant.activities).toHaveLength(1);
  expect(assistant.activities[0].decision).toBe("ALLOW");
  expect(state.contract?.session_id).toBe("session-1");
  expect(state.streaming).toBe(false);
});

test("recoverable stream errors retain the failed prompt for retry", () => {
  let state = agentReducer(initialAgentConversationState, {
    type: "submit",
    userId: "user-1",
    assistantId: "assistant-1",
    content: "Retry this prompt",
  });
  state = agentReducer(state, {
    type: "event",
    event: {
      event: "error",
      sequence: 2,
      code: "OLLAMA_UNAVAILABLE",
      recoverable: true,
      message: "Local Ollama is unavailable.",
    },
  });

  expect(state.streaming).toBe(false);
  expect(state.retryMessage).toBe("Retry this prompt");
  expect(state.draft).toBe("Retry this prompt");
  expect(state.messages[1].status).toBe("error");
});

test("assistant reset clears partial text but preserves receipts and sources", () => {
  let state = agentReducer(initialAgentConversationState, {
    type: "submit",
    userId: "user-1",
    assistantId: "assistant-1",
    content: "Research safely",
  });
  state = agentReducer(state, {
    type: "event",
    event: {
      event: "tool_proposed",
      sequence: 1,
      tool: "web_search",
      argument_summary: { query_present: true },
    },
  });
  state = agentReducer(state, {
    type: "event",
    event: {
      event: "tool_decision",
      sequence: 2,
      tool: "web_search",
      decision: "ALLOW",
      executed: true,
      reason: "Authorized.",
      matched_rules: [],
      receipt_id: "receipt-1",
      latency_ms: 1,
    },
  });
  state = agentReducer(state, {
    type: "event",
    event: {
      event: "source",
      sequence: 3,
      source: { title: "Source", url: "https://example.com", snippet: null },
    },
  });
  state = agentReducer(state, {
    type: "event",
    event: { event: "assistant_delta", sequence: 4, delta: "Partial local text" },
  });
  state = agentReducer(state, {
    type: "event",
    event: { event: "assistant_reset", sequence: 5, reason: "local_failure" },
  });
  state = agentReducer(state, {
    type: "event",
    event: {
      event: "model_status",
      sequence: 6,
      status: "answering",
      provider: "cloud",
      route_reason: "fallback",
    },
  });

  expect(state.messages[1].content).toBe("");
  expect(state.messages[1].activities).toHaveLength(1);
  expect(state.messages[1].sources).toHaveLength(1);
  expect(state.messages[1].provider).toBe("cloud");
  expect(state.messages[1].routeReason).toBe("fallback");
});

test("reset clears all browser-owned conversation state", () => {
  const submitted = agentReducer(initialAgentConversationState, {
    type: "submit",
    userId: "user-1",
    assistantId: "assistant-1",
    content: "Temporary prompt",
  });

  expect(agentReducer(submitted, { type: "reset" })).toEqual(
    initialAgentConversationState,
  );
});
