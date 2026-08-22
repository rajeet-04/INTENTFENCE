import type { ConsoleAction, SecurityConsoleViewModel } from "@/lib/security-console";

import { DecisionBadge } from "./DecisionBadge";

export function AttackChain({ view }: { view: SecurityConsoleViewModel }) {
  return (
    <section className="console-card attack-chain-card" aria-labelledby="attack-chain-heading">
      <div className="card-heading-row">
        <div>
          <p className="section-kicker">State & action-chain context</p>
          <h2 id="attack-chain-heading">Indirect prompt-injection chain</h2>
        </div>
        <span className="status-pill" data-status={view.attackBlocked ? "safe" : "danger"}>
          {view.attackBlocked ? "Attack blocked" : "Review required"}
        </span>
      </div>

      <div className="attack-chain">
        {view.actions.map((action, index) => (
          <div className="attack-chain-step" key={action.id}>
            <ChainNode action={action} />
            {index < view.actions.length - 1 ? <span className="chain-arrow" aria-hidden="true">→</span> : null}
          </div>
        ))}
      </div>

      <div className="comparison-strip">
        <div>
          <span>Protected run</span>
          <strong>{view.sensitiveDataEscaped ? "Sensitive data escaped" : "No sensitive data escaped"}</strong>
        </div>
        <div>
          <span>Controlled disabled comparison</span>
          <strong>{view.disabledComparison.exfiltrationExecuted ? "Exfiltration executed" : "No exfiltration"}</strong>
        </div>
      </div>
    </section>
  );
}

function ChainNode({ action }: { action: ConsoleAction }) {
  return (
    <div className="chain-node" data-decision={action.decision}>
      <span>{action.tool}</span>
      <DecisionBadge decision={action.decision} />
    </div>
  );
}
