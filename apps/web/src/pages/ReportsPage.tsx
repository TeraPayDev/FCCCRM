import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api, roadmapApi } from "../api/client";
import { loadTokens } from "../auth/session";
import { Icon } from "../components/Icon";
import { MetricTile } from "../components/analytics/Charts";
import { ModuleShell } from "../components/ModuleShell";
import "./reports.css";

type Row = Record<string, unknown>;
const reportTypes = [
  [
    "EXECUTIVE_CLIMATE_RISK_BRIEF",
    "Executive Climate Risk Brief",
    "Leadership summary of live climate conditions, governed datasets and operational activity.",
  ],
  [
    "HEAT_RISK_ASSESSMENT",
    "Heat Risk Assessment",
    "Temperature trends, heat references and methodology-governed indicators.",
  ],
  [
    "FLOOD_SITUATION_REPORT",
    "Flood Situation Report",
    "Rainfall, drainage/waterway context, incidents and flood-zone references.",
  ],
  [
    "TREE_PROGRAMME_PROGRESS",
    "Tree Programme Progress",
    "Tree inventory, planting, inspections, species and survival monitoring.",
  ],
  [
    "DATA_GOVERNANCE_REPORT",
    "Data Governance Report",
    "Dataset lifecycle, approvals, provenance and processing status.",
  ],
] as const;
function text(row: Row, key: string) {
  const value = row[key];
  return value == null ? "—" : String(value);
}
export function ReportsPage() {
  const [reports, setReports] = useState<Row[]>([]);
  const [canManage, setCanManage] = useState(false);
  const [type, setType] = useState<string>(reportTypes[0][0]);
  const [geography, setGeography] = useState("Freetown");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [modules, setModules] = useState<string[]>(["heat", "flood", "trees", "vulnerability"]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const load = async () => {
    const t = loadTokens();
    if (!t) return;
    const [items, me] = await Promise.all([
      roadmapApi.list(t.access_token, "/api/v1/reports"),
      api.me(t.access_token),
    ]);
    setReports(items);
    setCanManage(me.permissions.includes("reports.manage"));
  };
  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, []);
  const completed = reports.filter((r) => text(r, "status") === "COMPLETED").length;
  const pending = reports.length - completed;
  const selected = reportTypes.find((r) => r[0] === type) ?? reportTypes[0];
  const toggle = (module: string) =>
    setModules((items) =>
      items.includes(module) ? items.filter((x) => x !== module) : [...items, module],
    );
  async function generate(e: FormEvent) {
    e.preventDefault();
    const t = loadTokens();
    if (!t) return;
    setBusy(true);
    setMessage("Creating report job…");
    try {
      await roadmapApi.post(t.access_token, "/api/v1/reports", {
        report_type: type,
        format: "CSV",
        source_dataset_version_ids: [],
        parameters: {
          title: selected[1],
          geography,
          date_from: from || null,
          date_to: to || null,
          modules,
        },
      });
      setMessage("Report queued. CRAM is generating the output in the background.");
      await load();
      window.setTimeout(() => void load(), 1800);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to generate report.");
    } finally {
      setBusy(false);
    }
  }
  async function download(report: Row) {
    const t = loadTokens();
    if (!t) return;
    try {
      await roadmapApi.download(
        t.access_token,
        `/api/v1/reports/${text(report, "id")}/download`,
        `cram-report-${text(report, "id")}.csv`,
      );
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Report output is not ready.");
    }
  }
  return (
    <ModuleShell
      title="Climate Risk Reporting"
      subtitle="Build traceable executive and technical outputs with source, date and processing provenance."
      eyebrow="Decision support & communication"
    >
      <div className="metric-row">
        <MetricTile
          label="Generated"
          value={completed}
          hint="Completed report outputs"
          tone="good"
        />
        <MetricTile
          label="In progress"
          value={pending}
          hint="Queued or processing"
          tone={pending ? "warn" : "good"}
        />
        <MetricTile
          label="Templates"
          value={reportTypes.length}
          hint="Purpose-defined report types"
        />
        <MetricTile
          label="Output format"
          value="CSV"
          hint="Auditable baseline; presentation templates can extend this"
        />
      </div>
      {!canManage && (
        <div className="module-message">
          You have read-only reporting access. A user with report-management permission can create
          new outputs.
        </div>
      )}
      <div className="report-layout">
        <form className={`report-builder${canManage ? "" : " read-only"}`} onSubmit={generate}>
          <div className="section-title">
            <span>
              <Icon name="report" />
            </span>
            <div>
              <h2>Report builder</h2>
              <p>Choose the decision product you want CRAM to generate.</p>
            </div>
          </div>
          <label>
            Report type
            <select value={type} onChange={(e) => setType(e.target.value)}>
              {reportTypes.map(([code, label]) => (
                <option key={code} value={code}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <div className="report-template-help">
            <strong>{selected[1]}</strong>
            <p>{selected[2]}</p>
          </div>
          <div className="form-grid">
            <label>
              Geography
              <input value={geography} onChange={(e) => setGeography(e.target.value)} />
            </label>
            <label>
              From
              <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
            </label>
            <label>
              To
              <input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
            </label>
          </div>
          <fieldset>
            <legend>Include modules</legend>
            <div className="module-checks">
              {["heat", "flood", "trees", "vulnerability", "citizen reports", "processing"].map(
                (item) => (
                  <label key={item}>
                    <input
                      type="checkbox"
                      checked={modules.includes(item)}
                      onChange={() => toggle(item)}
                    />
                    <span>{item}</span>
                  </label>
                ),
              )}
            </div>
          </fieldset>
          <button disabled={busy || !canManage} className="icon-button report-generate">
            <Icon name="spark" />
            {busy ? "Queueing…" : "Generate report"}
          </button>
          {message && <div className="module-message">{message}</div>}
        </form>
        <aside className="report-preview">
          <p className="eyebrow">Output preview</p>
          <h2>{selected[1]}</h2>
          <div className="preview-cover">
            <Icon name="report" />
            <span>Freetown City Council</span>
            <strong>CRAM</strong>
            <small>
              {geography || "Freetown"} · {from || "Latest available"}
              {to ? ` to ${to}` : ""}
            </small>
          </div>
          <p>
            Generated reports retain the requested parameters, processing job ID and dataset-version
            references for auditability.
          </p>
        </aside>
      </div>
      <section className="data-section">
        <div className="section-heading">
          <div>
            <h2>Report history</h2>
            <p>Download completed outputs or monitor background generation.</p>
          </div>
          <button className="secondary-action icon-button" onClick={() => void load()}>
            <Icon name="refresh" /> Refresh
          </button>
        </div>
        <div className="report-cards">
          {reports.map((r) => (
            <article key={text(r, "id")} className="report-history-card">
              <span className="report-file-icon">
                <Icon name="file" />
              </span>
              <div>
                <strong>{text(r, "report_type").replaceAll("_", " ")}</strong>
                <small>{new Date(text(r, "created_at")).toLocaleString()}</small>
                <span
                  className={`account-status ${text(r, "status") === "COMPLETED" ? "active" : "inactive"}`}
                >
                  {text(r, "status")}
                </span>
              </div>
              <button
                disabled={text(r, "status") !== "COMPLETED"}
                onClick={() => void download(r)}
                className="secondary-action icon-button"
              >
                <Icon name="download" /> Download
              </button>
            </article>
          ))}
          {!reports.length && (
            <div className="empty-inline">No reports have been generated yet.</div>
          )}
        </div>
      </section>
    </ModuleShell>
  );
}
