import type { AgentContractSummary } from "@/lib/agent-api";

export function ContractCard({ contract }: { contract: AgentContractSummary | null }) {
  return (
    <section className="contract-card" aria-label="Active Intent Contract">
      <div className="contract-card-heading">
        <div>
          <p>Active Intent Contract</p>
          <h2>{contract ? `Contract v${contract.contract_version}` : "Contract pending"}</h2>
        </div>
        <span data-enabled={contract?.web_research_enabled ?? false}>
          {contract?.web_research_enabled ? "Web research on" : "Web research off"}
        </span>
      </div>
      <p className="contract-objective">
        {contract?.objective ?? "Your first message creates server-owned research authority."}
      </p>
      <dl>
        <div>
          <dt>Intent</dt>
          <dd>{suffix(contract?.intent_id)}</dd>
        </div>
        <div>
          <dt>Previous</dt>
          <dd>{suffix(contract?.previous_intent_id)}</dd>
        </div>
      </dl>
    </section>
  );
}

function suffix(value?: string | null) {
  return value ? `…${value.slice(-8)}` : "—";
}
