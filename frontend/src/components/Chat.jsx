import { useEffect, useRef, useState } from "react";
import { streamChat } from "../api.js";

/**
 * Renders inline citation markers as highlighted chips. Different models
 * emit citations in different formats regardless of prompt instructions —
 * e.g. plain "[1]" vs. gpt-oss's tool-citation style "【1†L1-L4】" — so this
 * matches either and normalizes both down to a clean "[n]" chip.
 */
function AnswerText({ text }) {
  const citationPattern = /(\[\d+\]|【\d+[^】]*】)/g;
  const parts = text.split(citationPattern);
  return (
    <div className="answer-text">
      {parts.map((part, i) => {
        const match = part.match(/^(?:\[|【)(\d+)/);
        return match ? (
          <span key={i} className="cite">
            [{match[1]}]
          </span>
        ) : (
          <span key={i}>{part}</span>
        );
      })}
    </div>
  );
}

function SourceCards({ sources, open, onToggle }) {
  if (!sources || sources.length === 0) return null;
  return (
    <div className="sources-wrap">
      <button type="button" className="sources-toggle" onClick={onToggle}>
        {open ? "▾" : "▸"} {open ? "Hide sources" : `Show sources (${sources.length})`}
      </button>
      {open && (
        <div className="sources">
          {sources.map((s, i) => (
            <div className="source-card" key={i}>
              <div className="src-head">
                <span>[{i + 1}]</span>
                <span>{s.filename}</span>
                <span>p.{s.page_number}</span>
              </div>
              <div className="src-body">{s.text.slice(0, 220)}{s.text.length > 220 ? "…" : ""}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Chat({ token, activeDocument, documents }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function handleSend(e) {
    e.preventDefault();
    const query = input.trim();
    if (!query || streaming) return;

    setInput("");
    setMessages((prev) => [
      ...prev,
      { role: "user", text: query },
      { role: "assistant", text: "", sources: [] },
    ]);
    setStreaming(true);

    await streamChat(
      token,
      { query, documentId: activeDocument },
      {
        onSources: (sources) => {
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = { ...next[next.length - 1], sources };
            return next;
          });
        },
        onToken: (chunk) => {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            next[next.length - 1] = { ...last, text: last.text + chunk };
            return next;
          });
        },
        onDone: () => setStreaming(false),
        onError: (err) => {
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = {
              ...next[next.length - 1],
              text: `Error: ${err.message}`,
            };
            return next;
          });
          setStreaming(false);
        },
      }
    );
  }

  function toggleSources(index) {
    setMessages((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], sourcesOpen: !next[index].sourcesOpen };
      return next;
    });
  }

  const scopeLabel = activeDocument
    ? documents.find((d) => d.id === activeDocument)?.filename ?? "selected document"
    : "all documents";

  return (
    <div className="chat-panel">
      <div className="chat-scroll" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="chat-empty">
            <h2>Ask your documents anything</h2>
            <p>
              Upload a PDF, then ask a question. Answers are grounded in your documents with
              page-level citations — currently searching <strong>{scopeLabel}</strong>.
            </p>
          </div>
        ) : (
          messages.map((m, i) =>
            m.role === "user" ? (
              <div className="msg user" key={i}>
                {m.text}
              </div>
            ) : (
              <div className="msg assistant" key={i}>
                <AnswerText text={m.text || "…"} />
                <SourceCards
                  sources={m.sources}
                  open={!!m.sourcesOpen}
                  onToggle={() => toggleSources(i)}
                />
              </div>
            )
          )
        )}
      </div>

      <form className="chat-input-row" onSubmit={handleSend}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={`Ask a question about ${scopeLabel}…`}
          disabled={streaming}
        />
        <button type="submit" className="btn-primary" disabled={streaming || !input.trim()}>
          {streaming ? "Thinking…" : "Ask"}
        </button>
      </form>
    </div>
  );
}