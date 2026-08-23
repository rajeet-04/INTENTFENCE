import { AgentStreamParseError, parseSseFrames } from "./agent-stream";
import { getApiBaseUrl } from "./api";

export type AgentContractSummary = {
  session_id: string;
  intent_id: string;
  previous_intent_id: string | null;
  contract_version: number;
  objective: string;
  web_research_enabled: boolean;
};

export type CitationSource = {
  title: string;
  url: string;
  snippet: string | null;
};

type EventBase = { sequence: number };

export type ReasoningMode = "auto" | "local" | "cloud";

export type AgentStreamEvent =
  | (EventBase & { event: "session"; contract: AgentContractSummary })
  | (EventBase & {
      event: "model_status";
      status: "thinking" | "searching" | "reading" | "answering";
      provider: "local" | "cloud";
      route_reason: "primary" | "fallback" | "escalation" | "explicit";
    })
  | (EventBase & {
      event: "tool_proposed";
      tool: string;
      argument_summary: Record<string, string | number | boolean>;
    })
  | (EventBase & {
      event: "tool_decision";
      tool: string;
      decision: "ALLOW" | "BLOCK" | "REQUIRE_APPROVAL";
      executed: boolean;
      reason: string;
      matched_rules: string[];
      receipt_id: string;
      latency_ms: number;
    })
  | (EventBase & { event: "source"; source: CitationSource })
  | (EventBase & { event: "assistant_delta"; delta: string })
  | (EventBase & {
      event: "assistant_reset";
      reason: "local_failure" | "intelligent_escalation";
    })
  | (EventBase & {
      event: "assistant_done";
      source_count: number;
      tool_count: number;
      contract: AgentContractSummary;
    })
  | (EventBase & {
      event: "error";
      code: string;
      recoverable: boolean;
      message: string;
    });

export type AgentChatRequest = {
  session_id?: string;
  history: Array<{ role: "user" | "assistant"; content: string }>;
  message: string;
  objective: string;
  web_research_enabled: boolean;
  revise_intent: boolean;
  reasoning_mode: ReasoningMode;
  controlled_probe?: boolean;
};

export class AgentApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null = null,
  ) {
    super(message);
    this.name = "AgentApiError";
  }
}

export async function streamAgentChat(
  request: AgentChatRequest,
  handlers: { onEvent: (event: AgentStreamEvent) => void },
  signal: AbortSignal,
): Promise<void> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/agent/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });
  if (!response.ok) {
    let message = `Agent request failed with status ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") message = payload.detail;
    } catch {
      // Keep the safe status-only fallback.
    }
    throw new AgentApiError(message, response.status);
  }
  if (!response.body) {
    throw new AgentApiError("Agent response did not include a stream.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let remainder = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      const parsed = parseSseFrames(remainder + decoder.decode(value, { stream: true }));
      remainder = parsed.remainder;
      for (const frame of parsed.frames) handlers.onEvent(frame.data);
    }
    remainder += decoder.decode();
    const final = parseSseFrames(remainder);
    for (const frame of final.frames) handlers.onEvent(frame.data);
    if (final.remainder.trim()) {
      throw new AgentStreamParseError("Agent stream ended with an incomplete event.");
    }
  } finally {
    reader.releaseLock();
  }
}
