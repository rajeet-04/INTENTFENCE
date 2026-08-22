import { HealthCard } from "@/components/HealthCard";

export default function Home() {
  return (
    <main>
      <header>
        <p className="eyebrow">IntentFence</p>
        <h1>Runtime authorization for autonomous AI agents</h1>
        <p>
          Phases 1–4 are integrated on main: typed contracts, deterministic policy, stateful action
          analysis, and purpose-bound data-flow checks now protect gateway actions.
        </p>
      </header>
      <HealthCard />
    </main>
  );
}
