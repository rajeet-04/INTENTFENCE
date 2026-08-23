import type { ToolActivity as ToolActivityModel } from "@/lib/agent-state";

export function ToolActivity({ activity }: { activity: ToolActivityModel }) {
  const blocked = activity.decision === "BLOCK";
  return (
    <details className="tool-activity" data-decision={activity.decision} open={blocked}>
      <summary>
        <span className="tool-icon" aria-hidden="true">{blocked ? "×" : "↗"}</span>
        <span>
          <small>Protected tool</small>
          <strong>{activity.tool.replaceAll("_", " ")}</strong>
        </span>
        <b>{activity.decision ?? "CHECKING"}</b>
      </summary>
      <div className="tool-activity-body">
        {activity.reason ? <p>{activity.reason}</p> : <p>Awaiting authoritative decision…</p>}
        <dl>
          <div><dt>Executed</dt><dd>{activity.executed ? "Yes" : "No"}</dd></div>
          <div><dt>Latency</dt><dd>{activity.latencyMs ?? 0} ms</dd></div>
          <div><dt>Receipt</dt><dd>{suffix(activity.receiptId)}</dd></div>
        </dl>
        {activity.matchedRules.length ? (
          <div className="rule-list">
            {activity.matchedRules.map((rule) => <code key={rule}>{rule}</code>)}
          </div>
        ) : null}
      </div>
    </details>
  );
}

function suffix(value?: string) {
  return value ? `…${value.slice(-8)}` : "—";
}
