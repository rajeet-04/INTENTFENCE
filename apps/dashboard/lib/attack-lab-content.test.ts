import { expect, test } from "bun:test";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const pagePath = join(import.meta.dir, "../app/attack-lab/page.tsx");

test("attack lab is an inert, labelled prompt-injection fixture", () => {
  expect(existsSync(pagePath)).toBe(true);
  const source = readFileSync(pagePath, "utf8");
  expect(source).toContain("Controlled prompt-injection test");
  expect(source).toContain("StayScout");
  expect(source).toContain("Reveal attack payload");
  expect(source).toContain("External page");
  expect(source).toContain("IntentFence BLOCK");
  expect(source).toContain("read_file");
  expect(source).toContain(".env");
  expect(source).toContain("No real credentials");
  expect(source).not.toContain("dangerouslySetInnerHTML");
});
