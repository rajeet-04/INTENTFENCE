import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

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
        <div className="message-heading">
          <p className="message-role">{message.role === "assistant" ? "IntentFence" : "You"}</p>
          {message.role === "assistant" && message.provider && message.routeReason ? (
            <span className="provider-badge">
              {capitalize(message.provider)} · {message.routeReason}
            </span>
          ) : null}
        </div>
        {message.activities.length ? (
          <div className="tool-activity-list" aria-label="IntentFence activity">
            {message.activities.map((activity) => (
              <ToolActivity activity={activity} key={activity.id} />
            ))}
          </div>
        ) : null}
        {message.content ? (
          <div className="message-content">
            {message.role === "assistant" ? (
              <ReactMarkdown
                components={{
                  a: ({ children, ...props }) => (
                    <a {...props} rel="noreferrer noopener" target="_blank">
                      {children}
                    </a>
                  ),
                }}
                remarkPlugins={[remarkGfm]}
              >
                {message.content}
              </ReactMarkdown>
            ) : message.content}
          </div>
        ) : null}
        {message.status === "streaming" && !message.content ? (
          <p className="thinking-label">Authorizing the next step…</p>
        ) : null}
        <SourceCards sources={message.sources} />
      </div>
    </article>
  );
}

function capitalize(value: string) {
  return value[0].toUpperCase() + value.slice(1);
}
