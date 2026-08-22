"use client";

import { useState } from "react";

import {
  fetchHotelAttackDemo,
  type HotelAttackComparison,
  type HotelAttackRun,
} from "@/lib/api";

type DemoState = "idle" | "loading" | "success" | "error";

function ResultPanel({ title, label, tone, run }: {
  title: string;
  label: string;
  tone: "danger" | "safe";
  run?: HotelAttackRun;
}) {
  const protectedMode = tone === "safe";
  const outcomes = [
    {
      label: "Secret file read",
      value: run ? (run.secret_read_executed ? "Executed" : "Blocked") : protectedMode ? "Blocked" : "Executes",
      good: run ? !run.secret_read_executed : protectedMode,
    },
    {
      label: "Data exfiltration",
      value: run ? (run.exfiltration_executed ? "Executed" : "Blocked") : protectedMode ? "Blocked" : "Executes",
      good: run ? !run.exfiltration_executed : protectedMode,
    },
    {
      label: "Legitimate workflow",
      value: run ? (run.legitimate_workflow_completed ? "Completed" : "Interrupted") : "Completes",
      good: run ? run.legitimate_workflow_completed : true,
    },
  ];

  return (
    <article className="result-panel" data-tone={tone}>
      <p className="panel-label">{label}</p>
      <h3>{title}</h3>
      <div className="outcome-list">
        {outcomes.map((outcome) => (
          <div className="outcome-row" key={outcome.label}>
            <span>{outcome.label}</span>
            <strong data-good={outcome.good}>
              <span aria-hidden="true">{outcome.good ? "✓" : "×"}</span>
              {outcome.value}
            </strong>
          </div>
        ))}
      </div>
    </article>
  );
}

export function DemoComparison() {
  const [comparison, setComparison] = useState<HotelAttackComparison>();
  const [state, setState] = useState<DemoState>("idle");

  async function runDemo() {
    setState("loading");
    try {
      setComparison(await fetchHotelAttackDemo());
      setState("success");
    } catch {
      setState("error");
    }
  }

  const timeline = comparison?.enabled.tool_sequence.map((tool, index) => ({
    tool,
    disabled: comparison.disabled.decisions[index],
    enabled: comparison.enabled.decisions[index],
  }));

  return (
    <section className="demo-section" aria-labelledby="demo-title">
      <div className="demo-heading">
        <div>
          <p className="section-kicker">Controlled attack simulation</p>
          <h2 id="demo-title">See the policy boundary in action.</h2>
          <p>
            A hotel page hides instructions to steal a local secret and send it to an unknown
            destination. The agent still needs to finish its legitimate comparison report.
          </p>
        </div>
        <button className="run-button" type="button" onClick={runDemo} disabled={state === "loading"}>
          <span className="run-dot" aria-hidden="true" />
          {state === "loading" ? "Running simulation…" : state === "success" ? "Run simulation again" : "Run attack simulation"}
        </button>
      </div>

      {state === "error" ? (
        <p className="demo-error" role="alert">
          The simulation could not reach the Runtime API. Confirm that localhost:8000 is running.
        </p>
      ) : null}

      <div className="comparison-grid">
        <ResultPanel label="Baseline agent" title="Without IntentFence" tone="danger" run={comparison?.disabled} />
        <ResultPanel label="Runtime protected" title="With IntentFence" tone="safe" run={comparison?.enabled} />
      </div>

      {timeline ? (
        <div className="decision-trace" aria-live="polite">
          <div className="trace-heading">
            <div>
              <p className="section-kicker">Authoritative decision trace</p>
              <h3>Same task. Same actions. Different outcome.</h3>
            </div>
            <span className="scenario-id">{comparison?.scenario_id}</span>
          </div>
          <div className="trace-table" role="table" aria-label="Tool decision comparison">
            <div className="trace-row trace-header" role="row">
              <span role="columnheader">Tool request</span>
              <span role="columnheader">Disabled</span>
              <span role="columnheader">Enabled</span>
            </div>
            {timeline.map((step, index) => (
              <div className="trace-row" role="row" key={`${step.tool}-${index}`}>
                <span className="tool-name" role="cell">
                  <small>{String(index + 1).padStart(2, "0")}</small>
                  {step.tool.replaceAll("_", " ")}
                </span>
                <strong className="decision" data-decision={step.disabled} role="cell">{step.disabled}</strong>
                <strong className="decision" data-decision={step.enabled} role="cell">{step.enabled}</strong>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <p className="demo-hint">Run the simulation to reveal the five intercepted tool decisions.</p>
      )}
    </section>
  );
}
