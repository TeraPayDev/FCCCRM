import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { api, roadmapApi } from "../api/client";
import { loadTokens } from "../auth/session";
import { Icon } from "../components/Icon";
import { MetricTile } from "../components/analytics/Charts";
import { ModuleShell } from "../components/ModuleShell";
import "./knowledge.css";

type Row = Record<string, unknown>;
type ViewMode = "all" | "governed" | "public";

function text(row: Row, key: string) {
  const value = row[key];
  if (value == null) return "—";
  return Array.isArray(value) ? value.join(", ") : String(value);
}

function rowSearchText(row: Row) {
  return `${text(row, "title")} ${text(row, "summary")} ${text(row, "tags")} ${text(row, "organisation")} ${text(row, "resource_type")} ${text(row, "content_type")}`.toLowerCase();
}

export function KnowledgeHubPage() {
  const [internal, setInternal] = useState<Row[]>([]);
  const [external, setExternal] = useState<Row[]>([]);
  const [canManage, setCanManage] = useState(false);
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<ViewMode>("all");
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [url, setUrl] = useState("");
  const [type, setType] = useState("GUIDANCE");
  const [tags, setTags] = useState("climate risk, CRAM");
  const [message, setMessage] = useState("");
  const [publicStatus, setPublicStatus] = useState("Loading authoritative public resources…");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const tokens = loadTokens();
    if (!tokens) return;
    setLoading(true);
    setMessage("");
    const [governed, publicResources, currentUser] = await Promise.allSettled([
      roadmapApi.list(tokens.access_token, "/api/v1/knowledge"),
      roadmapApi.object(tokens.access_token, "/api/v1/public-data/knowledge/world-bank"),
      api.me(tokens.access_token),
    ]);

    if (governed.status === "fulfilled") {
      setInternal(governed.value);
    } else {
      setMessage(
        "Governed knowledge could not be loaded. Check API connectivity and your report permissions.",
      );
    }

    if (publicResources.status === "fulfilled") {
      const records = publicResources.value.records;
      const rows = Array.isArray(records)
        ? records.filter((value): value is Row => Boolean(value && typeof value === "object"))
        : [];
      setExternal(rows);
      const errors = publicResources.value.errors;
      if (rows.length > 0) {
        setPublicStatus(
          Array.isArray(errors) && errors.length > 0
            ? `${rows.length} authoritative resources available; one or more live feeds reported a warning.`
            : `${rows.length} authoritative public climate resources available.`,
        );
      } else {
        setPublicStatus(
          "The public-resource feed returned no records. Try Refresh public resources.",
        );
      }
    } else {
      setExternal([]);
      setPublicStatus("Public climate-resource feeds are temporarily unavailable.");
    }

    if (currentUser.status === "fulfilled") {
      setCanManage(currentUser.value.permissions.includes("reports.manage"));
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const allRows = useMemo(
    () => [
      ...internal.map((row) => ({ ...row, _origin: "CRAM" })),
      ...external.map((row) => ({ ...row, _origin: text(row, "source") || "Public source" })),
    ],
    [internal, external],
  );

  const visible = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return allRows.filter((row) => {
      const origin = text(row, "_origin");
      if (mode === "governed" && origin !== "CRAM") return false;
      if (mode === "public" && origin === "CRAM") return false;
      return !normalized || rowSearchText(row).includes(normalized);
    });
  }, [allRows, mode, query]);

  async function add(event: FormEvent) {
    event.preventDefault();
    const tokens = loadTokens();
    if (!tokens) return;
    try {
      await roadmapApi.post(tokens.access_token, "/api/v1/knowledge", {
        title,
        content_type: type,
        visibility: "RESTRICTED",
        summary,
        file_reference: url || null,
        tags: tags
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean),
      });
      setTitle("");
      setSummary("");
      setUrl("");
      setTags("climate risk, CRAM");
      setShowForm(false);
      setMessage("Knowledge item added to the governed CRAM repository.");
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to add knowledge item.");
    }
  }

  async function saveExternal(row: Row) {
    const tokens = loadTokens();
    if (!tokens) return;
    try {
      const rowTags = row.tags;
      await roadmapApi.post(tokens.access_token, "/api/v1/knowledge", {
        title: text(row, "title"),
        content_type: "EXTERNAL_PUBLICATION",
        visibility: "RESTRICTED",
        summary: `External reference from ${text(row, "organisation")}. ${text(row, "authors") !== "—" ? `Authors: ${text(row, "authors")}` : ""}`,
        file_reference: text(row, "url") !== "—" ? text(row, "url") : null,
        tags: Array.isArray(rowTags) ? rowTags.map(String) : ["climate risk", "public reference"],
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
          label="Public resources"
          value={external.length}
          hint="Authoritative climate references"
          tone="good"
        />
        <MetricTile
          label="Sources"
          value={external.length ? 5 : 1}
          hint="CRAM + external official sources"
        />
        <MetricTile label="Current view" value={visible.length} hint="Resources matching filters" />
      </div>

      <section className="knowledge-source-banner">
        <span className={`knowledge-source-dot${external.length ? " online" : ""}`} />
        <div>
          <strong>Public knowledge feed</strong>
          <span>{publicStatus}</span>
        </div>
        <button
          className="secondary-action icon-button"
          onClick={() => void load()}
          disabled={loading}
        >
          <Icon name="refresh" /> {loading ? "Refreshing…" : "Refresh public resources"}
        </button>
      </section>

      <section className="knowledge-toolbar">
        <label className="search-field">
          <Icon name="search" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search climate risk, flood, heat, resilience, policy…"
          />
        </label>
        {canManage && (
          <button className="icon-button" onClick={() => setShowForm((value) => !value)}>
            <Icon name={showForm ? "close" : "plus"} />
            {showForm ? "Close" : "Add knowledge item"}
          </button>
        )}
      </section>

      <div className="knowledge-tabs" role="tablist" aria-label="Knowledge resource type">
        <button className={mode === "all" ? "active" : ""} onClick={() => setMode("all")}>
          All resources <span>{allRows.length}</span>
        </button>
        <button className={mode === "governed" ? "active" : ""} onClick={() => setMode("governed")}>
          Governed CRAM <span>{internal.length}</span>
        </button>
        <button className={mode === "public" ? "active" : ""} onClick={() => setMode("public")}>
          Public references <span>{external.length}</span>
        </button>
      </div>

      {message && <div className="module-message success">{message}</div>}

      {showForm && (
        <form className="knowledge-form" onSubmit={add}>
          <div>
            <h2>Add governed knowledge</h2>
            <p>
              Register an FCC or partner resource. External URLs are references only; secrets must
              never be entered here.
            </p>
          </div>
          <label>
            Title
            <input required value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>
          <label>
            Type
            <select value={type} onChange={(event) => setType(event.target.value)}>
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
            <textarea
              required
              value={summary}
              onChange={(event) => setSummary(event.target.value)}
            />
          </label>
          <label>
            Tags
            <input
              value={tags}
              onChange={(event) => setTags(event.target.value)}
              placeholder="climate risk, flood, policy"
            />
          </label>
          <label>
            File or external URL
            <input
              value={url}
              onChange={(event) => setUrl(event.target.value)}
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
          <p>Governed CRAM items and public references remain clearly distinguished.</p>
        </div>
      </div>
      <section className="knowledge-grid">
        {visible.map((row, index) => {
          const governed = text(row, "_origin") === "CRAM";
          const source = governed
            ? "CRAM governed repository"
            : text(row, "source") !== "—"
              ? text(row, "source")
              : text(row, "_origin");
          return (
            <article
              className="knowledge-card"
              key={`${text(row, "id")}-${text(row, "external_id")}-${index}`}
            >
              <div className="knowledge-card-top">
                <span className={`source-pill ${governed ? "governed" : "external"}`}>
                  {governed ? "Governed" : "Public reference"}
                </span>
                <span>
                  {text(row, "content_type") !== "—"
                    ? text(row, "content_type")
                    : text(row, "resource_type")}
                </span>
              </div>
              <h3>{text(row, "title")}</h3>
              <p>
                {text(row, "summary") !== "—"
                  ? text(row, "summary")
                  : text(row, "authors") !== "—"
                    ? `By ${text(row, "authors")}`
                    : "Authoritative climate-risk reference resource."}
              </p>
              <div className="knowledge-meta">
                <span>
                  <Icon name="organisation" />
                  {text(row, "organisation") !== "—"
                    ? text(row, "organisation")
                    : "CRAM repository"}
                </span>
                {text(row, "publication_date") !== "—" && (
                  <span>
                    <Icon name="calendar" />
                    {text(row, "publication_date")}
                  </span>
                )}
              </div>
              <div className="knowledge-source-line">
                <Icon name="info" /> {source}
              </div>
              <div className="knowledge-actions">
                {text(row, "url") !== "—" && (
                  <a
                    className="button secondary-button icon-button"
                    href={text(row, "url")}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <Icon name="external" /> Open source
                  </a>
                )}
                {canManage && !governed && (
                  <button
                    className="secondary-action icon-button"
                    onClick={() => void saveExternal(row)}
                  >
                    <Icon name="plus" /> Save to CRAM
                  </button>
                )}
              </div>
            </article>
          );
        })}
        {!visible.length && (
          <div className="empty-state-rich">
            <div className="empty-icon">
              <Icon name="knowledge" />
            </div>
            <h2>{loading ? "Loading resources…" : "No resources found"}</h2>
            <p>
              {loading
                ? "CRAM is retrieving governed and authoritative public references."
                : "Try a broader search, change the resource filter, or refresh the public feed."}
            </p>
          </div>
        )}
      </section>
    </ModuleShell>
  );
}
