import type { CitationSource } from "@/lib/agent-api";

export function SourceCards({ sources }: { sources: CitationSource[] }) {
  if (!sources.length) return null;
  return (
    <div className="source-cards" aria-label="Authoritative sources">
      {sources.map((source, index) => (
        <a
          aria-label={source.title}
          href={source.url}
          key={source.url}
          rel="noreferrer noopener"
          target="_blank"
        >
          <span>{index + 1}</span>
          <div>
            <strong>{source.title}</strong>
            {source.snippet ? <small>{source.snippet}</small> : null}
          </div>
          <b aria-hidden="true">↗</b>
        </a>
      ))}
    </div>
  );
}
