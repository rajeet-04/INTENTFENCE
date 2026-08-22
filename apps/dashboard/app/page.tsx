"use client";

import { useMemo, useState } from "react";

import {
  securityActions,
  securityMetrics,
  type Decision,
  type SecurityAction,
} from "../lib/security";

type Filter = "ALL" | Decision;

export default function Home() {
  const [selectedAction, setSelectedAction] =
    useState<SecurityAction>(securityActions[3]);

  const [decisionFilter, setDecisionFilter] =
    useState<Filter>("ALL");

  const [searchQuery, setSearchQuery] =
    useState("");

  const filteredActions = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    return securityActions.filter((action) => {
      const matchesDecision =
        decisionFilter === "ALL" ||
        action.decision === decisionFilter;

      const matchesSearch =
        query.length === 0 ||
        action.action.toLowerCase().includes(query) ||
        action.tool.toLowerCase().includes(query) ||
        action.data.toLowerCase().includes(query) ||
        action.destination.toLowerCase().includes(query) ||
        action.policy.toLowerCase().includes(query);

      return matchesDecision && matchesSearch;
    });
  }, [decisionFilter, searchQuery]);

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="flex min-h-screen">

        {/* =====================================================
            SIDEBAR
        ===================================================== */}

        <aside className="hidden w-64 shrink-0 border-r border-slate-800 bg-slate-950 lg:block">

          <div className="flex h-full flex-col">

            <div className="border-b border-slate-800 px-6 py-6">

              <h1 className="text-xl font-bold tracking-tight">
                IntentFence
              </h1>

              <p className="mt-1 text-xs text-slate-500">
                Security Operations
              </p>

            </div>

            <nav className="flex-1 space-y-1 p-4">

              <SidebarItem
                label="Overview"
                active
              />

              <SidebarItem
                label="Action Timeline"
              />

              <SidebarItem
                label="Security Decisions"
              />

              <SidebarItem
                label="Data Flow"
              />

              <SidebarItem
                label="Risk Analysis"
              />

              <SidebarItem
                label="Benchmarks"
              />

            </nav>

            <div className="border-t border-slate-800 p-4">

              <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4">

                <div className="flex items-center gap-2">

                  <span className="h-2 w-2 rounded-full bg-emerald-400" />

                  <span className="text-xs font-semibold text-emerald-400">
                    SYSTEM PROTECTED
                  </span>

                </div>

                <p className="mt-2 text-xs leading-5 text-slate-500">
                  Security policy enforcement is active.
                </p>

              </div>

            </div>

          </div>

        </aside>

        {/* =====================================================
            MAIN
        ===================================================== */}

        <div className="min-w-0 flex-1">

          {/* HEADER */}

          <header className="border-b border-slate-800 bg-slate-950/95 px-6 py-5">

            <div className="flex items-center justify-between gap-4">

              <div>

                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Security Operations
                </p>

                <h1 className="mt-1 text-xl font-semibold">
                  Investigation Console
                </h1>

              </div>

              <div className="flex items-center gap-3">

                <div className="hidden rounded-lg border border-slate-800 bg-slate-900 px-4 py-2 sm:block">

                  <p className="text-[10px] uppercase tracking-wider text-slate-500">
                    Contract
                  </p>

                  <p className="mt-1 text-sm font-semibold">
                    v1.0
                  </p>

                </div>

                <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-4 py-2">

                  <p className="text-[10px] uppercase tracking-wider text-slate-500">
                    Status
                  </p>

                  <p className="mt-1 text-sm font-semibold text-emerald-400">
                    ● PROTECTED
                  </p>

                </div>

              </div>

            </div>

          </header>

          {/* =====================================================
              CONTENT
          ===================================================== */}

          <div className="mx-auto max-w-7xl space-y-6 px-6 py-8">

            {/* ACTIVE INTENT */}

            <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">

              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Active Intent
              </p>

              <h2 className="mt-2 text-xl font-semibold">
                Process customer invoice and prepare payment report
              </h2>

              <div className="mt-4 flex flex-wrap gap-3">

                <span className="rounded-full bg-blue-500/10 px-3 py-1 text-sm text-blue-400">
                  Invoice Processing
                </span>

                <span className="rounded-full bg-slate-800 px-3 py-1 text-sm text-slate-300">
                  Session: IF-2026-001
                </span>

              </div>

            </section>

            {/* SECURITY SUMMARY */}

            <section className="grid gap-6 md:grid-cols-3">

              <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Current Decision
                </p>

                <div className="mt-4">

                  <DecisionBadge
                    decision={selectedAction.decision}
                  />

                </div>

                <p className="mt-4 text-sm leading-6 text-slate-400">
                  {getReason(selectedAction)}
                </p>

              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Risk Level
                </p>

                <p
                  className={`mt-3 text-3xl font-bold ${getRiskColor(
                    selectedAction,
                  )}`}
                >
                  {selectedAction.risk}
                </p>

                <p className="mt-2 text-sm text-slate-400">
                  {selectedAction.sensitivity} data +{" "}
                  {selectedAction.destinationTrust.toLowerCase()}{" "}
                  destination
                </p>

              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Destination Trust
                </p>

                <p
                  className={`mt-3 text-3xl font-bold ${
                    selectedAction.destinationTrust ===
                    "UNTRUSTED"
                      ? "text-red-400"
                      : selectedAction.destinationTrust ===
                          "CONTROLLED"
                        ? "text-amber-400"
                        : "text-emerald-400"
                  }`}
                >
                  {selectedAction.destinationTrust}
                </p>

                <p className="mt-2 text-sm text-slate-400">
                  {selectedAction.destination}
                </p>

              </div>

            </section>

            {/* =====================================================
                ACTION STREAM + RECEIPT
            ===================================================== */}

            <section className="grid gap-6 lg:grid-cols-2">

              {/* ACTION STREAM */}

              <div className="rounded-xl border border-slate-800 bg-slate-900">

                <div className="border-b border-slate-800 p-6">

                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Action Stream
                  </p>

                  <h2 className="mt-1 text-lg font-semibold">
                    Security Events
                  </h2>

                  <div className="mt-4">

                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(event) =>
                        setSearchQuery(event.target.value)
                      }
                      placeholder="Search actions, tools, data..."
                      className="w-full rounded-lg border border-slate-800 bg-slate-950 px-4 py-2.5 text-sm text-slate-200 outline-none placeholder:text-slate-600 focus:border-blue-500/50"
                    />

                  </div>

                  <div className="mt-3 flex flex-wrap gap-2">

                    <FilterButton
                      label="ALL"
                      active={decisionFilter === "ALL"}
                      onClick={() =>
                        setDecisionFilter("ALL")
                      }
                    />

                    <FilterButton
                      label="ALLOW"
                      active={decisionFilter === "ALLOW"}
                      onClick={() =>
                        setDecisionFilter("ALLOW")
                      }
                    />

                    <FilterButton
                      label="APPROVAL"
                      active={
                        decisionFilter === "REQUIRE_APPROVAL"
                      }
                      onClick={() =>
                        setDecisionFilter(
                          "REQUIRE_APPROVAL",
                        )
                      }
                    />

                    <FilterButton
                      label="BLOCK"
                      active={decisionFilter === "BLOCK"}
                      onClick={() =>
                        setDecisionFilter("BLOCK")
                      }
                    />

                  </div>

                </div>

                <div className="divide-y divide-slate-800">

                  {filteredActions.length === 0 ? (

                    <div className="p-8 text-center">

                      <p className="text-sm font-medium text-slate-400">
                        No matching security events
                      </p>

                      <p className="mt-1 text-xs text-slate-600">
                        Try changing the filter or search query.
                      </p>

                    </div>

                  ) : (

                    filteredActions.map((item) => {

                      const isSelected =
                        selectedAction.id === item.id;

                      return (

                        <button
                          key={item.id}
                          onClick={() =>
                            setSelectedAction(item)
                          }
                          className={`flex w-full items-center justify-between border-l-2 px-6 py-4 text-left transition ${
                            isSelected
                              ? "border-l-blue-400 bg-blue-500/5"
                              : "border-l-transparent hover:bg-slate-800/60"
                          }`}
                        >

                          <div className="flex items-center gap-4">

                            <div
                              className={`h-2.5 w-2.5 shrink-0 rounded-full ${
                                item.decision === "BLOCK"
                                  ? "bg-red-400"
                                  : item.decision ===
                                      "REQUIRE_APPROVAL"
                                    ? "bg-amber-400"
                                    : "bg-emerald-400"
                              }`}
                            />

                            <span className="font-mono text-xs text-slate-500">
                              {item.time}
                            </span>

                            <div>

                              <p className="text-sm font-medium">
                                {item.action}
                              </p>

                              <p className="mt-1 text-xs text-slate-500">
                                {item.tool}
                              </p>

                            </div>

                          </div>

                          <DecisionBadge
                            decision={item.decision}
                          />

                        </button>

                      );
                    })

                  )}

                </div>

              </div>

              {/* ACTION RECEIPT */}

              <ActionReceipt
                action={selectedAction}
              />

            </section>

            {/* =====================================================
                EVIDENCE PANEL
            ===================================================== */}

            <EvidencePanel
              action={selectedAction}
            />

            {/* =====================================================
                DATA FLOW
            ===================================================== */}

            <DataFlowSection
              action={selectedAction}
            />

            {/* =====================================================
                ATTACK CHAIN
            ===================================================== */}

            <AttackChain
              action={selectedAction}
            />

            {/* =====================================================
                ANALYTICS
            ===================================================== */}

            <SecurityAnalytics />

          </div>

        </div>

      </div>
    </main>
  );
}

/* ============================================================
   ACTION RECEIPT
============================================================ */

function ActionReceipt({
  action,
}: {
  action: SecurityAction;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900">
      <div className="border-b border-slate-800 p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Action Receipt
            </p>

            <h2 className="mt-1 text-lg font-semibold">
              Human-Readable Security Decision
            </h2>

            <p className="mt-2 text-xs text-slate-600">
              Explainable security decision with technical evidence
            </p>
          </div>

          <DecisionBadge decision={action.decision} />
        </div>
      </div>

      <div className="space-y-6 p-6">
        {/* FINAL DECISION */}
        <div
          className={`rounded-xl border p-5 ${
            action.decision === "BLOCK"
              ? "border-red-500/30 bg-red-500/5"
              : action.decision === "REQUIRE_APPROVAL"
                ? "border-amber-500/30 bg-amber-500/5"
                : "border-emerald-500/30 bg-emerald-500/5"
          }`}
        >
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Final Decision
          </p>

          <p
            className={`mt-2 text-2xl font-bold ${
              action.decision === "BLOCK"
                ? "text-red-400"
                : action.decision === "REQUIRE_APPROVAL"
                  ? "text-amber-400"
                  : "text-emerald-400"
            }`}
          >
            {action.decision === "REQUIRE_APPROVAL"
              ? "APPROVAL REQUIRED"
              : action.decision}
          </p>

          <p className="mt-3 text-sm leading-6 text-slate-400">
            {getReason(action)}
          </p>
        </div>

        {/* REQUESTED ACTION */}
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Requested Action
          </p>

          <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950 p-4">
            <p className="text-sm font-semibold text-slate-200">
              {action.action}
            </p>

            <p className="mt-2 font-mono text-xs text-slate-500">
              Tool: {action.tool}
            </p>
          </div>
        </div>

        {/* EXPANDABLE TECHNICAL EVIDENCE */}
        <details className="group rounded-xl border border-slate-800 bg-slate-950">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 p-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Technical Evidence
              </p>

              <p className="mt-1 text-sm font-medium text-slate-300">
                Contract, policy, provenance and audit details
              </p>
            </div>

            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-slate-800 bg-slate-900 text-slate-400 transition group-open:rotate-180">
              ↓
            </span>
          </summary>

          <div className="space-y-6 border-t border-slate-800 p-5">
            {/* SECURITY CONTEXT */}
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Security Context
              </p>

              <div className="mt-3 grid gap-4 sm:grid-cols-2">
                <ReceiptField
                  label="INTENT"
                  value="Process customer invoice"
                />

                <ReceiptField
                  label="ACTOR"
                  value="IntentFence Agent"
                />

                <ReceiptField
                  label="SOURCE"
                  value={action.data}
                />

                <ReceiptField
                  label="DATA CLASSIFICATION"
                  value={action.sensitivity}
                />

                <ReceiptField
                  label="DESTINATION"
                  value={action.destination}
                />

                <ReceiptField
                  label="DESTINATION TRUST"
                  value={action.destinationTrust}
                />
              </div>
            </div>

            {/* POLICY EVALUATION */}
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Policy Evaluation
              </p>

              <div className="mt-3 rounded-lg border border-slate-800 bg-slate-900 p-4">
                <div className="flex items-center justify-between gap-4">
                  <span className="font-mono text-xs text-blue-400">
                    {action.policy}
                  </span>

                  <span className="rounded-full bg-blue-500/10 px-2.5 py-1 text-[10px] font-semibold text-blue-400">
                    POLICY MATCH
                  </span>
                </div>

                <div className="mt-4 space-y-3">
                  <PolicyCheck
                    label="Intent alignment"
                    passed={action.decision !== "BLOCK"}
                  />

                  <PolicyCheck
                    label="Data sensitivity"
                    passed={action.sensitivity !== "SENSITIVE"}
                  />

                  <PolicyCheck
                    label="Destination trust"
                    passed={action.destinationTrust !== "UNTRUSTED"}
                  />

                  <PolicyCheck
                    label="Purpose boundary"
                    passed={action.policy !== "PURPOSE_BOUNDARY_VIOLATION"}
                  />
                </div>
              </div>
            </div>

            {/* AUDIT METADATA */}
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Audit Metadata
              </p>

              <div className="mt-3 grid gap-4 sm:grid-cols-2">
                <ReceiptField
                  label="RECEIPT ID"
                  value={action.id}
                  mono
                />

                <ReceiptField
                  label="TIMESTAMP"
                  value={`2026-08-22 ${action.time}`}
                  mono
                />

                <ReceiptField
                  label="POLICY VERSION"
                  value="intentfence-policy-v1"
                  mono
                />

                <ReceiptField
                  label="INTEGRITY HASH"
                  value={generateReceiptHash(action)}
                  mono
                />
              </div>
            </div>
          </div>
        </details>
      </div>
    </div>
  );
}

/* ============================================================
   EVIDENCE PANEL
============================================================ */

function EvidencePanel({
  action,
}: {
  action: SecurityAction;
}) {
  const evidence = getEvidence(action);

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">

        <div>

          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Decision Evidence
          </p>

          <h2 className="mt-1 text-lg font-semibold">
            Why IntentFence Made This Decision
          </h2>

        </div>

        <span className="w-fit rounded-full border border-slate-800 bg-slate-950 px-3 py-1 font-mono text-xs text-slate-500">
          {action.id}
        </span>

      </div>

      <div className="mt-8 grid gap-4 md:grid-cols-5">

        <EvidenceNode
          number="01"
          title="Intent"
          value={evidence.intent}
          status="neutral"
        />

        <EvidenceArrow />

        <EvidenceNode
          number="02"
          title="Data"
          value={action.data}
          status={
            action.sensitivity === "SENSITIVE"
              ? "danger"
              : "neutral"
          }
        />

        <EvidenceArrow />

        <EvidenceNode
          number="03"
          title="Destination"
          value={action.destination}
          status={
            action.destinationTrust ===
            "UNTRUSTED"
              ? "danger"
              : "safe"
          }
        />

      </div>

      <div className="my-5 h-px bg-slate-800" />

      <div className="grid gap-4 md:grid-cols-2">

        <div className="rounded-xl border border-slate-800 bg-slate-950 p-5">

          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Policy Signal
          </p>

          <p className="mt-3 font-mono text-sm text-blue-400">
            {action.policy}
          </p>

          <p className="mt-3 text-sm leading-6 text-slate-500">
            {evidence.policyExplanation}
          </p>

        </div>

        <div
          className={`rounded-xl border p-5 ${
            action.decision === "BLOCK"
              ? "border-red-500/20 bg-red-500/5"
              : action.decision ===
                  "REQUIRE_APPROVAL"
                ? "border-amber-500/20 bg-amber-500/5"
                : "border-emerald-500/20 bg-emerald-500/5"
          }`}
        >

          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Enforcement
          </p>

          <p
            className={`mt-3 text-lg font-bold ${
              action.decision === "BLOCK"
                ? "text-red-400"
                : action.decision ===
                    "REQUIRE_APPROVAL"
                  ? "text-amber-400"
                  : "text-emerald-400"
            }`}
          >
            {action.decision}
          </p>

          <p className="mt-3 text-sm leading-6 text-slate-400">
            {evidence.enforcementExplanation}
          </p>

        </div>

      </div>

    </section>
  );
}

/* ============================================================
   DATA FLOW
============================================================ */

function DataFlowSection({
  action,
}: {
  action: SecurityAction;
}) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">

        <div>

          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Data Flow
          </p>

          <h2 className="mt-1 text-lg font-semibold">
            Source → Transformation → Destination
          </h2>

        </div>

        <DecisionBadge
          decision={action.decision}
        />

      </div>

      <div className="mt-8">

        <div className="flex flex-col items-stretch gap-3 lg:flex-row lg:items-center">

          <DataFlowNode
            step="01"
            title="Data Source"
            value={action.data}
            description="Original data accessed by the agent"
            status={
              action.sensitivity ===
              "SENSITIVE"
                ? "danger"
                : "normal"
            }
          />

          <DataFlowConnector />

          <DataFlowNode
            step="02"
            title="Agent / Tool"
            value={action.tool}
            description="Operation requested by the agent"
            status="active"
          />

          <DataFlowConnector />

          <DataFlowNode
            step="03"
            title="Policy Evaluation"
            value={action.policy}
            description="IntentFence evaluates the operation"
            status={
              action.decision === "BLOCK"
                ? "danger"
                : action.decision ===
                    "REQUIRE_APPROVAL"
                  ? "warning"
                  : "safe"
            }
          />

          <DataFlowConnector />

          <DataFlowNode
            step="04"
            title="Destination"
            value={action.destination}
            description="Target receiving the operation"
            status={
              action.destinationTrust ===
              "UNTRUSTED"
                ? "danger"
                : action.destinationTrust ===
                    "CONTROLLED"
                  ? "warning"
                  : "safe"
            }
          />

        </div>

      </div>

    </section>
  );
}

/* ============================================================
   ATTACK CHAIN
============================================================ */

function AttackChain({
  action,
}: {
  action: SecurityAction;
}) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">

        <div>

          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Risk / Action Chain
          </p>

          <h2 className="mt-1 text-lg font-semibold">
            Security Decision Path
          </h2>

        </div>

        <DecisionBadge
          decision={action.decision}
        />

      </div>

      <div className="mt-8 overflow-x-auto pb-3">

        <div className="flex min-w-max items-center gap-3">

          <ChainNode
            text="User Intent"
            subtitle="Invoice Processing"
            active
          />

          <ChainArrow />

          <ChainNode
            text={action.tool}
            subtitle="AGENT TOOL"
            active
          />

          <ChainArrow />

          <ChainNode
            text={action.data}
            subtitle={action.sensitivity}
            danger={
              action.sensitivity ===
              "SENSITIVE"
            }
            active={
              action.sensitivity ===
              "SENSITIVE"
            }
          />

          <ChainArrow />

          <ChainNode
            text={action.destination}
            subtitle={
              action.destinationTrust
            }
            danger={
              action.destinationTrust ===
              "UNTRUSTED"
            }
            active
          />

          <ChainArrow />

          <ChainNode
            text={action.decision}
            subtitle="POLICY DECISION"
            danger={
              action.decision === "BLOCK"
            }
            active
          />

        </div>

      </div>

      <div
        className={`mt-6 rounded-lg border p-4 ${
          action.decision === "BLOCK"
            ? "border-red-500/20 bg-red-500/5"
            : action.decision ===
                "REQUIRE_APPROVAL"
              ? "border-amber-500/20 bg-amber-500/5"
              : "border-emerald-500/20 bg-emerald-500/5"
        }`}
      >

        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Decision Explanation
        </p>

        <p className="mt-2 text-sm leading-6 text-slate-300">
          {getReason(action)}
        </p>

      </div>

    </section>
  );
}

/* ============================================================
   SECURITY ANALYTICS
============================================================ */

function SecurityAnalytics() {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">

        <div>

          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Security Analytics
          </p>

          <h2 className="mt-1 text-lg font-semibold">
            Protection Performance
          </h2>

        </div>

        <span className="w-fit rounded-full border border-slate-800 bg-slate-950 px-3 py-1 text-xs text-slate-400">
          BENCHMARK OUTPUT
        </span>

      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-4">

        <MetricCard
          label="Attack Blocking Rate"
          value={`${securityMetrics.attackBlockingRate}%`}
          description="Malicious actions blocked"
          status="good"
        />

        <MetricCard
          label="Safe Task Completion"
          value={`${securityMetrics.safeTaskCompletionRate}%`}
          description="Legitimate tasks completed"
          status="good"
        />

        <MetricCard
          label="False Positive Rate"
          value={`${securityMetrics.falsePositiveRate}%`}
          description="Legitimate actions blocked"
          status="warning"
        />

        <MetricCard
          label="Decision Latency"
          value={`${securityMetrics.averageDecisionLatency} ms`}
          description="Average security decision"
          status="good"
        />

      </div>

      <p className="mt-5 text-xs text-slate-600">
        Metrics shown here are temporary demo values
        and will later be replaced with verified
        Phase 8 benchmark outputs.
      </p>

    </section>
  );
}

/* ============================================================
   SIDEBAR
============================================================ */

function SidebarItem({
  label,
  active = false,
}: {
  label: string;
  active?: boolean;
}) {
  return (
    <button
      className={`flex w-full items-center rounded-lg px-3 py-2.5 text-left text-sm transition ${
        active
          ? "bg-blue-500/10 text-blue-400"
          : "text-slate-500 hover:bg-slate-900 hover:text-slate-300"
      }`}
    >

      <span
        className={`mr-3 h-1.5 w-1.5 rounded-full ${
          active
            ? "bg-blue-400"
            : "bg-slate-700"
        }`}
      />

      {label}

    </button>
  );
}

/* ============================================================
   FILTER BUTTON
============================================================ */

function FilterButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
        active
          ? "border-blue-500/30 bg-blue-500/10 text-blue-400"
          : "border-slate-800 bg-slate-950 text-slate-500 hover:border-slate-700 hover:text-slate-300"
      }`}
    >
      {label}
    </button>
  );
}

/* ============================================================
   DECISION BADGE
============================================================ */

function DecisionBadge({
  decision,
}: {
  decision: Decision;
}) {
  const styles: Record<Decision, string> = {
    ALLOW:
      "bg-emerald-500/10 text-emerald-400",

    BLOCK:
      "bg-red-500/10 text-red-400",

    REQUIRE_APPROVAL:
      "bg-amber-500/10 text-amber-400",
  };

  return (
    <span
      className={`rounded-full px-3 py-1 text-xs font-semibold ${styles[decision]}`}
    >
      {decision === "REQUIRE_APPROVAL"
        ? "APPROVAL"
        : decision}
    </span>
  );
}

/* ============================================================
   RECEIPT FIELD
============================================================ */

function ReceiptField({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>

      <p className="text-xs text-slate-500">
        {label}
      </p>

      <p
        className={`mt-1 text-sm font-medium ${
          mono
            ? "font-mono text-slate-300"
            : "text-slate-200"
        }`}
      >
        {value}
      </p>

    </div>
  );
}

/* ============================================================
   POLICY CHECK
============================================================ */

function PolicyCheck({
  label,
  passed,
}: {
  label: string;
  passed: boolean;
}) {
  return (
    <div className="flex items-center justify-between">

      <div className="flex items-center gap-3">

        <span
          className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${
            passed
              ? "bg-emerald-500/10 text-emerald-400"
              : "bg-red-500/10 text-red-400"
          }`}
        >
          {passed ? "✓" : "!"}
        </span>

        <span className="text-xs text-slate-400">
          {label}
        </span>

      </div>

      <span
        className={`text-[10px] font-semibold uppercase ${
          passed
            ? "text-emerald-400"
            : "text-red-400"
        }`}
      >
        {passed ? "PASS" : "FAIL"}
      </span>

    </div>
  );
}

/* ============================================================
   EVIDENCE NODE
============================================================ */

function EvidenceNode({
  number,
  title,
  value,
  status,
}: {
  number: string;
  title: string;
  value: string;
  status: "neutral" | "safe" | "danger";
}) {
  const styles = {
    neutral:
      "border-slate-800 bg-slate-950",

    safe:
      "border-emerald-500/30 bg-emerald-500/5",

    danger:
      "border-red-500/30 bg-red-500/5",
  };

  const valueStyles = {
    neutral: "text-slate-200",
    safe: "text-emerald-400",
    danger: "text-red-400",
  };

  return (
    <div
      className={`rounded-xl border p-5 ${styles[status]}`}
    >

      <span className="font-mono text-[10px] text-slate-600">
        {number}
      </span>

      <p className="mt-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
        {title}
      </p>

      <p
        className={`mt-2 break-words text-sm font-semibold ${valueStyles[status]}`}
      >
        {value}
      </p>

    </div>
  );
}

/* ============================================================
   EVIDENCE ARROW
============================================================ */

function EvidenceArrow() {
  return (
    <div className="hidden items-center justify-center md:flex">

      <span className="text-xl text-slate-700">
        →
      </span>

    </div>
  );
}

/* ============================================================
   DATA FLOW NODE
============================================================ */

function DataFlowNode({
  step,
  title,
  value,
  description,
  status,
}: {
  step: string;
  title: string;
  value: string;
  description: string;
  status:
    | "normal"
    | "active"
    | "safe"
    | "warning"
    | "danger";
}) {
  const styles = {
    normal:
      "border-slate-800 bg-slate-950",

    active:
      "border-blue-500/30 bg-blue-500/5",

    safe:
      "border-emerald-500/30 bg-emerald-500/5",

    warning:
      "border-amber-500/30 bg-amber-500/5",

    danger:
      "border-red-500/30 bg-red-500/5",
  };

  const textStyles = {
    normal: "text-slate-200",
    active: "text-blue-400",
    safe: "text-emerald-400",
    warning: "text-amber-400",
    danger: "text-red-400",
  };

  return (
    <div
      className={`flex-1 rounded-xl border p-5 ${styles[status]}`}
    >

      <div className="flex items-center justify-between">

        <span className="font-mono text-[10px] text-slate-600">
          STEP {step}
        </span>

        <span
          className={`h-2 w-2 rounded-full ${
            status === "danger"
              ? "bg-red-400"
              : status === "warning"
                ? "bg-amber-400"
                : status === "safe"
                  ? "bg-emerald-400"
                  : status === "active"
                    ? "bg-blue-400"
                    : "bg-slate-600"
          }`}
        />

      </div>

      <p className="mt-4 text-xs font-semibold uppercase tracking-wider text-slate-500">
        {title}
      </p>

      <p
        className={`mt-2 break-words text-sm font-semibold ${textStyles[status]}`}
      >
        {value}
      </p>

      <p className="mt-2 text-xs leading-5 text-slate-600">
        {description}
      </p>

    </div>
  );
}

/* ============================================================
   DATA FLOW CONNECTOR
============================================================ */

function DataFlowConnector() {
  return (
    <div className="flex items-center justify-center">

      <span className="text-slate-600">
        →
      </span>

    </div>
  );
}

/* ============================================================
   CHAIN NODE
============================================================ */

function ChainNode({
  text,
  subtitle,
  danger = false,
  active = false,
}: {
  text: string;
  subtitle: string;
  danger?: boolean;
  active?: boolean;
}) {
  return (
    <div
      className={`relative min-w-36 rounded-xl border px-5 py-4 transition-all ${
        danger
          ? "border-red-500/30 bg-red-500/10"
          : active
            ? "border-blue-500/40 bg-blue-500/10"
            : "border-slate-700 bg-slate-800/50"
      }`}
    >

      {active && (
        <span className="absolute -right-1.5 -top-1.5 h-3 w-3 rounded-full bg-blue-400 ring-4 ring-slate-900" />
      )}

      <p
        className={`break-words text-sm font-semibold ${
          danger
            ? "text-red-400"
            : active
              ? "text-blue-400"
              : "text-slate-200"
        }`}
      >
        {text}
      </p>

      <p
        className={`mt-2 text-xs ${
          danger
            ? "text-red-400/70"
            : active
              ? "text-blue-400/70"
              : "text-slate-500"
        }`}
      >
        {subtitle}
      </p>

    </div>
  );
}

/* ============================================================
   CHAIN ARROW
============================================================ */

function ChainArrow() {
  return (
    <span className="text-slate-600">
      →
    </span>
  );
}

/* ============================================================
   METRIC CARD
============================================================ */

function MetricCard({
  label,
  value,
  description,
  status,
}: {
  label: string;
  value: string;
  description: string;
  status: "good" | "warning";
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950 p-5">

      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
        {label}
      </p>

      <p
        className={`mt-3 text-3xl font-bold ${
          status === "good"
            ? "text-emerald-400"
            : "text-amber-400"
        }`}
      >
        {value}
      </p>

      <p className="mt-2 text-xs text-slate-500">
        {description}
      </p>

    </div>
  );
}

/* ============================================================
   SECURITY REASON
============================================================ */

function getReason(
  action: SecurityAction,
): string {
  switch (action.decision) {

    case "ALLOW":
      return "The requested action is consistent with the active intent, uses an approved data path, and does not violate the current security policy.";

    case "REQUIRE_APPROVAL":
      return "The action accesses sensitive data. The operation may be legitimate, but human approval is required before the data can be used.";

    case "BLOCK":
      return "The action attempts to move sensitive customer data to an untrusted external destination outside the approved purpose boundary.";
  }
}

/* ============================================================
   EVIDENCE
============================================================ */

function getEvidence(action: SecurityAction) {
  return {
    intent:
      "Process customer invoice and prepare payment report",

    policyExplanation:
      action.policy ===
      "PURPOSE_BOUNDARY_VIOLATION"
        ? "The requested destination is outside the purpose approved for the current task."
        : action.policy ===
            "UNTRUSTED_DESTINATION"
          ? "The destination has not been approved as a trusted recipient for this data."
          : action.policy ===
              "SENSITIVE_DATA_REVIEW"
            ? "The data is classified as sensitive and requires additional review."
            : "The action matches the approved purpose and destination policy.",

    enforcementExplanation:
      action.decision === "BLOCK"
        ? "IntentFence prevented the operation from executing."
        : action.decision ===
            "REQUIRE_APPROVAL"
          ? "IntentFence paused the operation until a human reviewer approves it."
          : "IntentFence allowed the operation to continue.",
  };
}

/* ============================================================
   RISK COLOR
============================================================ */

function getRiskColor(
  action: SecurityAction,
): string {
  switch (action.risk) {

    case "LOW":
      return "text-emerald-400";

    case "MEDIUM":
      return "text-amber-400";

    case "HIGH":
      return "text-red-400";
  }
}

/* ============================================================
   RECEIPT HASH
============================================================ */

function generateReceiptHash(
  action: SecurityAction,
): string {
  const value = [
    action.id,
    action.time,
    action.tool,
    action.action,
    action.decision,
    action.data,
    action.destination,
    action.policy,
  ].join("|");

  let hash = 0;

  for (let i = 0; i < value.length; i++) {

    hash =
      (hash << 5) -
      hash +
      value.charCodeAt(i);

    hash |= 0;
  }

  return `IF-${Math.abs(hash)
    .toString(16)
    .padStart(8, "0")
    .toUpperCase()}`;
}