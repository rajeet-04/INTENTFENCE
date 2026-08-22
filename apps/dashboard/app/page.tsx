import { HealthCard } from "@/components/HealthCard";

export default function Home() {
  return (
    <main>
      <header>
        <p className="eyebrow">IntentFence</p>
        <h1>Runtime authorization for autonomous AI agents</h1>
        <p>
          Phase 1 establishes the typed, fail-closed security boundary before production policy
          execution is enabled.
        </p>
      </header>
      <HealthCard />
    </main>
  );
}
