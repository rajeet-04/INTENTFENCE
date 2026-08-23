"use client";

import { useMemo, useState } from "react";

import type {
  AgentConversationState,
  ConversationMessage,
  ToolActivity,
} from "@/lib/agent-state";

import { DecisionBadge } from "./DecisionBadge";

type DecisionFilter = "ALL" | "ALLOW" | "BLOCK" | "REQUIRE_APPROVAL";

type LiveAction = ToolActivity & {
  messageId: string;
  provider: ConversationMessage["provider"];
  routeReason: ConversationMessage["routeReason"];
};

export function SecurityConsole({ state }: { state: AgentConversationState }) {
  const [selectedId, setSelectedId] = useState("");
  const [filter, setFilter] = useState<DecisionFilter>("ALL");
  const [query, setQuery] = useState("");
  const actions = useMemo(
    () =>
      state.messages.flatMap((message) =>
        message.role === "assistant"
          ? message.activities.map((activity) => ({
              ...activity,
              messageId: message.id,
              provider: message.provider,
              routeReason: message.routeReason,
            }))
          : [],
      ),
    [state.messages],
  );
  const sources = useMemo(
    () =>
      Array.from(
        new Map(
          state.messages
            .flatMap((message) => message.sources)
            .map((source) => [source.url, source]),
        ).values(),
      ),
    [state.messages],
  );
  const filteredActions = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return actions.filter((action) => {
      const decisionMatches = filter === "ALL" || action.decision === filter;
      const searchMatches =
        !normalized ||
        action.tool.toLowerCase().includes(normalized) ||
        action.reason?.toLowerCase().includes(normalized) ||
        action.matchedRules.some((rule) => rule.toLowerCase().includes(normalized));
      return decisionMatches && searchMatches;
    });
  }, [actions, filter, query]);

  if (!state.contract && state.messages.length === 0) {
    return (
      <main className="console-shell">
        <section className="console-card console-loading" aria-live="polite">
          <p className="section-kicker">Live session evidence</p>
          <h1>No agent evidence yet</h1>
          <p>
            Run a query in the Agent tab. Its real contracts, tool decisions, receipts, and sources
            will appear here.
          </p>
        </section>
      </main>
    );
  }

  const selectedAction =
    actions.find((action) => action.id === selectedId) ??
    filteredActions[0] ??
    actions[0] ??
    null;
  const allowed = actions.filter((action) => action.decision === "ALLOW").length;
  const blocked = actions.filter((action) => action.decision === "BLOCK").length;
  const executed = actions.filter((action) => action.executed).length;

  return (
    <main className="console-shell">
      <header className="console-header">
        <div>
          <p className="eyebrow">IntentFence Security Operations</p>
          <h1>Live agent evidence</h1>
          <p className="header-copy">
            This view is derived only from the current Agent session&apos;s streamed contracts,
            authorization decisions, receipts, and sources.
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

      <section
        className="console-card session-overview"
        aria-labelledby="active-objective-heading"
      >
        <div>
          <p className="section-kicker">Active objective</p>
          <h2 id="active-objective-heading">
            {state.contract?.objective ?? "Contract pending"}
          </h2>
          <p className="muted-copy">
            Session <code>{state.contract?.session_id ?? "pending"}</code> · Intent{" "}
            <code>{state.contract?.intent_id ?? "pending"}</code>
          </p>
        </div>
        <div
          className="contract-chip"
          aria-label={`Intent Contract version ${state.contract?.contract_version ?? 0}`}
        >
          <span>Intent Contract</span>
          <strong>v{state.contract?.contract_version ?? 0}</strong>
        </div>
      </section>

      <section className="judge-summary" aria-label="Live evidence summary">
        <SummaryCard
          label="Allowed actions"
          value={String(allowed)}
          tone="safe"
          detail="Authorized by the active contract"
        />
        <SummaryCard
          label="Blocked actions"
          value={String(blocked)}
          tone={blocked ? "danger" : "neutral"}
          detail="Prevented before tool execution"
        />
        <SummaryCard
          label="Executed actions"
          value={String(executed)}
          tone="neutral"
          detail={`${sources.length} cited source${sources.length === 1 ? "" : "s"}`}
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
              {decision === "REQUIRE_APPROVAL"
                ? "Approval"
                : decision.charAt(0) + decision.slice(1).toLowerCase()}
            </button>
          ))}
        </div>
        <label className="search-field">
          <span>Search live actions</span>
          <input
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Tool, reason or rule"
            type="search"
            value={query}
          />
        </label>
      </section>

      <section className="console-two-column">
        <section className="console-card timeline-card" aria-labelledby="timeline-heading">
          <div className="card-heading-row">
            <div>
              <p className="section-kicker">Current session stream</p>
              <h2 id="timeline-heading">Protected tool decisions</h2>
            </div>
            <span className="count-pill">{filteredActions.length} actions</span>
          </div>
          <div className="timeline-list">
            {filteredActions.length ? (
              filteredActions.map((action, index) => (
                <button
                  className="timeline-row"
                  data-selected={action.id === selectedAction?.id}
                  key={`${action.messageId}-${action.id}`}
                  onClick={() => setSelectedId(action.id)}
                  type="button"
                >
                  <span className="timeline-index">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span className="timeline-main">
                    <strong>{humanize(action.tool)}</strong>
                    <small>{action.matchedRules[0] ?? "Decision pending"}</small>
                  </span>
                  {action.decision ? (
                    <DecisionBadge decision={action.decision} />
                  ) : (
                    <span className="decision-badge">PENDING</span>
                  )}
                </button>
              ))
            ) : (
              <p className="muted-copy">No matching tool actions in this session.</p>
            )}
          </div>
        </section>

        {selectedAction ? (
          <LiveReceipt action={selectedAction} />
        ) : (
          <section className="console-card receipt-card">
            <p className="section-kicker">Decision explanation</p>
            <h2>No tool receipt yet</h2>
            <p className="muted-copy">The current query has not proposed a tool call.</p>
          </section>
        )}
      </section>

      <section className="console-card evidence-card" aria-labelledby="live-sources-heading">
        <div className="card-heading-row">
          <div>
            <p className="section-kicker">Current session provenance</p>
            <h2 id="live-sources-heading">Sources returned by executed tools</h2>
          </div>
          <span className="count-pill">{sources.length} sources</span>
        </div>
        {sources.length ? (
          <div className="source-cards">
            {sources.map((source) => (
              <a
                href={source.url}
                key={source.url}
                rel="noreferrer noopener"
                target="_blank"
              >
                <span aria-hidden="true">↗</span>
                <div>
                  <strong>{source.title}</strong>
                  <small>{source.snippet ?? source.url}</small>
                </div>
              </a>
            ))}
          </div>
        ) : (
          <p className="muted-copy">No sources have been returned in this session.</p>
        )}
      </section>
    </main>
  );
}

function LiveReceipt({ action }: { action: LiveAction }) {
  const route =
    action.provider && action.routeReason
      ? `${capitalize(action.provider)} · ${action.routeReason}`
      : "Not reported";
  return (
    <section className="console-card receipt-card" aria-labelledby="receipt-heading">
      <div className="card-heading-row">
        <div>
          <p className="section-kicker">Authoritative stream receipt</p>
          <h2 id="receipt-heading">Why IntentFence decided this</h2>
        </div>
        {action.decision ? (
          <DecisionBadge decision={action.decision} />
        ) : (
          <span className="decision-badge">PENDING</span>
        )}
      </div>
      <p className="decision-reason">
        {action.reason ?? "Awaiting an authorization decision."}
      </p>
      <dl className="evidence-grid">
        <Evidence label="Tool" value={action.tool} mono />
        <Evidence
          label="Executed"
          value={
            action.executed === undefined ? "Pending" : action.executed ? "Yes" : "No"
          }
        />
        <Evidence label="Model route" value={route} />
        <Evidence
          label="Latency"
          value={action.latencyMs === undefined ? "Pending" : `${action.latencyMs} ms`}
        />
      </dl>
      <details className="technical-details" open>
        <summary>Technical Action Receipt</summary>
        <dl className="technical-grid">
          <Evidence label="Receipt ID" value={action.receiptId ?? "Pending"} mono />
          <Evidence label="Proposal ID" value={action.id} mono />
          <Evidence
            label="Arguments"
            value={JSON.stringify(action.argumentSummary)}
            mono
          />
        </dl>
        <div className="rule-list">
          <span>Matched rules</span>
          {action.matchedRules.length ? (
            <ul>
              {action.matchedRules.map((rule) => (
                <li key={rule}><code>{rule}</code></li>
              ))}
            </ul>
          ) : (
            <p>No rule reported yet.</p>
          )}
        </div>
      </details>
    </section>
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
      <span>{label}</span><strong>{value}</strong><small>{detail}</small>
    </article>
  );
}

function Evidence({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return <div><dt>{label}</dt><dd className={mono ? "mono" : undefined}>{value}</dd></div>;
}

function humanize(tool: string) {
  return tool.split("_").map(capitalize).join(" ");
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
