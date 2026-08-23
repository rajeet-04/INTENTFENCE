import type { ConversationMessage } from "@/lib/agent-state";

import { SourceCards } from "./SourceCards";
import { ToolActivity } from "./ToolActivity";

export function ChatMessage({ message }: { message: ConversationMessage }) {
  return (
    <article className="chat-message" data-role={message.role} data-status={message.status}>
      <div className="message-avatar" aria-hidden="true">
        {message.role === "assistant" ? "IF" : "You"}
      </div>
      <div className="message-body">
        <p className="message-role">{message.role === "assistant" ? "IntentFence" : "You"}</p>
        {message.activities.length ? (
          <div className="tool-activity-list" aria-label="IntentFence activity">
            {message.activities.map((activity) => (
              <ToolActivity activity={activity} key={activity.id} />
            ))}
          </div>
        ) : null}
        {message.content ? <div className="message-content">{message.content}</div> : null}
        {message.status === "streaming" && !message.content ? (
          <p className="thinking-label">Authorizing the next step…</p>
        ) : null}
        <SourceCards sources={message.sources} />
      </div>
    </article>
  );
}
