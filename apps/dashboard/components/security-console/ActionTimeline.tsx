import type { ConsoleAction } from "@/lib/security-console";

import { DecisionBadge } from "./DecisionBadge";

export function ActionTimeline({
  actions,
  selectedId,
  onSelect,
}: {
  actions: ConsoleAction[];
  selectedId: string;
  onSelect: (action: ConsoleAction) => void;
}) {
  return (
    <section className="console-card timeline-card" aria-labelledby="timeline-heading">
      <div className="card-heading-row">
        <div>
          <p className="section-kicker">Live action stream</p>
          <h2 id="timeline-heading">Protected tool decisions</h2>
        </div>
        <span className="count-pill">{actions.length} actions</span>
      </div>

      <div className="timeline-list">
        {actions.map((action, index) => (
          <button
            className="timeline-row"
            data-selected={action.id === selectedId}
            key={action.id}
            onClick={() => onSelect(action)}
            type="button"
          >
            <span className="timeline-index">{String(index + 1).padStart(2, "0")}</span>
            <span className="timeline-main">
              <strong>{humanizeTool(action.tool)}</strong>
              <small>{action.matchedRules[0] ?? action.decisionSource}</small>
            </span>
            <DecisionBadge decision={action.decision} />
          </button>
        ))}
      </div>
    </section>
  );
}

function humanizeTool(tool: string): string {
  return tool
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
