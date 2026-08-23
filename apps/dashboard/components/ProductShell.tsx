"use client";

import { useState } from "react";

import {
  AgentConsole,
  type AgentStreamFunction,
} from "@/components/agent/AgentConsole";
import { SecurityConsole } from "@/components/security-console/SecurityConsole";
import {
  initialAgentConversationState,
  type AgentConversationState,
} from "@/lib/agent-state";

export function ProductShell({ stream }: { stream?: AgentStreamFunction }) {
  const [view, setView] = useState<"agent" | "evidence">("agent");
  const [evidence, setEvidence] = useState<AgentConversationState>(
    initialAgentConversationState,
  );
  return (
    <div className="product-shell">
      <nav className="product-nav" aria-label="IntentFence product views">
        <a className="product-wordmark" href="#top" aria-label="IntentFence home">
          <span>IF</span> IntentFence
        </a>
        <div className="view-switcher">
          <button
            aria-pressed={view === "agent"}
            onClick={() => setView("agent")}
            type="button"
          >
            Agent
          </button>
          <button
            aria-pressed={view === "evidence"}
            onClick={() => setView("evidence")}
            type="button"
          >
            Evidence
          </button>
        </div>
        <span className="protection-state"><i /> Gateway protected</span>
      </nav>
      <div id="top" hidden={view !== "agent"}>
        <AgentConsole onStateChange={setEvidence} stream={stream} />
      </div>
      <div hidden={view !== "evidence"}>
        <section className="evidence-intro">
          <p>Authoritative release evidence</p>
          <h1>Measured security performance</h1>
          <span>Controlled attack · receipts · benchmark provenance</span>
        </section>
        <SecurityConsole state={evidence} />
      </div>
    </div>
  );
}
