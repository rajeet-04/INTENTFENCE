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

export type BenchmarkMetricPayload = {
  value: number | null;
  numerator: number;
  denominator: number;
  target: number;
  comparison: ">=" | "<";
  met: boolean;
};

export type BenchmarkSummaryPayload = {
  run_ids: string[];
  scenario_count: number;
  total_events: number;
  headline_kpis: {
    attack_blocking_rate: BenchmarkMetricPayload;
    safe_task_completion_rate: BenchmarkMetricPayload;
    false_positive_rate: BenchmarkMetricPayload;
    scored_events: number;
    excluded_events_without_ground_truth: number;
    malicious_action_count: number;
    benign_action_count: number;
    benign_workflow_count: number;
    benign_workflows_awaiting_approval: number;
  };
  driver_metrics: {
    deterministic_decision_share: number | null;
    semantic_decision_share: number | null;
    cloud_escalation_share: number | null;
    approval_share: number | null;
    action_chain_block_count: number;
    mutated_attack_blocking_rate: number | null;
    block_count_by_rule_id: Record<string, number>;
  };
  guardrails: {
    deterministic_p95_latency_ms: number | null;
    semantic_p95_latency_ms: number | null;
    false_negative_rate: number | null;
  };
};

export type LatestBenchmarkPayload = {
  status: "pending" | "ready";
  run_id: string | null;
  summary: BenchmarkSummaryPayload | null;
};

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

export type DemoDecision = Decision;
export type HotelAttackRun = DemoRunPayload;
export type HotelAttackComparison = HotelAttackDemoPayload;

export function fetchHotelAttackDemo(signal?: AbortSignal): Promise<HotelAttackDemoPayload>;
export function fetchHotelAttackDemo(
  request: typeof fetch,
  baseUrl?: string,
): Promise<HotelAttackDemoPayload>;
export async function fetchHotelAttackDemo(
  signalOrRequest?: AbortSignal | typeof fetch,
  baseUrl: string = getApiBaseUrl(),
): Promise<HotelAttackDemoPayload> {
  const injectedRequest = typeof signalOrRequest === "function";
  const request = injectedRequest ? signalOrRequest : fetch;
  const response = await request(
    `${baseUrl}/demo/hotel-attack`,
    injectedRequest
      ? { method: "POST" }
      : {
          method: "POST",
          headers: { Accept: "application/json" },
          cache: "no-store",
          signal: signalOrRequest,
        },
  );

  if (!response.ok) {
    throw new Error(`Demo API returned ${response.status}`);
  }

  return (await response.json()) as HotelAttackDemoPayload;
}

export async function fetchLatestBenchmarkSummary(
  signal?: AbortSignal,
): Promise<LatestBenchmarkPayload> {
  const response = await fetch(`${getApiBaseUrl()}/benchmarks/latest`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });

  if (!response.ok) {
    throw new Error(`Benchmark API returned ${response.status}`);
  }

  return (await response.json()) as LatestBenchmarkPayload;
}
