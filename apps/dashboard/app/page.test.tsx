import { expect, test } from "bun:test";
import { renderToStaticMarkup } from "react-dom/server";

import Home from "./page";

test("renders the Agent and Evidence product shell with source-backed evidence", () => {
  const markup = renderToStaticMarkup(<Home />);

  expect(markup).toContain("Agent");
  expect(markup).toContain("Evidence");
  expect(markup).toContain("Ask IntentFence");
  expect(markup).toContain("Web research");
  expect(markup).toContain("Run live injection test");
  expect(markup).toContain("/attack-lab");
  expect(markup).toContain("No agent evidence yet");
  expect(markup).not.toContain("See the policy boundary in action");
  expect(markup).not.toContain("Without IntentFence");
});
