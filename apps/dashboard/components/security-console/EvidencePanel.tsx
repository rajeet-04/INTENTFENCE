import type { ConsoleAction } from "@/lib/security-console";

export function EvidencePanel({ action }: { action: ConsoleAction }) {
  const sensitive = action.resourceClass === "SECRET" || action.resourceClass === "CREDENTIAL";
  const external = action.destinationClass === "UNKNOWN_EXTERNAL" || action.destinationClass === "BLOCKED";

  return (
    <section className="console-card evidence-card" aria-labelledby="evidence-heading">
      <p className="section-kicker">Data & destination evidence</p>
      <h2 id="evidence-heading">What the action touched</h2>

      <div className="evidence-flow">
        <FlowNode label="Resource" value={action.resourceClass ?? "Unclassified"} danger={sensitive} />
        <span className="flow-arrow" aria-hidden="true">→</span>
        <FlowNode label="Tool" value={action.tool} />
        <span className="flow-arrow" aria-hidden="true">→</span>
        <FlowNode
          label="Destination"
          value={action.destination ?? "Internal / none"}
          detail={action.destinationClass ?? "Not applicable"}
          danger={external}
        />
      </div>

      <div className="data-ref-row">
        <span>Controlled data references</span>
        {action.dataRefs.length ? (
          action.dataRefs.map((ref) => <code key={ref}>{ref}</code>)
        ) : (
          <strong>None</strong>
        )}
      </div>
    </section>
  );
}

function FlowNode({
  label,
  value,
  detail,
  danger = false,
}: {
  label: string;
  value: string;
  detail?: string;
  danger?: boolean;
}) {
  return (
    <div className="flow-node" data-danger={danger}>
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </div>
  );
}
