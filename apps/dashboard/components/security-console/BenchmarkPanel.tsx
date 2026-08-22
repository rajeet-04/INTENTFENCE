import type { BenchmarkMetricPayload } from "@/lib/api";
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
      {benchmark.status === "ready" ? (
        <div className="benchmark-results">
          <div className="benchmark-run-meta">
            <span>Measured run</span>
            <code>{benchmark.runId}</code>
            <span>
              {benchmark.metrics.scenario_count} scenarios · {benchmark.metrics.total_events} actions
            </span>
          </div>
          <div className="benchmark-kpi-grid">
            <MetricCard
              label="Attack Blocking Rate"
              metric={benchmark.metrics.headline_kpis.attack_blocking_rate}
            />
            <MetricCard
              label="Safe Task Completion Rate"
              metric={benchmark.metrics.headline_kpis.safe_task_completion_rate}
            />
            <MetricCard
              label="False Positive Rate"
              metric={benchmark.metrics.headline_kpis.false_positive_rate}
            />
          </div>
          <div className="benchmark-driver-grid">
            <Driver
              label="Approval share"
              value={formatPercent(benchmark.metrics.driver_metrics.approval_share)}
            />
            <Driver
              label="Deterministic decision share"
              value={formatPercent(benchmark.metrics.driver_metrics.deterministic_decision_share)}
            />
            <Driver
              label="Semantic decision share"
              value={formatPercent(benchmark.metrics.driver_metrics.semantic_decision_share)}
            />
            <Driver
              label="Mutated attack blocking"
              value={formatPercent(benchmark.metrics.driver_metrics.mutated_attack_blocking_rate)}
            />
            <Driver
              label="Deterministic P95"
              value={formatLatency(benchmark.metrics.guardrails.deterministic_p95_latency_ms)}
            />
            <Driver
              label="Semantic P95"
              value={formatLatency(benchmark.metrics.guardrails.semantic_p95_latency_ms)}
            />
          </div>
          <div className="benchmark-rules">
            <strong>Top blocking rules</strong>
            <div>
              {topRules(benchmark.metrics.driver_metrics.block_count_by_rule_id).map(
                ([rule, count]) => (
                  <span key={rule}>
                    <code>{rule}</code> {count}
                  </span>
                ),
              )}
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function MetricCard({ label, metric }: { label: string; metric: BenchmarkMetricPayload }) {
  return (
    <article className="benchmark-metric" data-met={metric.met}>
      <span>{label}</span>
      <strong>{formatPercent(metric.value)}</strong>
      <small>
        {metric.numerator}/{metric.denominator} measured · target {metric.comparison}{" "}
        {formatPercent(metric.target)}
      </small>
    </article>
  );
}

function Driver({ label, value }: { label: string; value: string }) {
  return (
    <div className="benchmark-driver">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatPercent(value: number | null): string {
  return value === null ? "N/A" : `${(value * 100).toFixed(1)}%`;
}

function formatLatency(value: number | null): string {
  return value === null ? "N/A" : `${value} ms`;
}

function topRules(rules: Record<string, number>): Array<[string, number]> {
  return Object.entries(rules)
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .slice(0, 5);
}
