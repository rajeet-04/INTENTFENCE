import type { Decision } from "@/lib/api";

export function DecisionBadge({ decision }: { decision: Decision }) {
  const label = decision === "REQUIRE_APPROVAL" ? "APPROVAL" : decision;
  return (
    <span className="decision-badge" data-decision={decision}>
      {label}
    </span>
  );
}
