import type { ConsoleAction } from "@/lib/security-console";

import { DecisionBadge } from "./DecisionBadge";

export function ReceiptPanel({ action }: { action: ConsoleAction }) {
  return (
    <section className="console-card receipt-card" aria-labelledby="receipt-heading">
      <div className="card-heading-row">
        <div>
          <p className="section-kicker">Decision explanation</p>
          <h2 id="receipt-heading">Why IntentFence decided this</h2>
        </div>
        <DecisionBadge decision={action.decision} />
      </div>

      <p className="decision-reason">{action.reason}</p>

      <dl className="evidence-grid">
        <Evidence label="Tool" value={action.tool} mono />
        <Evidence label="Risk score" value={action.riskScore.toFixed(2)} />
        <Evidence label="Resource" value={action.resourceClass ?? "Not classified"} />
        <Evidence label="Destination" value={action.destination ?? "No external destination"} />
        <Evidence label="Destination trust" value={action.destinationClass ?? "Not applicable"} />
        <Evidence label="Decision source" value={action.decisionSource} />
      </dl>

      <details className="technical-details">
        <summary>Technical Action Receipt</summary>
        <dl className="technical-grid">
          <Evidence label="Receipt ID" value={action.id} mono />
          <Evidence label="Request ID" value={action.requestId} mono />
          <Evidence label="Intent ID" value={action.intentId} mono />
          <Evidence label="Latency" value={`${action.latencyMs} ms`} />
          <Evidence
            label="Semantic confidence"
            value={action.semanticConfidence === null ? "Not evaluated" : action.semanticConfidence.toFixed(2)}
          />
          <Evidence
            label="Semantic relevance"
            value={action.semanticRelevance === null ? "Not evaluated" : action.semanticRelevance.toFixed(2)}
          />
        </dl>
        <div className="rule-list">
          <span>Matched rules</span>
          {action.matchedRules.length ? (
            <ul>
              {action.matchedRules.map((rule) => (
                <li key={rule}><code>{rule}</code></li>
              ))}
            </ul>
          ) : (
            <p>No deterministic rule matched.</p>
          )}
        </div>
      </details>
    </section>
  );
}

function Evidence({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd className={mono ? "mono" : undefined}>{value}</dd>
    </div>
  );
}
