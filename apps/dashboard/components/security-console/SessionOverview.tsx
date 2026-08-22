import type { SecurityConsoleViewModel } from "@/lib/security-console";

export function SessionOverview({ view }: { view: SecurityConsoleViewModel }) {
  return (
    <section className="console-card session-overview" aria-labelledby="active-objective-heading">
      <div>
        <p className="section-kicker">Active objective</p>
        <h2 id="active-objective-heading">{view.objective}</h2>
        <p className="muted-copy">
          Session <code>{view.sessionId}</code> · Scenario <code>{view.scenarioId}</code>
        </p>
      </div>
      <div className="contract-chip" aria-label={`Intent Contract version ${view.contractVersion}`}>
        <span>Intent Contract</span>
        <strong>v{view.contractVersion}</strong>
      </div>
    </section>
  );
}
