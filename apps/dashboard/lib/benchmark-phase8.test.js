import { expect, test } from "bun:test";
import { readFileSync } from "node:fs";

const apiSource = readFileSync(new URL("./api.ts", import.meta.url), "utf8");
const benchmarkPanelSource = readFileSync(
  new URL("../components/security-console/BenchmarkPanel.tsx", import.meta.url),
  "utf8",
);

test("Phase 8 adds a latest benchmark summary API client", () => {
  expect(apiSource).toContain("fetchLatestBenchmarkSummary");
  expect(apiSource).toContain("/benchmarks/latest");
});

test("Phase 8 benchmark panel renders measured headline metrics", () => {
  expect(benchmarkPanelSource).toContain("Attack Blocking Rate");
  expect(benchmarkPanelSource).toContain("Safe Task Completion Rate");
  expect(benchmarkPanelSource).toContain("False Positive Rate");
});
