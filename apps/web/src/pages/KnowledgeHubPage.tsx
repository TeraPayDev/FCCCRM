import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { api, roadmapApi } from "../api/client";
import { loadTokens } from "../auth/session";
import { Icon } from "../components/Icon";
import { MetricTile } from "../components/analytics/Charts";
import { ModuleShell } from "../components/ModuleShell";
import "./knowledge.css";

type Row = Record<string, unknown>;
function text(r: Row, k: string) {
  const v = r[k];
  return v == null ? "—" : Array.isArray(v) ? v.join(", ") : String(v);
}
export function KnowledgeHubPage() {
  const [internal, setInternal] = useState<Row[]>([]);
  const [external, setExternal] = useState<Row[]>([]);
  const [canManage, setCanManage] = useState(false);
  const [query, setQuery] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [url, setUrl] = useState("");
  const [type, setType] = useState("GUIDANCE");
  const [message, setMessage] = useState("");
  const load = async () => {
    const t = loadTokens();
    if (!t) return;
    const [a, b, c] = await Promise.allSettled([
      roadmapApi.list(t.access_token, "/api/v1/knowledge"),
      roadmapApi.object(t.access_token, "/api/v1/public-data/knowledge/world-bank"),
      api.me(t.access_token),
    ]);
    if (a.status === "fulfilled") setInternal(a.value);
    if (b.status === "fulfilled") {
      const v = b.value.records;
      setExternal(
        Array.isArray(v) ? v.filter((x): x is Row => Boolean(x && typeof x === "object")) : [],
      );
    }
    if (c.status === "fulfilled") setCanManage(c.value.permissions.includes("reports.manage"));
  };
  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, []);
  const visible = useMemo(
    () =>
      [
        ...internal.map((r) => ({ ...r, _origin: "CRAM" })),
        ...external.map((r) => ({ ...r, _origin: "World Bank API" })),
      ].filter(
        (r) =>
          !query ||
          `${text(r, "title")} ${text(r, "summary")} ${text(r, "tags")} ${text(r, "organisation")}`
            .toLowerCase()
            .includes(query.toLowerCase()),
      ),
    [internal, external, query],
  );
  async function add(e: FormEvent) {
    e.preventDefault();
    const t = loadTokens();
    if (!t) return;
    try {
      await roadmapApi.post(t.access_token, "/api/v1/knowledge", {
        title,
        content_type: type,
        visibility: "RESTRICTED",
        summary,
        file_reference: url || null,
        tags: ["climate risk", "CRAM"],
      });
      setTitle("");
      setSummary("");
      setUrl("");
      setShowForm(false);
      setMessage("Knowledge item added to the governed CRAM repository.");
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to add knowledge item.");
    }
  }
  async function saveExternal(r: Row) {
    const t = loadTokens();
    if (!t) return;
    try {
      await roadmapApi.post(t.access_token, "/api/v1/knowledge", {
        title: text(r, "title"),
        content_type: "EXTERNAL_PUBLICATION",
        visibility: "RESTRICTED",
        summary: `External reference from ${text(r, "organisation")}. ${text(r, "authors") !== "—" ? `Authors: ${text(r, "authors")}` : ""}`,
        file_reference: text(r, "url") !== "—" ? text(r, "url") : null,
        tags: ["climate risk", "World Bank", "public reference"],
      });
      setMessage("External resource saved into the governed Knowledge Hub.");
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to save resource.");
    }
  }
  return (
    <ModuleShell
      title="Knowledge Hub"
      subtitle="A searchable institutional repository for methods, policies, climate studies, reports and authoritative public references."
      eyebrow="Institutional memory"
    >
      <div className="metric-row">
        <MetricTile label="Governed items" value={internal.length} hint="Stored in CRAM" />
        <MetricTile
          label="Live resources"
          value={external.length}
          hint="World Bank Documents & Reports API"
          tone="good"
        />
        <MetricTile
          label="Sources"
          value={external.length ? 2 : 1}
          hint="CRAM + public knowledge feeds"
        />
        <MetricTile label="Search" value={visible.length} hint="Items matching current view" />
      </div>
      <section className="knowledge-toolbar">
        <label className="search-field">
          <Icon name="search" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search climate risk, flood, heat, resilience, policy…"
          />
        </label>
        {canManage && (
          <button className="icon-button" onClick={() => setShowForm((v) => !v)}>
            <Icon name={showForm ? "close" : "plus"} />
            {showForm ? "Close" : "Add knowledge item"}
          </button>
        )}
        <button className="secondary-action icon-button" onClick={() => void load()}>
          <Icon name="refresh" /> Refresh public resources
        </button>
      </section>
      {message && <div className="module-message success">{message}</div>}
      {showForm && (
        <form className="knowledge-form" onSubmit={add}>
          <div>
            <h2>Add governed knowledge</h2>
            <p>
              Register an FCC or partner resource without exposing secrets or bypassing governance.
            </p>
          </div>
          <label>
            Title
            <input required value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label>
            Type
            <select value={type} onChange={(e) => setType(e.target.value)}>
              <option>GUIDANCE</option>
              <option>METHODOLOGY</option>
              <option>POLICY</option>
              <option>CLIMATE_STUDY</option>
              <option>DATASET_DOCUMENTATION</option>
              <option>REPORT</option>
            </select>
          </label>
          <label className="wide">
            Summary
            <textarea required value={summary} onChange={(e) => setSummary(e.target.value)} />
          </label>
          <label className="wide">
            File or external URL
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://… or approved object reference"
            />
          </label>
          <button className="icon-button">
            <Icon name="check" /> Save knowledge item
          </button>
        </form>
      )}
      <div className="section-heading">
        <div>
          <h2>Climate risk resource library</h2>
          <p>Governed CRAM items and live public references are clearly distinguished.</p>
        </div>
      </div>
      <section className="knowledge-grid">
        {visible.map((r, i) => (
          <article
            className="knowledge-card"
            key={`${text(r, "id")}-${text(r, "external_id")}-${i}`}
          >
            <div className="knowledge-card-top">
              <span
                className={`source-pill ${text(r, "_origin") === "CRAM" ? "governed" : "external"}`}
              >
                {text(r, "_origin")}
              </span>
              <span>
                {text(r, "content_type") !== "—"
                  ? text(r, "content_type")
                  : text(r, "resource_type")}
              </span>
            </div>
            <h3>{text(r, "title")}</h3>
            <p>
              {text(r, "summary") !== "—"
                ? text(r, "summary")
                : text(r, "authors") !== "—"
                  ? `By ${text(r, "authors")}`
                  : "Public climate-risk resource."}
            </p>
            <div className="knowledge-meta">
              <span>
                <Icon name="organisation" />
                {text(r, "organisation") !== "—" ? text(r, "organisation") : "CRAM repository"}
              </span>
              {text(r, "publication_date") !== "—" && (
                <span>
                  <Icon name="calendar" />
                  {text(r, "publication_date")}
                </span>
              )}
            </div>
            <div className="knowledge-actions">
              {text(r, "url") !== "—" && (
                <a
                  className="button secondary-button icon-button"
                  href={text(r, "url")}
                  target="_blank"
                  rel="noreferrer"
                >
                  <Icon name="external" /> Open source
                </a>
              )}
              {canManage && text(r, "_origin") !== "CRAM" && (
                <button
                  className="secondary-action icon-button"
                  onClick={() => void saveExternal(r)}
                >
                  <Icon name="plus" /> Save to CRAM
                </button>
              )}
            </div>
          </article>
        ))}
        {!visible.length && (
          <div className="empty-state-rich">
            <div className="empty-icon">
              <Icon name="knowledge" />
            </div>
            <h2>No resources found</h2>
            <p>Try a broader search or refresh the public-resource feed.</p>
          </div>
        )}
      </section>
    </ModuleShell>
  );
}
