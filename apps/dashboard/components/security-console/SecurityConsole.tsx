"use client";

import { useEffect, useMemo, useState } from "react";

import { fetchHotelAttackDemo, type Decision } from "@/lib/api";
import {
  buildSecurityConsoleViewModel,
  type ConsoleAction,
  type SecurityConsoleViewModel,
} from "@/lib/security-console";

import { ActionTimeline } from "./ActionTimeline";
import { AttackChain } from "./AttackChain";
import { BenchmarkPanel } from "./BenchmarkPanel";
import { DecisionBadge } from "./DecisionBadge";
import { EvidencePanel } from "./EvidencePanel";
import { ReceiptPanel } from "./ReceiptPanel";
import { SessionOverview } from "./SessionOverview";

type DecisionFilter = "ALL" | Decision;

export function SecurityConsole() {
  const [view, setView] = useState<SecurityConsoleViewModel | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [filter, setFilter] = useState<DecisionFilter>("ALL");
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    fetchHotelAttackDemo(controller.signal)
      .then((payload) => {
        const nextView = buildSecurityConsoleViewModel(payload);
        setView(nextView);
        const blocked = nextView.actions.find((action) => action.decision === "BLOCK");
        setSelectedId(blocked?.id ?? nextView.actions[0]?.id ?? "");
      })
      .catch((cause: unknown) => {
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof Error ? cause.message : "Unable to load IntentFence security data.");
      });

    return () => controller.abort();
  }, []);

  const filteredActions = useMemo(() => {
    if (!view) return [];
    const normalized = query.trim().toLowerCase();
    return view.actions.filter((action) => {
      const decisionMatches = filter === "ALL" || action.decision === filter;
      const searchMatches =
        normalized.length === 0 ||
        action.tool.toLowerCase().includes(normalized) ||
        action.reason.toLowerCase().includes(normalized) ||
        action.matchedRules.some((rule) => rule.toLowerCase().includes(normalized));
      return decisionMatches && searchMatches;
    });
  }, [filter, query, view]);

  if (error) {
    return (
      <main className="console-shell">
        <section className="console-card console-error" role="alert">
          <p className="section-kicker">Security console unavailable</p>
          <h1>Unable to load authoritative gateway evidence</h1>
          <p>{error}</p>
          <p>Start the IntentFence API on port 8000 and refresh this page.</p>
        </section>
      </main>
    );
  }

  if (!view) {
    return (
      <main className="console-shell">
        <section className="console-card console-loading" aria-live="polite">
          <p className="section-kicker">IntentFence</p>
          <h1>Loading security evidence…</h1>
          <p>Reading the controlled hotel attack run from the authoritative Phase 6 gateway.</p>
        </section>
      </main>
    );
  }

  const selectedAction =
    view.actions.find((action) => action.id === selectedId) ?? view.actions[0] ?? null;

  return (
    <main className="console-shell">
      <header className="console-header">
        <div>
          <p className="eyebrow">IntentFence Security Operations</p>
          <h1>Explainable runtime authorization</h1>
          <p className="header-copy">
            See what the user intended, what the agent attempted, what IntentFence decided, and why.
          </p>
        </div>
        <div className="protected-indicator">
          <span aria-hidden="true" />
          <div>
            <small>Gateway</small>
            <strong>Protected</strong>
          </div>
        </div>
      </header>

      <SessionOverview view={view} />

      <section className="judge-summary" aria-label="Security outcome summary">
        <SummaryCard
          label="Attack outcome"
          value={view.attackBlocked ? "Blocked" : "Review"}
          tone={view.attackBlocked ? "safe" : "danger"}
          detail="Secret read and external exfiltration path"
        />
        <SummaryCard
          label="Sensitive data escaped"
          value={view.sensitiveDataEscaped ? "Yes" : "No"}
          tone={view.sensitiveDataEscaped ? "danger" : "safe"}
          detail="Protected gateway execution"
        />
        <SummaryCard
          label="Legitimate workflow"
          value={view.legitimateWorkflowCompleted ? "Completed" : "Stopped"}
          tone={view.legitimateWorkflowCompleted ? "safe" : "neutral"}
          detail="Cheaper hotel choice saved safely"
        />
      </section>

      <section className="console-controls" aria-label="Action filters">
        <div className="filter-group">
          {(["ALL", "ALLOW", "REQUIRE_APPROVAL", "BLOCK"] as const).map((decision) => (
            <button
              className="filter-button"
              data-active={filter === decision}
              key={decision}
              onClick={() => setFilter(decision)}
              type="button"
            >
              {decision === "REQUIRE_APPROVAL" ? "Approval" : decision.charAt(0) + decision.slice(1).toLowerCase()}
            </button>
          ))}
        </div>
        <label className="search-field">
          <span>Search actions</span>
          <input
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Tool, reason or rule"
            type="search"
            value={query}
          />
        </label>
      </section>

      <section className="console-two-column">
        <ActionTimeline
          actions={filteredActions}
          onSelect={(action: ConsoleAction) => setSelectedId(action.id)}
          selectedId={selectedId}
        />
        {selectedAction ? <ReceiptPanel action={selectedAction} /> : <EmptySelection />}
      </section>

      {selectedAction ? <EvidencePanel action={selectedAction} /> : null}
      <AttackChain view={view} />
      <BenchmarkPanel benchmark={view.benchmark} />
    </main>
  );
}

function SummaryCard({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value: string;
  detail: string;
  tone: "safe" | "danger" | "neutral";
}) {
  return (
    <article className="summary-card" data-tone={tone}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function EmptySelection() {
  return (
    <section className="console-card receipt-card">
      <p className="section-kicker">Decision explanation</p>
      <h2>No matching action selected</h2>
      <p className="muted-copy">Change the filters to inspect an authoritative Action Receipt.</p>
    </section>
  );
}
