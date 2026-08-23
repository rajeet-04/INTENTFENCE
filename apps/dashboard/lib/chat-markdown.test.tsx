import { expect, test } from "bun:test";
import { render, screen } from "@testing-library/react";

import { ChatMessage } from "@/components/agent/ChatMessage";
import type { ConversationMessage } from "@/lib/agent-state";

test("assistant responses render safe GitHub-flavored Markdown", () => {
  const message: ConversationMessage = {
    id: "assistant-markdown",
    role: "assistant",
    content: [
      "## Security result",
      "",
      "IntentFence **blocked** the call with `Executed: No`.",
      "",
      "| Tool | Decision |",
      "| --- | --- |",
      "| read_file | BLOCK |",
      "",
      "[Evidence](https://example.com/evidence)",
      "",
      "<script>window.compromised = true</script>",
    ].join("\n"),
    status: "complete",
    sources: [],
    activities: [],
    provider: "cloud",
    routeReason: "explicit",
  };

  const { container } = render(<ChatMessage message={message} />);

  expect(screen.getByRole("heading", { level: 2, name: "Security result" })).toBeTruthy();
  expect(screen.getByText("blocked").tagName).toBe("STRONG");
  expect(screen.getByRole("table")).toBeTruthy();
  const link = screen.getByRole("link", { name: "Evidence" });
  expect(link.getAttribute("target")).toBe("_blank");
  expect(link.getAttribute("rel")).toBe("noreferrer noopener");
  expect(container.querySelector("script")).toBeNull();
});

test("user prompts remain literal text instead of rendered Markdown", () => {
  const message: ConversationMessage = {
    id: "user-markdown",
    role: "user",
    content: "## Keep this literal",
    status: "complete",
    sources: [],
    activities: [],
    provider: null,
    routeReason: null,
  };

  render(<ChatMessage message={message} />);

  expect(screen.queryByRole("heading", { name: "Keep this literal" })).toBeNull();
  expect(screen.getByText("## Keep this literal")).toBeTruthy();
});
