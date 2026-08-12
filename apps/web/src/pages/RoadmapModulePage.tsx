import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, roadmapApi } from "../api/client";
import { loadTokens } from "../auth/session";
import { ModuleShell } from "../components/ModuleShell";

type Row = Record<string, unknown>;
type LiveDefinition = { label: string; path: string; recordKey?: string };

type ModuleConfig = {
  title: string;
  subtitle: string;
  endpoints: Array<[string, string]>;
  live?: LiveDefinition[];
};

const configs: Record<string, ModuleConfig> = {
  processing: {
    title: "ETL / Processing",
    subtitle: "Background jobs, retries, idempotency, schedules and live public data connectors.",
    endpoints: [
      ["Jobs", "/api/v1/processing/jobs"],
      ["Schedules", "/api/v1/processing/schedules"],
      ["Integration connectors", "/api/v1/integrations/connectors"],
      ["Integration runs", "/api/v1/integrations/runs"],
    ],
  },
  heat: {
    title: "Heat Analytics",
    subtitle: "Governed CRAM observations plus live public weather reference data for Freetown.",
    endpoints: [
      ["Governed weather observations", "/api/v1/heat/observations"],
      ["Approved heat indicators", "/api/v1/heat/indicators"],
    ],
    live: [
      {
        label: "Open-Meteo current & hourly weather",
        path: "/api/v1/public-data/weather/open-meteo",
        recordKey: "hourly",
      },
      {
        label: "NASA POWER historical weather",
        path: "/api/v1/public-data/weather/nasa-power",
        recordKey: "records",
      },
    ],
  },
  flood: {
    title: "Flood Monitoring",
    subtitle: "Flood incidents and zones with live precipitation and drainage/waterway context.",
    endpoints: [
      ["Governed incidents", "/api/v1/flood/incidents"],
      ["Authoritative flood zones", "/api/v1/flood/zones"],
      ["Approved risk indicators", "/api/v1/flood/indicators"],
    ],
    live: [
      {
        label: "Live precipitation context",
        path: "/api/v1/public-data/weather/open-meteo",
        recordKey: "hourly",
      },
      {
        label: "OpenStreetMap waterways",
        path: "/api/v1/public-data/spatial/osm",
        recordKey: "features",
      },
    ],
  },
  trees: {
    title: "Tree Monitoring",
    subtitle: "Longitudinal CRAM tree registry plus live OpenStreetMap tree reference features.",
    endpoints: [
      ["Governed trees", "/api/v1/trees"],
      ["Inspections", "/api/v1/trees/inspections"],
      ["Batches", "/api/v1/trees/batches"],
      ["Species", "/api/v1/trees/species"],
      ["Catchments", "/api/v1/trees/catchments"],
    ],
    live: [
      {
        label: "OpenStreetMap tree reference",
        path: "/api/v1/public-data/spatial/osm",
        recordKey: "features",
      },
    ],
  },
  vulnerability: {
    title: "Climate Vulnerability",
    subtitle: "Governed socio-economic inputs plus World Bank public reference indicators.",
    endpoints: [
      ["Governed socio-economic indicators", "/api/v1/vulnerability/socio-economic"],
      ["Approved vulnerability indicators", "/api/v1/vulnerability/indicators"],
    ],
    live: [
      {
        label: "World Bank Sierra Leone context",
        path: "/api/v1/public-data/vulnerability/world-bank",
        recordKey: "records",
      },
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
      "Approved methodology registry with historical and Earth-observation reference catalogues.",
    endpoints: [["Methodologies", "/api/v1/analytics/methodologies"]],
    live: [
      {
        label: "Open-Meteo multi-year historical reference",
        path: "/api/v1/public-data/weather/history",
        recordKey: "records",
      },
      {
        label: "NASA POWER climate history",
        path: "/api/v1/public-data/weather/nasa-power",
        recordKey: "records",
      },
      {
        label: "Copernicus Climate Data Store readiness",
        path: "/api/v1/public-data/climate/copernicus-cds",
        recordKey: "records",
      },
      {
        label: "Copernicus Earth observation catalogue",
        path: "/api/v1/public-data/earth-observation/copernicus",
        recordKey: "records",
      },
      {
        label: "USGS Landsat catalogue",
        path: "/api/v1/public-data/earth-observation/usgs",
        recordKey: "records",
      },
    ],
  },
};

function printable(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function rowsFromLive(payload: Row, recordKey?: string, module?: string): Row[] {
  if (!recordKey) return [payload];
  const raw = payload[recordKey];
  if (!Array.isArray(raw)) return [];
  const rows = raw.filter((item): item is Row => Boolean(item && typeof item === "object"));
  if (recordKey === "features") {
    const flattened = rows.map((row) => {
      const properties = row.properties as Row | undefined;
      const geometry = row.geometry as Row | undefined;
      return {
        kind: properties?.kind,
        name: properties?.name,
        source: properties?.source,
        waterway: properties?.waterway,
        geometry_type: geometry?.type,
      };
    });
    if (module === "trees") return flattened.filter((row) => row.kind === "tree");
    if (module === "flood") return flattened.filter((row) => row.kind === "waterway");
    return flattened;
  }
  return rows;
}

function DataTable({ rows }: { rows: Row[] }) {
  if (rows.length === 0) return <p className="module-empty">No records available.</p>;
  const keys = Object.keys(rows[0])
    .filter((key) => key !== "geometry")
    .slice(0, 7);
  return (
    <table className="module-table">
      <thead>
        <tr>
          {keys.map((key) => (
            <th key={key}>{key.replaceAll("_", " ")}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.slice(0, 50).map((row, index) => (
          <tr key={String(row.id ?? index)}>
            {keys.map((key) => (
              <td key={key}>{printable(row[key])}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function RoadmapModulePage({ module }: { module: string }) {
  const navigate = useNavigate();
  const config = configs[module] ?? configs.processing;
  const [data, setData] = useState<Record<string, Row[]>>({});
  const [liveData, setLiveData] = useState<Record<string, Row>>({});
  const [message, setMessage] = useState("Loading…");
  const [liveMessage, setLiveMessage] = useState("");
  const [actionMessage, setActionMessage] = useState("");

  const reload = async () => {
    const tokens = loadTokens();
    if (!tokens) {
      navigate("/login?reason=expired");
      return;
    }
    try {
      const entries = await Promise.all(
        config.endpoints.map(
          async ([label, path]) =>
            [label, await roadmapApi.list(tokens.access_token, path)] as const,
        ),
      );
      setData(Object.fromEntries(entries));
      setMessage("");
    } catch (error: unknown) {
      setMessage(error instanceof Error ? error.message : "Unable to load module data.");
    }
  };

  const loadLive = async () => {
    if (!config.live?.length) return;
    const tokens = loadTokens();
    if (!tokens) return;
    setLiveMessage("Loading live public reference data…");
    const results: Record<string, Row> = {};
    for (const definition of config.live) {
      try {
        results[definition.label] = await roadmapApi.object(tokens.access_token, definition.path);
      } catch (error) {
        results[definition.label] = {
          error: error instanceof ApiError ? error.message : "Live source unavailable.",
        };
      }
    }
    setLiveData(results);
    setLiveMessage("");
  };

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void reload();
      void loadLive();
    }, 0);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [module]);

  const total = useMemo(
    () => Object.values(data).reduce((sum, rows) => sum + rows.length, 0),
    [data],
  );

  const bootstrap = async () => {
    const tokens = loadTokens();
    if (!tokens) return;
    setActionMessage("Configuring public connectors…");
    try {
      const result = await roadmapApi.post(
        tokens.access_token,
        "/api/v1/integrations/public/bootstrap",
      );
      setActionMessage(
        `Public connectors ready: ${String(result.public_connector_count ?? 0)} configured.`,
      );
      await roadmapApi.post(tokens.access_token, "/api/v1/processing/schedules/run-due");
      window.setTimeout(() => void reload(), 1200);
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "Unable to configure connectors.");
    }
  };

  return (
    <ModuleShell title={config.title} subtitle={config.subtitle}>
      <section className="module-card">
        <div className="module-grid">
          <div className="module-metric">
            <span className="metric-label">Governed CRAM records</span>
            <strong>{total}</strong>
            <p>Records already loaded into CRAM domain tables.</p>
          </div>
          <div className="module-metric">
            <span className="metric-label">Data surfaces</span>
            <strong>{config.endpoints.length + (config.live?.length ?? 0)}</strong>
            <p>Governed and live-reference sources available to this module.</p>
          </div>
        </div>
        {message && <p>{message}</p>}
        {module === "processing" && (
          <div className="module-toolbar">
            <button type="button" onClick={() => void bootstrap()}>
              Configure public connectors
            </button>
            <button type="button" className="secondary" onClick={() => void reload()}>
              Refresh jobs
            </button>
            {actionMessage && <span>{actionMessage}</span>}
          </div>
        )}
      </section>

      {module === "analytics" && (
        <p className="module-note">
          Live historical and satellite catalogues are reference inputs only. CRAM does not present
          a predictive or scenario result as authoritative until the methodology, assumptions,
          evaluation criteria and approval are recorded.
        </p>
      )}
      {module === "heat" && (
        <p className="module-note">
          Live weather helps users explore current conditions, but official heat indicators remain
          provenance-first and methodology-governed.
        </p>
      )}
      {module === "flood" && (
        <p className="module-note">
          Precipitation and mapped waterways provide situational context. CRAM deliberately does not
          invent a flood-risk formula; authoritative risk indicators require an approved methodology
          and agency data.
        </p>
      )}
      {module === "vulnerability" && (
        <p className="module-note">
          World Bank values provide national socio-economic context. They are not automatically
          converted into a Freetown vulnerability score.
        </p>
      )}

      {config.live?.length ? (
        <section className="module-card live-reference-card">
          <div className="live-reference-heading">
            <div>
              <span className="live-badge">LIVE PUBLIC REFERENCE</span>
              <h2>External data available now</h2>
            </div>
            <button type="button" className="secondary" onClick={() => void loadLive()}>
              Refresh live data
            </button>
          </div>
          {liveMessage && <p>{liveMessage}</p>}
          {config.live.map((definition) => {
            const payload = liveData[definition.label];
            const rows = payload ? rowsFromLive(payload, definition.recordKey, module) : [];
            return (
              <div className="live-source" key={definition.label}>
                <div className="live-source-title">
                  <strong>{definition.label}</strong>
                  {payload?.retrieved_at ? (
                    <span>Retrieved {String(payload.retrieved_at)}</span>
                  ) : null}
                </div>
                {payload?.error ? (
                  <p className="module-source-error">{String(payload.error)}</p>
                ) : (
                  <DataTable rows={rows} />
                )}
                {payload?.governance ? (
                  <p className="source-governance">{String(payload.governance)}</p>
                ) : null}
              </div>
            );
          })}
        </section>
      ) : null}

      {Object.entries(data).map(([label, rows]) => (
        <section className="module-card" key={label}>
          <h2>{label}</h2>
          <DataTable rows={rows} />
        </section>
      ))}
      <div className="module-actions">
        <Link to="/dashboards">Dashboard index</Link>
        <Link to="/audit">Audit trail</Link>
      </div>
    </ModuleShell>
  );
}
