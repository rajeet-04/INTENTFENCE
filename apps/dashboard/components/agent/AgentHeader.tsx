import { HealthCard } from "@/components/HealthCard";

export function AgentHeader() {
  return (
    <header className="agent-header">
      <div>
        <p className="agent-eyebrow">Local intelligence · authoritative execution</p>
        <h1>Ask freely. Act safely.</h1>
        <p>
          Qwen researches the live web while IntentFence authorizes every proposed tool call
          before it can execute.
        </p>
      </div>
      <div className="agent-runtime">
        <HealthCard />
      </div>
    </header>
  );
}
