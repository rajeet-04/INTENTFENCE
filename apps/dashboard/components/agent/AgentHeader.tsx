import { HealthCard } from "@/components/HealthCard";

export function AgentHeader() {
  return (
    <header className="agent-header">
      <div>
        <p className="agent-eyebrow">Adaptive intelligence · authoritative execution</p>
        <h1>Ask freely. Act safely.</h1>
        <p>
          Local Qwen leads, Ollama Cloud can assist, and IntentFence authorizes every proposed
          tool call before either model can execute it.
        </p>
      </div>
      <div className="agent-runtime">
        <HealthCard />
      </div>
    </header>
  );
}
