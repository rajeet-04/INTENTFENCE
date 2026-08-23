import type {
  AgentContractSummary,
  AgentStreamEvent,
  CitationSource,
} from "./agent-api";

export type ToolActivity = {
  id: string;
  tool: string;
  argumentSummary: Record<string, string | number | boolean>;
  decision?: "ALLOW" | "BLOCK" | "REQUIRE_APPROVAL";
  executed?: boolean;
  reason?: string;
  matchedRules: string[];
  receiptId?: string;
  latencyMs?: number;
};

export type ConversationMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  status: "complete" | "streaming" | "error";
  sources: CitationSource[];
  activities: ToolActivity[];
  provider: "local" | "cloud" | null;
  routeReason: "primary" | "fallback" | "escalation" | "explicit" | null;
};

export type AgentConversationState = {
  messages: ConversationMessage[];
  contract: AgentContractSummary | null;
  streaming: boolean;
  modelStatus: string | null;
  activeAssistantId: string | null;
  draft: string;
  retryMessage: string | null;
  error: { code: string; message: string; recoverable: boolean } | null;
};

export const initialAgentConversationState: AgentConversationState = {
  messages: [],
  contract: null,
  streaming: false,
  modelStatus: null,
  activeAssistantId: null,
  draft: "",
  retryMessage: null,
  error: null,
};

export type AgentAction =
  | {
      type: "submit";
      userId: string;
      assistantId: string;
      content: string;
    }
  | { type: "event"; event: AgentStreamEvent }
  | { type: "transport_error"; message: string; recoverable: boolean }
  | { type: "set_draft"; draft: string }
  | { type: "reset" };

export function agentReducer(
  state: AgentConversationState,
  action: AgentAction,
): AgentConversationState {
  switch (action.type) {
    case "submit":
      return {
        ...state,
        messages: [
          ...state.messages,
          message(action.userId, "user", action.content, "complete"),
          message(action.assistantId, "assistant", "", "streaming"),
        ],
        streaming: true,
        modelStatus: "thinking",
        activeAssistantId: action.assistantId,
        draft: action.content,
        retryMessage: null,
        error: null,
      };
    case "set_draft":
      return { ...state, draft: action.draft };
    case "transport_error":
      return failState(state, "TRANSPORT_ERROR", action.message, action.recoverable);
    case "event":
      return reduceEvent(state, action.event);
    case "reset":
      return initialAgentConversationState;
  }
}

function reduceEvent(
  state: AgentConversationState,
  event: AgentStreamEvent,
): AgentConversationState {
  switch (event.event) {
    case "session":
      return { ...state, contract: event.contract };
    case "model_status":
      return {
        ...updateAssistant(state, (assistant) => ({
          ...assistant,
          provider: event.provider,
          routeReason: event.route_reason,
        })),
        modelStatus: event.status,
      };
    case "tool_proposed":
      return updateAssistant(state, (assistant) => ({
        ...assistant,
        activities: [
          ...assistant.activities,
          {
            id: `tool-${event.sequence}`,
            tool: event.tool,
            argumentSummary: event.argument_summary,
            matchedRules: [],
          },
        ],
      }));
    case "tool_decision":
      return updateAssistant(state, (assistant) => {
        const index = assistant.activities.findLastIndex(
          (activity) => activity.tool === event.tool && !activity.decision,
        );
        if (index < 0) return assistant;
        const activities = [...assistant.activities];
        activities[index] = {
          ...activities[index],
          decision: event.decision,
          executed: event.executed,
          reason: event.reason,
          matchedRules: event.matched_rules,
          receiptId: event.receipt_id,
          latencyMs: event.latency_ms,
        };
        return { ...assistant, activities };
      });
    case "source":
      return updateAssistant(state, (assistant) => ({
        ...assistant,
        sources: assistant.sources.some((source) => source.url === event.source.url)
          ? assistant.sources
          : [...assistant.sources, event.source],
      }));
    case "assistant_delta":
      return updateAssistant(state, (assistant) => ({
        ...assistant,
        content: assistant.content + event.delta,
      }));
    case "assistant_reset":
      return updateAssistant(state, (assistant) => ({
        ...assistant,
        content: "",
      }));
    case "assistant_done":
      return {
        ...updateAssistant(state, (assistant) => ({
          ...assistant,
          status: "complete",
        })),
        contract: event.contract,
        streaming: false,
        modelStatus: null,
        activeAssistantId: null,
        draft: "",
        retryMessage: null,
      };
    case "error":
      return failState(state, event.code, event.message, event.recoverable);
    default: {
      const exhaustive: never = event;
      throw new Error(`Unknown agent event: ${JSON.stringify(exhaustive)}`);
    }
  }
}

function failState(
  state: AgentConversationState,
  code: string,
  messageText: string,
  recoverable: boolean,
): AgentConversationState {
  const lastUser = state.messages.findLast((item) => item.role === "user");
  return {
    ...updateAssistant(state, (assistant) => ({ ...assistant, status: "error" })),
    streaming: false,
    modelStatus: null,
    activeAssistantId: null,
    draft: lastUser?.content ?? state.draft,
    retryMessage: recoverable ? (lastUser?.content ?? null) : null,
    error: { code, message: messageText, recoverable },
  };
}

function updateAssistant(
  state: AgentConversationState,
  update: (message: ConversationMessage) => ConversationMessage,
): AgentConversationState {
  if (!state.activeAssistantId) return state;
  return {
    ...state,
    messages: state.messages.map((item) =>
      item.id === state.activeAssistantId ? update(item) : item,
    ),
  };
}

function message(
  id: string,
  role: "user" | "assistant",
  content: string,
  status: ConversationMessage["status"],
): ConversationMessage {
  return {
    id,
    role,
    content,
    status,
    sources: [],
    activities: [],
    provider: null,
    routeReason: null,
  };
}
