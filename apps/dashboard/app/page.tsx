import { HealthCard } from "@/components/HealthCard";

export default function Home() {
  return (
    <main>
      <header>
        <p className="eyebrow">IntentFence</p>
        <h1>Runtime authorization for autonomous AI agents</h1>
        <p>
          Phases 1–6 are integrated on main: typed contracts, deterministic policy, stateful action
          analysis, purpose-bound data flow, semantic authorization, and the authoritative gateway
          protect all five supported tool actions.
        </p>
      </header>
      <HealthCard />
    </main>
  );
}
