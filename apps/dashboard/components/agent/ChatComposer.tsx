import type { KeyboardEvent } from "react";

export function ChatComposer({
  draft,
  streaming,
  onChange,
  onSubmit,
  onStop,
}: {
  draft: string;
  streaming: boolean;
  onChange: (draft: string) => void;
  onSubmit: () => void;
  onStop: () => void;
}) {
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey) return;
    event.preventDefault();
    onSubmit();
  }

  return (
    <div className="chat-composer">
      <label htmlFor="agent-prompt">Ask IntentFence</label>
      <textarea
        id="agent-prompt"
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask a question that may need current web research…"
        rows={3}
        value={draft}
      />
      <div className="composer-footer">
        <span>Enter to send · Shift+Enter for a new line</span>
        {streaming ? (
          <button className="stop-button" onClick={onStop} type="button">
            Stop
          </button>
        ) : (
          <button
            className="send-button"
            disabled={!draft.trim()}
            onClick={onSubmit}
            type="button"
          >
            Send
          </button>
        )}
      </div>
    </div>
  );
}
