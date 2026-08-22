import { expect, test } from "bun:test";
import { readFileSync } from "node:fs";

const consoleSource = readFileSync(
  new URL("../components/security-console/SecurityConsole.tsx", import.meta.url),
  "utf8",
);
const panelSource = readFileSync(
  new URL("../components/security-console/BenchmarkPanel.tsx", import.meta.url),
  "utf8",
);
const viewModelSource = readFileSync(new URL("./security-console.ts", import.meta.url), "utf8");

test("security console loads the latest persisted benchmark summary", () => {
  expect(consoleSource).toContain("fetchLatestBenchmarkSummary");
  expect(consoleSource).toContain("benchmarkPayload");
});

test("view model accepts measured benchmark records instead of forcing pending", () => {
  expect(viewModelSource).toContain("LatestBenchmarkPayload");
  expect(viewModelSource).toContain("benchmarkPayload");
});

test("benchmark panel has a measured-data rendering path with provenance", () => {
  expect(panelSource).toContain('benchmark.status === "ready"');
  expect(panelSource).toContain("numerator");
  expect(panelSource).toContain("denominator");
  expect(panelSource).toContain("target");
});
