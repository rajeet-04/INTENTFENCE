"use client";

import { useEffect, useState } from "react";

import { getApiBaseUrl } from "@/lib/api";

type HealthState = "checking" | "online" | "offline";

export function HealthCard() {
  const [state, setState] = useState<HealthState>("checking");

  useEffect(() => {
    const controller = new AbortController();

    fetch(`${getApiBaseUrl()}/health`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) {
          throw new Error("health check failed");
        }
        setState("online");
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
      <span>Runtime API</span>
      <strong data-state={state}>{state}</strong>
    </section>
  );
}
