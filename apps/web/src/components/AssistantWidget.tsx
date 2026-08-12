import { useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { api, type AssistantCitation } from "../api/client";
import { loadTokens } from "../auth/session";
import { Icon } from "./Icon";
import "./assistant-widget.css";

type Message = {
  id: number;
  role: "user" | "assistant";
  text: string;
  citations?: AssistantCitation[];
  model?: string;
};

const suggestions = [
  "How do I publish a dataset?",
  "Explain the current heat analytics workflow.",
  "What does CRAM use for flood monitoring?",
  "How should I interpret climate vulnerability data?",
];

export function AssistantWidget() {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const sequence = useRef(0);
  const hasConversation = messages.length > 0;
  const visibleSuggestions = useMemo(
    () => suggestions.slice(0, hasConversation ? 2 : 4),
    [hasConversation],
  );

  async function ask(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;
    const tokens = loadTokens();
    if (!tokens) {
      setError("Your session is unavailable. Please sign in again.");
      return;
    }
    sequence.current += 1;
    setMessages((items) => [...items, { id: sequence.current, role: "user", text: trimmed }]);
    setQuestion("");
    setError("");
    setLoading(true);
    try {
      const result = await api.askAssistant(tokens.access_token, trimmed, location.pathname);
      sequence.current += 1;
      setMessages((items) => [
        ...items,
        {
          id: sequence.current,
          role: "assistant",
          text: result.answer,
          citations: result.citations,
          model: result.model,
        },
      ]);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "CRAM AI Assistant is temporarily unavailable.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={`assistant-widget${open ? " open" : ""}`}>
      {open && (
        <section className="assistant-panel" aria-label="CRAM AI Assistant">
          <header className="assistant-head">
            <div className="assistant-mark">
              <Icon name="spark" />
            </div>
            <div>
              <strong>CRAM AI Assistant</strong>
              <span>Application guidance + climate intelligence</span>
            </div>
            <button onClick={() => setOpen(false)} aria-label="Close assistant">
              <Icon name="close" />
            </button>
          </header>
          <div className="assistant-trust">
            <Icon name="shield" /> Answers are grounded in CRAM context and
            approved/public-reference sources where available.
          </div>
          <div className="assistant-messages">
            {!hasConversation && (
              <div className="assistant-welcome">
                <h3>How can I help?</h3>
                <p>
                  Ask how to use CRAM, interpret a module, or understand climate-risk concepts and
                  live reference data.
                </p>
              </div>
            )}
            {messages.map((message) => (
              <article key={message.id} className={`assistant-message ${message.role}`}>
                <div className="assistant-bubble">{message.text}</div>
                {message.role === "assistant" &&
                  message.citations &&
                  message.citations.length > 0 && (
                    <details className="assistant-sources">
                      <summary>Sources used ({message.citations.length})</summary>
                      <div>
                        {message.citations.map((source) =>
                          source.url ? (
                            <a
                              key={`${message.id}-${source.label}`}
                              href={source.url}
                              target="_blank"
                              rel="noreferrer"
                            >
                              <strong>[{source.label}]</strong> {source.title}
                              <span>{source.source_type}</span>
                            </a>
                          ) : (
                            <p key={`${message.id}-${source.label}`}>
                              <strong>[{source.label}]</strong> {source.title}
                              <span>{source.source_type}</span>
                            </p>
                          ),
                        )}
                      </div>
                    </details>
                  )}
                {message.model && (
                  <small className="assistant-model">AI response • {message.model}</small>
                )}
              </article>
            ))}
            {loading && (
              <div className="assistant-thinking">
                <i />
                <i />
                <i />
                <span>Reviewing CRAM context…</span>
              </div>
            )}
          </div>
          <div className="assistant-suggestions">
            {visibleSuggestions.map((item) => (
              <button key={item} onClick={() => void ask(item)}>
                {item}
              </button>
            ))}
          </div>
          {error && <div className="assistant-error">{error}</div>}
          <form
            className="assistant-compose"
            onSubmit={(event) => {
              event.preventDefault();
              void ask(question);
            }}
          >
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask CRAM or a climate-risk question…"
              rows={2}
            />
            <button
              type="submit"
              disabled={loading || question.trim().length < 2}
              aria-label="Send question"
            >
              <Icon name="arrow" />
            </button>
          </form>
          <footer>
            AI responses support decision-making; governed methodologies and official agency data
            remain authoritative.
          </footer>
        </section>
      )}
      <button
        className="assistant-launcher"
        onClick={() => setOpen((value) => !value)}
        aria-label="Open CRAM AI Assistant"
      >
        <Icon name={open ? "close" : "spark"} />
        {!open && <span>Ask CRAM</span>}
      </button>
    </div>
  );
}
