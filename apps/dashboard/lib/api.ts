export type Decision = "ALLOW" | "BLOCK" | "REQUIRE_APPROVAL";
export type GatewayMode = "ENABLED" | "DISABLED";

export type ActionReceiptPayload = {
  receipt_id: string;
  timestamp: string;
  session_id: string;
  intent_id: string;
  request_id: string;
  tool: string;
  resource_class: string | null;
  destination: string | null;
  destination_class: string | null;
  data_refs: string[];
  matched_rules: string[];
  rule_strength: string | null;
  semantic_relevance_score: number | null;
  semantic_confidence: number | null;
  risk_score: number;
  decision_source: string;
  final_decision: Decision;
  reason: string;
  latency_ms: number;
};

export type SecurityEventPayload = {
  event_id: string;
  scenario_id: string | null;
  session_id: string;
  request_id: string;
  intent_id: string;
  contract_version: number;
  gateway_mode: GatewayMode;
  tool: string;
  resource_class: string | null;
  destination: string | null;
  destination_class: string | null;
  data_sensitivity: string | null;
  matched_rules: string[];
  semantic_relevance: number | null;
  semantic_confidence: number | null;
  accumulated_risk: number;
  risk_score: number;
  final_decision: Decision;
  decision_source: string;
  latency_ms: number;
  workflow_completed: boolean;
  reason: string;
};

export type DemoRunPayload = {
  mode: GatewayMode;
  tool_sequence: string[];
  decisions: Decision[];
  secret_read_executed: boolean;
  exfiltration_executed: boolean;
  legitimate_workflow_completed: boolean;
  receipt_ids: string[];
  receipts: ActionReceiptPayload[];
  events: SecurityEventPayload[];
};

export type HotelAttackDemoPayload = {
  scenario_id: string;
  objective: string;
  contract_version: number;
  disabled: DemoRunPayload;
  enabled: DemoRunPayload;
};

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

export async function fetchHotelAttackDemo(signal?: AbortSignal): Promise<HotelAttackDemoPayload> {
  const response = await fetch(`${getApiBaseUrl()}/demo/hotel-attack`, {
    method: "POST",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });

  if (!response.ok) {
    throw new Error(`IntentFence demo API returned ${response.status}`);
  }

  return (await response.json()) as HotelAttackDemoPayload;
}
