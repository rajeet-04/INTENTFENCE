import { expect, test } from "bun:test";
import { renderToStaticMarkup } from "react-dom/server";

import Home from "./page";

test("renders an attack comparison call to action for the judge demo", () => {
  const markup = renderToStaticMarkup(<Home />);

  expect(markup).toContain("Run attack simulation");
  expect(markup).toContain("Without IntentFence");
  expect(markup).toContain("With IntentFence");
});
