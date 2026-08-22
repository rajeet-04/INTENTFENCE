import { expect, test } from "bun:test";
import { readFileSync } from "node:fs";

const workflowSource = readFileSync(
  new URL("../../../.github/workflows/ci.yml", import.meta.url),
  "utf8",
);

test("Phase 8 fabricated-headline gate does not depend on unavailable ripgrep", () => {
  expect(workflowSource).not.toContain('rg -n "96\\.4%|98\\.1%|1\\.7%"');
  expect(workflowSource).toContain("grep -R");
});
