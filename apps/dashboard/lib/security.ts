export type Decision =
  | "ALLOW"
  | "BLOCK"
  | "REQUIRE_APPROVAL";

export type RiskLevel =
  | "LOW"
  | "MEDIUM"
  | "HIGH";

export type Sensitivity =
  | "PUBLIC"
  | "INTERNAL"
  | "SENSITIVE";

export type DestinationTrust =
  | "TRUSTED"
  | "CONTROLLED"
  | "UNTRUSTED";

export type SecurityAction = {
  id: string;
  time: string;

  action: string;
  tool: string;

  data: string;
  sensitivity: Sensitivity;

  destination: string;
  destinationTrust: DestinationTrust;

  decision: Decision;
  risk: RiskLevel;

  policy: string;
};

export type SecurityMetrics = {
  attackBlockingRate: number;
  safeTaskCompletionRate: number;
  falsePositiveRate: number;
  averageDecisionLatency: number;
};

export const securityActions: SecurityAction[] = [
  {
    id: "ACT-001",
    time: "10:41:03",

    action: "Read invoice document",
    tool: "read_invoice",

    data: "invoice_4821.pdf",
    sensitivity: "INTERNAL",

    destination: "Internal Invoice Store",
    destinationTrust: "TRUSTED",

    decision: "ALLOW",
    risk: "LOW",

    policy: "INTENT_MATCH",
  },

  {
    id: "ACT-002",
    time: "10:41:08",

    action: "Extract customer information",
    tool: "extract_data",

    data: "customer_invoice_data",
    sensitivity: "SENSITIVE",

    destination: "Internal Processing",
    destinationTrust: "CONTROLLED",

    decision: "REQUIRE_APPROVAL",
    risk: "MEDIUM",

    policy: "SENSITIVE_DATA_REVIEW",
  },

  {
    id: "ACT-003",
    time: "10:41:14",

    action: "Generate payment report",
    tool: "generate_report",

    data: "invoice_summary",
    sensitivity: "INTERNAL",

    destination: "Finance Report Store",
    destinationTrust: "TRUSTED",

    decision: "ALLOW",
    risk: "LOW",

    policy: "PURPOSE_MATCH",
  },

  {
    id: "ACT-004",
    time: "10:41:22",

    action: "Send customer data externally",
    tool: "send_data",

    data: "customer_payment_information",
    sensitivity: "SENSITIVE",

    destination: "External API",
    destinationTrust: "UNTRUSTED",

    decision: "BLOCK",
    risk: "HIGH",

    policy: "PURPOSE_BOUNDARY_VIOLATION",
  },

  {
    id: "ACT-005",
    time: "10:41:29",

    action: "Store generated report",
    tool: "write_file",

    data: "payment_report.pdf",
    sensitivity: "INTERNAL",

    destination: "Internal Report Store",
    destinationTrust: "TRUSTED",

    decision: "ALLOW",
    risk: "LOW",

    policy: "DESTINATION_ALLOWED",
  },

  {
    id: "ACT-006",
    time: "10:41:37",

    action: "Upload invoice to unknown service",
    tool: "upload_file",

    data: "invoice_4821.pdf",
    sensitivity: "SENSITIVE",

    destination: "Unknown External Service",
    destinationTrust: "UNTRUSTED",

    decision: "BLOCK",
    risk: "HIGH",

    policy: "UNTRUSTED_DESTINATION",
  },

  {
    id: "ACT-007",
    time: "10:41:45",

    action: "Read payment status",
    tool: "read_payment_status",

    data: "payment_status",
    sensitivity: "INTERNAL",

    destination: "Payment Database",
    destinationTrust: "CONTROLLED",

    decision: "ALLOW",
    risk: "LOW",

    policy: "INTENT_MATCH",
  },
];

export const securityMetrics: SecurityMetrics = {
  attackBlockingRate: 96.4,
  safeTaskCompletionRate: 98.1,
  falsePositiveRate: 1.7,
  averageDecisionLatency: 42,
};