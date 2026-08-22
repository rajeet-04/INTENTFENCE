import type { ActionReceiptPayload, HotelAttackDemoPayload } from "./api";

export type ConsoleAction = {
  id: string;
  timestamp: string;
  tool: string;
  decision: ActionReceiptPayload["final_decision"];
  reason: string;
  riskScore: number;
  resourceClass: string | null;
  destination: string | null;
  destinationClass: string | null;
  dataRefs: string[];
  matchedRules: string[];
  ruleStrength: string | null;
  semanticRelevance: number | null;
  semanticConfidence: number | null;
  latencyMs: number;
  decisionSource: string;
  sessionId: string;
  intentId: string;
  requestId: string;
};

export type SecurityConsoleViewModel = {
  scenarioId: string;
  objective: string;
  contractVersion: number;
  sessionId: string;
  actions: ConsoleAction[];
  attackBlocked: boolean;
  sensitiveDataEscaped: boolean;
  legitimateWorkflowCompleted: boolean;
  disabledComparison: {
    secretReadExecuted: boolean;
    exfiltrationExecuted: boolean;
  };
  benchmark: {
    status: "pending";
    metrics: null;
  };
};

function mapReceipt(receipt: ActionReceiptPayload): ConsoleAction {
  return {
    id: receipt.receipt_id,
    timestamp: receipt.timestamp,
    tool: receipt.tool,
    decision: receipt.final_decision,
    reason: receipt.reason,
    riskScore: receipt.risk_score,
    resourceClass: receipt.resource_class,
    destination: receipt.destination,
    destinationClass: receipt.destination_class,
    dataRefs: receipt.data_refs,
    matchedRules: receipt.matched_rules,
    ruleStrength: receipt.rule_strength,
    semanticRelevance: receipt.semantic_relevance_score,
    semanticConfidence: receipt.semantic_confidence,
    latencyMs: receipt.latency_ms,
    decisionSource: receipt.decision_source,
    sessionId: receipt.session_id,
    intentId: receipt.intent_id,
    requestId: receipt.request_id,
  };
}

export function buildSecurityConsoleViewModel(
  payload: HotelAttackDemoPayload,
): SecurityConsoleViewModel {
  const actions = payload.enabled.receipts.map(mapReceipt);
  const sessionId = actions[0]?.sessionId ?? "unknown";
  const blockedAttackActions = actions.filter(
    (action) =>
      action.decision === "BLOCK" &&
      (action.tool === "read_file" || action.tool === "http_request"),
  );

  return {
    scenarioId: payload.scenario_id,
    objective: payload.objective,
    contractVersion: payload.contract_version,
    sessionId,
    actions,
    attackBlocked:
      blockedAttackActions.length >= 2 &&
      !payload.enabled.secret_read_executed &&
      !payload.enabled.exfiltration_executed,
    sensitiveDataEscaped: payload.enabled.exfiltration_executed,
    legitimateWorkflowCompleted: payload.enabled.legitimate_workflow_completed,
    disabledComparison: {
      secretReadExecuted: payload.disabled.secret_read_executed,
      exfiltrationExecuted: payload.disabled.exfiltration_executed,
    },
    benchmark: {
      status: "pending",
      metrics: null,
    },
  };
}
