import { DemoComparison } from "@/components/DemoComparison";
import { HealthCard } from "@/components/HealthCard";
import { SecurityConsole } from "@/components/security-console/SecurityConsole";

export default function Home() {
  return (
    <>
      <section className="judge-stage" aria-label="IntentFence judge demonstration">
        <header className="hero">
          <nav className="topbar" aria-label="Project status">
            <span className="wordmark">IntentFence</span>
            <HealthCard />
          </nav>
          <div className="hero-copy">
            <p className="judge-eyebrow">
              <span /> Runtime authorization layer
            </p>
            <h1>
              Stop the action.
              <br />
              Not the agent.
            </h1>
            <p className="hero-summary">
              IntentFence intercepts every protected tool call, blocks prompt-injection attacks at
              runtime, and lets legitimate autonomous work continue.
            </p>
            <div className="phase-strip" aria-label="Integrated project phases">
              <strong>Phases 1–7 integrated</strong>
              <span>5 protected tools</span>
              <span>Policy + semantics + state</span>
              <span>Security operations console</span>
            </div>
          </div>
        </header>
        <DemoComparison />
      </section>
      <SecurityConsole />
    </>
  );
}
