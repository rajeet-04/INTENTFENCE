import type { SecurityConsoleViewModel } from "@/lib/security-console";

export function BenchmarkPanel({ benchmark }: { benchmark: SecurityConsoleViewModel["benchmark"] }) {
  return (
    <section className="console-card benchmark-card" aria-labelledby="benchmark-heading">
      <p className="section-kicker">Benchmark KPI summary</p>
      <h2 id="benchmark-heading">Phase 8 benchmark data</h2>
      {benchmark.status === "pending" ? (
        <div className="benchmark-pending">
          <strong>Benchmark data pending Phase 8</strong>
          <p>
            Attack Blocking Rate, Safe Task Completion Rate and False Positive Rate will render only
            from measured benchmark records. No placeholder metrics are shown.
          </p>
        </div>
      ) : null}
    </section>
  );
}
