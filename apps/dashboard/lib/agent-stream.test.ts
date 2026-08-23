import { expect, test } from "bun:test";

import { AgentStreamParseError, parseSseFrames } from "./agent-stream";

test("fragmented SSE remains buffered until the complete event arrives", () => {
  const first = parseSseFrames(
    'id: 1\nevent: assistant_delta\ndata: {"event":"assistant_delta","sequence":1,"delta":"Hel',
  );
  expect(first.frames).toHaveLength(0);

  const second = parseSseFrames(first.remainder + 'lo"}\n\n');
  expect(second.frames).toEqual([
    {
      id: 1,
      event: "assistant_delta",
      data: { event: "assistant_delta", sequence: 1, delta: "Hello" },
    },
  ]);
  expect(second.remainder).toBe("");
});

test("multiple complete SSE frames are parsed in order", () => {
  const parsed = parseSseFrames(
    'id: 2\nevent: model_status\ndata: {"event":"model_status","sequence":2,"status":"thinking"}\n\n' +
      'id: 3\nevent: assistant_done\ndata: {"event":"assistant_done","sequence":3,"source_count":0,"tool_count":0,"contract":{"session_id":"s","intent_id":"i","previous_intent_id":null,"contract_version":1,"objective":"Research","web_research_enabled":true}}\n\n',
  );

  expect(parsed.frames.map((frame) => [frame.id, frame.event])).toEqual([
    [2, "model_status"],
    [3, "assistant_done"],
  ]);
  expect(parsed.remainder).toBe("");
});

test("malformed SSE JSON fails with a typed parser error", () => {
  expect(() =>
    parseSseFrames("id: 1\nevent: error\ndata: {not-json}\n\n"),
  ).toThrow(AgentStreamParseError);
});

test("a trailing partial frame is preserved byte-for-byte", () => {
  const trailing = "id: 4\nevent: source\ndata: {\"event\":\"source\"";
  const parsed = parseSseFrames(trailing);

  expect(parsed.frames).toEqual([]);
  expect(parsed.remainder).toBe(trailing);
});
