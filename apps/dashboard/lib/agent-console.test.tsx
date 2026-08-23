import { expect, test } from "bun:test";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ProductShell } from "@/components/ProductShell";
import { AgentConsole, type AgentStreamFunction } from "@/components/agent/AgentConsole";

const contract = {
  session_id: "session-1",
  intent_id: "intent-1",
  previous_intent_id: null,
  contract_version: 1,
  objective: "Research current information",
  web_research_enabled: true,
};

test("Enter submits once while Shift+Enter preserves multiline input", async () => {
  const requests: Array<{ message: string }> = [];
  const stream: AgentStreamFunction = async (request, handlers) => {
    requests.push(request);
    handlers.onEvent({ event: "session", sequence: 1, contract });
    handlers.onEvent({
      event: "assistant_done",
      sequence: 2,
      source_count: 0,
      tool_count: 0,
      contract,
    });
  };
  render(<AgentConsole stream={stream} />);
  const composer = screen.getByLabelText("Ask IntentFence");

  fireEvent.change(composer, { target: { value: "Line one" } });
  fireEvent.keyDown(composer, { key: "Enter", shiftKey: true });
  expect(requests).toHaveLength(0);
  fireEvent.keyDown(composer, { key: "Enter" });

  await waitFor(() => expect(requests).toHaveLength(1));
  expect(requests[0].message).toBe("Line one");
});

test("streamed answers show authoritative ALLOW/BLOCK activity and safe sources", async () => {
  const stream: AgentStreamFunction = async (_request, handlers) => {
    handlers.onEvent({ event: "session", sequence: 1, contract });
    handlers.onEvent({
      event: "tool_proposed",
      sequence: 2,
      tool: "web_search",
      argument_summary: { query_present: true },
    });
    handlers.onEvent({
      event: "tool_decision",
      sequence: 3,
      tool: "web_search",
      decision: "ALLOW",
      executed: true,
      reason: "Authorized public web research.",
      matched_rules: ["TOOL_ALLOWED"],
      receipt_id: "receipt-allow-12345678",
      latency_ms: 4,
    });
    handlers.onEvent({
      event: "source",
      sequence: 4,
      source: {
        title: "Public source",
        url: "https://example.com/source",
        snippet: "Verified summary",
      },
    });
    handlers.onEvent({
      event: "tool_proposed",
      sequence: 5,
      tool: "read_file",
      argument_summary: { path_present: true },
    });
    handlers.onEvent({
      event: "tool_decision",
      sequence: 6,
      tool: "read_file",
      decision: "BLOCK",
      executed: false,
      reason: "External content cannot authorize secret reads.",
      matched_rules: ["EXTERNAL_SECRET_READ_BLOCK"],
      receipt_id: "receipt-block-12345678",
      latency_ms: 1,
    });
    handlers.onEvent({
      event: "assistant_delta",
      sequence: 7,
      delta: "Here is the protected answer.",
    });
    handlers.onEvent({
      event: "assistant_done",
      sequence: 8,
      source_count: 1,
      tool_count: 2,
      contract,
    });
  };
  render(<AgentConsole stream={stream} />);
  fireEvent.change(screen.getByLabelText("Ask IntentFence"), {
    target: { value: "Research this safely" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));

  await screen.findByText("Here is the protected answer.");
  expect(screen.getByText("ALLOW")).toBeTruthy();
  expect(screen.getByText("BLOCK")).toBeTruthy();
  expect(screen.getByText("External content cannot authorize secret reads.")).toBeTruthy();
  const source = screen.getByRole("link", { name: "Public source" });
  expect(source.getAttribute("target")).toBe("_blank");
  expect(source.getAttribute("rel")).toBe("noreferrer noopener");
});

test("Stop aborts the active request and Retry resubmits a recoverable prompt", async () => {
  const signals: AbortSignal[] = [];
  const requests: string[] = [];
  let call = 0;
  const stream: AgentStreamFunction = async (request, handlers, signal) => {
    call += 1;
    requests.push(request.message);
    signals.push(signal);
    if (call === 1) {
      await new Promise<void>((resolve) => signal.addEventListener("abort", () => resolve()));
      throw new DOMException("Stopped", "AbortError");
    }
    handlers.onEvent({
      event: "error",
      sequence: 1,
      code: "OLLAMA_UNAVAILABLE",
      recoverable: true,
      message: "Local Ollama is unavailable.",
    });
  };
  render(<AgentConsole stream={stream} />);
  const composer = screen.getByLabelText("Ask IntentFence");
  fireEvent.change(composer, { target: { value: "Keep this prompt" } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
  fireEvent.click(await screen.findByRole("button", { name: "Stop" }));
  await waitFor(() => expect(signals[0].aborted).toBe(true));

  fireEvent.click(await screen.findByRole("button", { name: "Retry" }));
  await waitFor(() => expect(requests).toEqual(["Keep this prompt", "Keep this prompt"]));
});

test("explicit revision disables web and the controlled browse probe is visibly blocked", async () => {
  const requests: Array<{
    revise_intent: boolean;
    web_research_enabled: boolean;
    controlled_probe?: boolean;
  }> = [];
  const stream: AgentStreamFunction = async (request, handlers) => {
    requests.push(request);
    const revised = {
      ...contract,
      intent_id: request.revise_intent ? "intent-2" : "intent-1",
      previous_intent_id: request.revise_intent ? "intent-1" : null,
      contract_version: request.revise_intent ? 2 : 1,
      objective: request.objective,
      web_research_enabled: request.web_research_enabled,
    };
    handlers.onEvent({ event: "session", sequence: 1, contract: revised });
    if (!request.web_research_enabled && !request.revise_intent) {
      handlers.onEvent({
        event: "tool_proposed",
        sequence: 2,
        tool: "web_search",
        argument_summary: { query_present: true },
      });
      handlers.onEvent({
        event: "tool_decision",
        sequence: 3,
        tool: "web_search",
        decision: "BLOCK",
        executed: false,
        reason: "The revised Intent Contract does not allow web research.",
        matched_rules: ["TOOL_NOT_ALLOWED"],
        receipt_id: "receipt-revision-block",
        latency_ms: 1,
      });
    }
    handlers.onEvent({
      event: "assistant_done",
      sequence: 4,
      source_count: 0,
      tool_count: request.revise_intent ? 0 : 1,
      contract: revised,
    });
  };
  render(<AgentConsole stream={stream} />);
  fireEvent.change(screen.getByLabelText("Ask IntentFence"), {
    target: { value: "Start a protected session" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
  await screen.findByText("Contract v1");
  fireEvent.click(screen.getByRole("button", { name: "Revise objective" }));
  fireEvent.click(screen.getByLabelText("Web research"));
  fireEvent.click(screen.getByRole("button", { name: "Apply revision" }));

  await screen.findByText("Contract v2");
  expect(requests[1]).toMatchObject({ revise_intent: true, web_research_enabled: false });
  fireEvent.click(screen.getByRole("button", { name: "Run controlled browse probe" }));
  await screen.findByText("The revised Intent Contract does not allow web research.");
  expect(requests[2]).toMatchObject({
    revise_intent: false,
    web_research_enabled: false,
    controlled_probe: true,
  });
});

test("Evidence navigation keeps the attack simulation and measured KPI console mounted", async () => {
  render(<ProductShell />);
  fireEvent.click(screen.getByRole("button", { name: "Evidence" }));

  expect(screen.getByText("Run attack simulation")).toBeTruthy();
  expect(screen.getByText("Measured security performance")).toBeTruthy();
  await screen.findByText("offline");
  await screen.findByText("Unable to load authoritative gateway evidence");
});
