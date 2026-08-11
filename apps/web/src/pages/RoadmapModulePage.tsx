import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { roadmapApi } from "../api/client";
import { loadTokens } from "../auth/session";
import { ModuleShell } from "../components/ModuleShell";

type Row = Record<string, unknown>;
const configs: Record<
  string,
  { title: string; subtitle: string; endpoints: Array<[string, string]> }
> = {
  processing: {
    title: "ETL / Processing",
    subtitle: "Background jobs, retries, idempotency and processor status.",
    endpoints: [["Jobs", "/api/v1/processing/jobs"], ["Schedules", "/api/v1/processing/schedules"]],
  },
  heat: {
    title: "Heat Analytics",
    subtitle: "Weather observations and approved, versioned heat indicators.",
    endpoints: [
      ["Weather observations", "/api/v1/heat/observations"],
      ["Heat indicators", "/api/v1/heat/indicators"],
    ],
  },
  flood: {
    title: "Flood Monitoring",
    subtitle: "Flood incidents, zones and methodology-governed risk indicators.",
    endpoints: [
      ["Incidents", "/api/v1/flood/incidents"],
      ["Flood zones", "/api/v1/flood/zones"],
      ["Risk indicators", "/api/v1/flood/indicators"],
    ],
  },
  trees: {
    title: "Tree Monitoring",
    subtitle: "Longitudinal tree registry, planting batches, catchments and inspection history.",
    endpoints: [
      ["Trees", "/api/v1/trees"],
      ["Inspections", "/api/v1/trees/inspections"],
      ["Batches", "/api/v1/trees/batches"],
      ["Species", "/api/v1/trees/species"],
      ["Catchments", "/api/v1/trees/catchments"],
    ],
  },
  vulnerability: {
    title: "Climate Vulnerability",
    subtitle: "Socio-economic inputs and methodology-versioned vulnerability outputs.",
    endpoints: [
      ["Socio-economic indicators", "/api/v1/vulnerability/socio-economic"],
      ["Vulnerability indicators", "/api/v1/vulnerability/indicators"],
    ],
  },
  citizen: {
    title: "Citizen Hazard Reporting",
    subtitle: "Moderated public hazard reports with privacy-safe operational visibility.",
    endpoints: [["Moderation queue", "/api/v1/citizen-reports"]],
  },
  notifications: {
    title: "Alerts & Notifications",
    subtitle: "Domain alerts separated from recipient delivery records.",
    endpoints: [["My notifications", "/api/v1/notifications"]],
  },
  reports: {
    title: "Reporting",
    subtitle: "Reproducible, source-version-aware reports generated through background processing.",
    endpoints: [["Report history", "/api/v1/reports"]],
  },
  knowledge: {
    title: "Knowledge Hub",
    subtitle: "Permission-aware repository for datasets, reports, methods and publications.",
    endpoints: [["Knowledge items", "/api/v1/knowledge"]],
  },
  administration: {
    title: "Administration & Operations",
    subtitle: "Controlled non-secret settings and operational control surfaces.",
    endpoints: [
      ["Non-secret settings", "/api/v1/admin/settings"],
      ["Processing jobs", "/api/v1/processing/jobs"],
    ],
  },
  analytics: {
    title: "Advanced Analytics",
    subtitle:
      "Versioned methodology registry. Predictive/scenario execution remains gated by approved methods and data.",
    endpoints: [["Methodologies", "/api/v1/analytics/methodologies"]],
  },
};
function printable(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
export function RoadmapModulePage({ module }: { module: string }) {
  const navigate = useNavigate();
  const config = configs[module] ?? configs.processing;
  const [data, setData] = useState<Record<string, Row[]>>({});
  const [message, setMessage] = useState("Loading…");
  useEffect(() => {
    const tokens = loadTokens();
    if (!tokens) {
      navigate("/login");
      return;
    }
    let active = true;
    Promise.all(
      config.endpoints.map(
        async ([label, path]) => [label, await roadmapApi.list(tokens.access_token, path)] as const,
      ),
    )
      .then((entries) => {
        if (active) {
          setData(Object.fromEntries(entries));
          setMessage("");
        }
      })
      .catch((error: unknown) => {
        if (active)
          setMessage(error instanceof Error ? error.message : "Unable to load module data.");
      });
    return () => {
      active = false;
    };
  }, [config, navigate]);
  const total = useMemo(
    () => Object.values(data).reduce((sum, rows) => sum + rows.length, 0),
    [data],
  );
  return (
    <ModuleShell title={config.title} subtitle={config.subtitle}>
      <section className="module-card">
        <div className="module-grid">
          <div className="module-metric">
            Loaded records<strong>{total}</strong>
          </div>
          <div className="module-metric">
            Data surfaces<strong>{config.endpoints.length}</strong>
          </div>
        </div>
        {message && <p>{message}</p>}
      </section>
      {module === "analytics" && (
        <p className="module-note">
          CRAM does not execute or present an analytical model as authoritative until its
          methodology, assumptions, evaluation criteria and approval are recorded.
        </p>
      )}
      {module === "heat" && (
        <p className="module-note">
          Heat calculations are provenance-first: scientific formulas are not embedded unless their
          approved methodology/version is known.
        </p>
      )}
      {Object.entries(data).map(([label, rows]) => (
        <section className="module-card" key={label}>
          <h2>{label}</h2>
          {rows.length === 0 ? (
            <p>No records yet.</p>
          ) : (
            <table className="module-table">
              <thead>
                <tr>
                  {Object.keys(rows[0])
                    .slice(0, 7)
                    .map((key) => (
                      <th key={key}>{key.replaceAll("_", " ")}</th>
                    ))}
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 50).map((row, index) => (
                  <tr key={String(row.id ?? index)}>
                    {Object.keys(rows[0])
                      .slice(0, 7)
                      .map((key) => (
                        <td key={key}>{printable(row[key])}</td>
                      ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      ))}
      <div className="module-actions">
        <Link to="/dashboards">Dashboard index</Link>
        <Link to="/audit">Audit trail</Link>
      </div>
    </ModuleShell>
  );
}
