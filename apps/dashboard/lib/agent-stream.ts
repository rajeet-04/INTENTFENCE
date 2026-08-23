import type { AgentStreamEvent } from "./agent-api";

export type ParsedSseFrame = {
  id: number;
  event: AgentStreamEvent["event"];
  data: AgentStreamEvent;
};

export class AgentStreamParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AgentStreamParseError";
  }
}

export function parseSseFrames(buffer: string): {
  frames: ParsedSseFrame[];
  remainder: string;
} {
  const frames: ParsedSseFrame[] = [];
  let remainder = buffer;
  while (true) {
    const boundary = remainder.indexOf("\n\n");
    if (boundary < 0) break;
    const block = remainder.slice(0, boundary);
    remainder = remainder.slice(boundary + 2);
    if (!block.trim()) continue;
    frames.push(parseFrame(block));
  }
  return { frames, remainder };
}

function parseFrame(block: string): ParsedSseFrame {
  let id: number | null = null;
  let event: string | null = null;
  let dataText: string | null = null;
  for (const line of block.split("\n")) {
    if (line.startsWith("id: ")) id = Number(line.slice(4));
    else if (line.startsWith("event: ")) event = line.slice(7);
    else if (line.startsWith("data: ")) dataText = line.slice(6);
  }
  if (!Number.isInteger(id) || id === null || id < 1 || !event || dataText === null) {
    throw new AgentStreamParseError("Agent stream frame is missing required fields.");
  }
  let data: unknown;
  try {
    data = JSON.parse(dataText);
  } catch {
    throw new AgentStreamParseError("Agent stream contained malformed JSON.");
  }
  if (
    typeof data !== "object" ||
    data === null ||
    !("event" in data) ||
    !("sequence" in data) ||
    data.event !== event ||
    data.sequence !== id
  ) {
    throw new AgentStreamParseError("Agent stream event metadata did not match its payload.");
  }
  return {
    id,
    event: event as AgentStreamEvent["event"],
    data: data as AgentStreamEvent,
  };
}
