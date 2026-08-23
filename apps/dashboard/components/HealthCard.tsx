"use client";

import { useEffect, useState } from "react";

import { getApiBaseUrl } from "@/lib/api";

type HealthState = "checking" | "configured" | "degraded" | "offline";

type Readiness = {
  status: "configured" | "degraded";
  model: string;
};

export function HealthCard() {
  const [state, setState] = useState<HealthState>("checking");
  const [model, setModel] = useState("local model");

  useEffect(() => {
    const controller = new AbortController();

    fetch(`${getApiBaseUrl()}/agent/readiness`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("health check failed");
        }
        const readiness = (await response.json()) as Readiness;
        setModel(readiness.model);
        setState(readiness.status);
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setState("offline");
      });

    return () => controller.abort();
  }, []);

  return (
    <section className="health-card" aria-live="polite">
      <span>Agent runtime</span>
      <strong data-state={state}>{state}</strong>
      <small className="model-chip">{model} · local</small>
    </section>
  );
}
