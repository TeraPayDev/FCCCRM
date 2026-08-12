import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, roadmapApi } from "../api/client";
import { loadTokens } from "../auth/session";
import { ClimateMap } from "../components/analytics/ClimateMap";
import {
  BarChart,
  Donut,
  ForecastChart,
  LineChart,
  MetricTile,
} from "../components/analytics/Charts";
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
    subtitle:
      "Operational health, automated ingestion, retries, schedules and connector execution.",
    endpoints: [
      ["Jobs", "/api/v1/processing/jobs"],
      ["Schedules", "/api/v1/processing/schedules"],
      ["Integration connectors", "/api/v1/integrations/connectors"],
      ["Integration runs", "/api/v1/integrations/runs"],
    ],
  },
  heat: {
    title: "Heat Analytics",
    subtitle:
      "Live weather intelligence, historical trends and governed heat-analysis outputs for Freetown.",
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
      {
        label: "Freetown weather surface",
        path: "/api/v1/public-data/weather/grid",
        recordKey: "features",
      },
      {
        label: "OpenStreetMap context",
        path: "/api/v1/public-data/spatial/osm",
        recordKey: "features",
      },
    ],
  },
  flood: {
    title: "Flood Monitoring",
    subtitle:
      "Rainfall intensity, mapped waterways, citizen incidents and authoritative flood-zone intelligence.",
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
        label: "Freetown precipitation surface",
        path: "/api/v1/public-data/weather/grid",
        recordKey: "features",
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
    subtitle:
      "Spatial tree inventory, planting interventions, inspections and survival/canopy monitoring.",
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
    subtitle:
      "Socio-economic context and governed spatial vulnerability outputs for priority intervention planning.",
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
    subtitle:
      "Moderate geotagged community reports and coordinate field response across responsible agencies.",
    endpoints: [["Moderation queue", "/api/v1/citizen-reports"]],
  },
  notifications: {
    title: "Alerts & Notifications",
    subtitle: "Operational alerts and recipient delivery records across CRAM workflows.",
    endpoints: [["My notifications", "/api/v1/notifications"]],
  },
  administration: {
    title: "Administration & Operations",
    subtitle: "Platform controls, processing health, identity governance and non-secret settings.",
    endpoints: [
      ["Non-secret settings", "/api/v1/admin/settings"],
      ["Processing jobs", "/api/v1/processing/jobs"],
    ],
  },
  analytics: {
    title: "Advanced Analytics",
    subtitle:
      "Historical climate trends, Earth-observation catalogues and governed methodology foundations.",
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

function number(row: Row, key: string): number | null {
  const v = row[key];
  return typeof v === "number" && Number.isFinite(v) && v > -900 ? v : null;
}
function text(row: Row, key: string) {
  const v = row[key];
  return v === null || v === undefined
    ? "—"
    : typeof v === "object"
      ? JSON.stringify(v)
      : String(v);
}
function rowsFromLive(payload: Row, recordKey?: string): Row[] {
  const raw = recordKey ? payload[recordKey] : [payload];
  return Array.isArray(raw) ? raw.filter((v): v is Row => Boolean(v && typeof v === "object")) : [];
}
function featureRows(payload: Row, kind?: string) {
  return rowsFromLive(payload, "features").filter((r) => {
    const p = r.properties as Row | undefined;
    return !kind || p?.kind === kind;
  });
}
function asFeatures(payload?: Row) {
  return rowsFromLive(payload ?? {}, "features") as Array<{
    type: "Feature";
    properties: Record<string, unknown>;
    geometry: { type: string; coordinates: unknown };
  }>;
}
function series(rows: Row[], valueKey: string, labelKey: string) {
  return rows.map((r) => ({ label: text(r, labelKey), value: number(r, valueKey) }));
}

function DataTable({ rows, limit = 12 }: { rows: Row[]; limit?: number }) {
  const [open, setOpen] = useState(false);
  if (!rows.length) return <p className="module-empty">No records available.</p>;
  const keys = Object.keys(rows[0])
    .filter((k) => k !== "geometry" && k !== "properties")
    .slice(0, 7);
  const shown = rows.slice(0, open ? 50 : limit);
  return (
    <div className="table-wrap">
      <table className="module-table">
        <thead>
          <tr>
            {keys.map((k) => (
              <th key={k}>{k.replaceAll("_", " ")}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {shown.map((r, i) => (
            <tr key={String(r.id ?? i)}>
              {keys.map((k) => (
                <td key={k}>{text(r, k)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > limit && (
        <button className="table-toggle" onClick={() => setOpen((v) => !v)}>
          {open ? "Show summary" : "Show more records"} · {rows.length} total
        </button>
      )}
    </div>
  );
}

function LiveTable({
  label,
  payload,
  recordKey,
  module,
}: {
  label: string;
  payload: Row;
  recordKey?: string;
  module: string;
}) {
  if (payload.error) return <div className="source-error">{String(payload.error)}</div>;
  let rows = rowsFromLive(payload, recordKey);
  if (recordKey === "features")
    rows = rows
      .map((r) => {
        const p = (r.properties as Row | undefined) ?? {};
        const g = (r.geometry as Row | undefined) ?? {};
        return {
          kind: p.kind,
          name: p.name,
          source: p.source,
          waterway: p.waterway,
          temperature_c: p.temperature_c,
          precipitation_mm: p.precipitation_mm,
          geometry_type: g.type,
        };
      })
      .filter((r) =>
        module === "trees" ? r.kind === "tree" : module === "flood" ? r.kind === "waterway" : true,
      );
  return (
    <section className="data-section">
      <div className="section-heading">
        <div>
          <h2>{label}</h2>
          <p>Live public reference · retrieved {text(payload, "retrieved_at")}</p>
        </div>
        <span className="reference-badge">PUBLIC REFERENCE</span>
      </div>
      <DataTable rows={rows} />
    </section>
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
  const [forecast, setForecast] = useState<Row>({});
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
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Unable to load module data.");
    }
  };
  const loadLive = async () => {
    if (!config.live?.length) return;
    const tokens = loadTokens();
    if (!tokens) return;
    setLiveMessage("Refreshing live sources…");
    const results: Record<string, Row> = {};
    for (const def of config.live) {
      try {
        results[def.label] = await roadmapApi.object(tokens.access_token, def.path);
      } catch (e) {
        results[def.label] = {
          error: e instanceof ApiError ? e.message : "Live source unavailable.",
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
    return () => window.clearTimeout(timer); // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [module]);
  const total = useMemo(() => Object.values(data).reduce((s, r) => s + r.length, 0), [data]);
  const bootstrap = async () => {
    const t = loadTokens();
    if (!t) return;
    setActionMessage("Configuring public connectors…");
    try {
      const r = await roadmapApi.post(t.access_token, "/api/v1/integrations/public/bootstrap");
      setActionMessage(
        `Public connectors ready: ${String(r.public_connector_count ?? 0)} configured.`,
      );
      await roadmapApi.post(t.access_token, "/api/v1/processing/schedules/run-due");
      window.setTimeout(() => void reload(), 1200);
    } catch (e) {
      setActionMessage(e instanceof Error ? e.message : "Unable to configure connectors.");
    }
  };
  const runHeatForecast = async () => {
    const t = loadTokens();
    if (!t) return;
    const values = history
      .slice(-45)
      .map((r) => number(r, "temperature_max_c"))
      .filter((v): v is number => v !== null);
    if (values.length < 2) {
      setActionMessage("Historical series is not ready for forecasting.");
      return;
    }
    setActionMessage("Running CRAM engineering trend forecast…");
    try {
      const result = await roadmapApi.post(t.access_token, "/api/v1/analytics/predict/heat", {
        values,
        periods: 14,
      });
      setForecast(result);
      setActionMessage("Trend forecast generated from the current historical reference series.");
    } catch (e) {
      setActionMessage(e instanceof Error ? e.message : "Unable to run trend forecast.");
    }
  };

  const hourly = rowsFromLive(
    liveData["Open-Meteo current & hourly weather"] ?? liveData["Live precipitation context"] ?? {},
    "hourly",
  );
  const nasa = rowsFromLive(
    liveData["NASA POWER historical weather"] ?? liveData["NASA POWER climate history"] ?? {},
    "records",
  );
  const history = rowsFromLive(
    liveData["Open-Meteo multi-year historical reference"] ?? {},
    "records",
  );
  const osm =
    liveData["OpenStreetMap context"] ??
    liveData["OpenStreetMap waterways"] ??
    liveData["OpenStreetMap tree reference"] ??
    {};
  const grid =
    liveData["Freetown weather surface"] ?? liveData["Freetown precipitation surface"] ?? {};
  const world = rowsFromLive(liveData["World Bank Sierra Leone context"] ?? {}, "records");
  const allJobs = data.Jobs ?? data["Processing jobs"] ?? [];
  const jobs = allJobs.filter((r) => !text(r, "parameters").includes("SLMET-SANDBOX"));
  const retiredLegacyJobs = allJobs.length - jobs.length;
  const failed = jobs.filter((r) => text(r, "status") === "FAILED").length;
  const succeeded = jobs.filter((r) => text(r, "status") === "SUCCEEDED").length;

  return (
    <ModuleShell
      title={config.title}
      subtitle={config.subtitle}
      actions={
        config.live?.length ? (
          <button className="secondary-action" onClick={() => void loadLive()}>
            {liveMessage || "Refresh live data"}
          </button>
        ) : undefined
      }
    >
      {message && <div className="module-message">{message}</div>}
      {actionMessage && <div className="module-message success">{actionMessage}</div>}

      {module === "heat" && (
        <>
          <div className="metric-row">
            <MetricTile
              label="Current temperature"
              value={`${text((liveData["Open-Meteo current & hourly weather"]?.current as Row) ?? {}, "temperature_2m")}°C`}
              hint="Open-Meteo · Freetown"
              tone="good"
            />
            <MetricTile
              label="Humidity"
              value={`${text((liveData["Open-Meteo current & hourly weather"]?.current as Row) ?? {}, "relative_humidity_2m")}%`}
              hint="Current public reference"
            />
            <MetricTile
              label="24h rainfall"
              value={`${hourly
                .slice(0, 24)
                .reduce((s, r) => s + (number(r, "rain_mm") ?? 0), 0)
                .toFixed(1)} mm`}
              hint="Hourly accumulation"
            />
            <MetricTile
              label="Governed heat indicators"
              value={(data["Approved heat indicators"] ?? []).length}
              hint="Approved methodology outputs"
            />
          </div>
          <div className="analytics-grid">
            <LineChart
              title="Temperature trend"
              subtitle="Open-Meteo hourly forecast/reference"
              points={series(hourly, "temperature_c", "observed_at")}
              unit="°C"
            />
            <BarChart
              title="Rainfall intensity"
              subtitle="Hourly precipitation context"
              points={series(hourly, "precipitation_mm", "observed_at")}
              unit=" mm"
            />
            <article className="viz-card map-span">
              <header>
                <div>
                  <h3>Freetown temperature surface</h3>
                  <p>Real Open-Meteo grid cells · contextual, not an approved heat-risk index</p>
                </div>
                <span className="reference-badge">LIVE</span>
              </header>
              <ClimateMap
                features={asFeatures(osm)}
                weatherGrid={asFeatures(grid)}
                mode="heat"
                height={390}
              />
            </article>
            <LineChart
              title="NASA POWER temperature history"
              subtitle="Recent daily analysis-ready reference"
              points={series(nasa, "temperature_c", "date")}
              unit="°C"
            />
          </div>
        </>
      )}

      {module === "flood" && (
        <>
          <div className="metric-row">
            <MetricTile
              label="Recent rainfall"
              value={`${hourly
                .slice(0, 24)
                .reduce((s, r) => s + (number(r, "precipitation_mm") ?? 0), 0)
                .toFixed(1)} mm`}
              hint="Next/most recent 24 hourly values"
            />
            <MetricTile
              label="Mapped waterways"
              value={featureRows(osm, "waterway").length}
              hint="OpenStreetMap reference"
              tone="good"
            />
            <MetricTile
              label="Governed incidents"
              value={(data["Governed incidents"] ?? []).length}
              hint="Validated CRAM incidents"
            />
            <MetricTile
              label="Flood zones"
              value={(data["Authoritative flood zones"] ?? []).length}
              hint="Authoritative agency layers"
            />
          </div>
          <div className="analytics-grid">
            <BarChart
              title="Hourly precipitation"
              subtitle="Rainfall intensity context for flood monitoring"
              points={series(hourly, "precipitation_mm", "observed_at")}
              unit=" mm"
            />
            <article className="viz-card map-span">
              <header>
                <div>
                  <h3>Rainfall & drainage context</h3>
                  <p>
                    Public precipitation surface over mapped waterways; no invented
                    flood-probability score
                  </p>
                </div>
                <span className="reference-badge">LIVE</span>
              </header>
              <ClimateMap
                features={asFeatures(osm)}
                weatherGrid={asFeatures(grid)}
                mode="flood"
                height={420}
              />
            </article>
          </div>
        </>
      )}

      {module === "trees" && (
        <>
          <div className="metric-row">
            <MetricTile
              label="Mapped reference trees"
              value={featureRows(osm, "tree").length}
              hint="OpenStreetMap public reference"
              tone="good"
            />
            <MetricTile
              label="Governed trees"
              value={(data["Governed trees"] ?? []).length}
              hint="FCC authoritative registry"
            />
            <MetricTile
              label="Inspections"
              value={(data.Inspections ?? []).length}
              hint="Longitudinal field records"
            />
            <MetricTile
              label="Planting catchments"
              value={(data.Catchments ?? []).length}
              hint="Programme monitoring areas"
            />
          </div>
          <div className="analytics-grid">
            <article className="viz-card map-span">
              <header>
                <div>
                  <h3>Tree distribution map</h3>
                  <p>
                    Reference tree points with room for FCC registry, catchments and vegetation
                    layers
                  </p>
                </div>
                <span className="reference-badge">OSM</span>
              </header>
              <ClimateMap features={asFeatures(osm)} mode="trees" height={440} />
            </article>
            <Donut
              title="Registry readiness"
              value={(data["Governed trees"] ?? []).length}
              total={Math.max(1, featureRows(osm, "tree").length)}
              centerLabel="governed"
            >
              <p>
                As FCC planting and survival data is loaded, this panel becomes a survival/progress
                summary by catchment and species.
              </p>
            </Donut>
          </div>
        </>
      )}

      {module === "vulnerability" && (
        <>
          <div className="metric-row">
            {world.slice(0, 4).map((r, i) => (
              <MetricTile
                key={i}
                label={text(r, "indicator")}
                value={
                  typeof r.value === "number"
                    ? r.value.toLocaleString(undefined, { maximumFractionDigits: 1 })
                    : text(r, "value")
                }
                hint={`${text(r, "year")} · Sierra Leone`}
              />
            ))}
          </div>
          <div className="analytics-grid">
            <BarChart
              title="Socio-economic reference indicators"
              subtitle="World Bank context; values retain their native units"
              points={world.map((r) => ({
                label: text(r, "indicator"),
                value: number(r, "value"),
              }))}
            />
            <article className="viz-card">
              <header>
                <div>
                  <h3>Vulnerability model readiness</h3>
                  <p>TOR-aligned workflow without fabricating an index</p>
                </div>
              </header>
              <div className="pipeline">
                <span>Population & poverty</span>
                <b>+</b>
                <span>Heat exposure</span>
                <b>+</b>
                <span>Flood exposure</span>
                <b>→</b>
                <span className="pending">Approved methodology</span>
                <b>→</b>
                <span>Priority zones</span>
              </div>
              <p className="compact-note">
                An official vulnerability map is generated only when Stats-SL/NaCSA inputs and an
                approved methodology are registered in CRAM.
              </p>
            </article>
          </div>
        </>
      )}

      {module === "processing" && (
        <>
          <div className="metric-row">
            <MetricTile
              label="Processing jobs"
              value={jobs.length}
              hint="Current operational history"
            />
            <MetricTile label="Succeeded" value={succeeded} hint="Completed jobs" tone="good" />
            <MetricTile
              label="Failed"
              value={failed}
              hint="Requires operator attention"
              tone={failed ? "bad" : "good"}
            />
            <MetricTile
              label="Active connectors"
              value={
                (data["Integration connectors"] ?? []).filter((r) => r.is_active !== false).length
              }
              hint="Institutional/public data adapters"
            />
            <MetricTile
              label="Retired legacy jobs"
              value={retiredLegacyJobs}
              hint="Preserved in audit history; excluded from current health"
            />
          </div>
          <div className="analytics-grid">
            <Donut
              title="Job success rate"
              value={succeeded}
              total={Math.max(1, succeeded + failed)}
              centerLabel="success"
            >
              <p>
                {failed
                  ? `${failed} failed job(s) remain visible for diagnosis.`
                  : "No failed jobs in the current result set."}
              </p>
            </Donut>
            <article className="viz-card">
              <header>
                <div>
                  <h3>Connector operations</h3>
                  <p>Configure genuine public connectors and retire obsolete sandbox jobs.</p>
                </div>
              </header>
              <button onClick={() => void bootstrap()}>Configure public connectors</button>
              <p className="compact-note">
                The bootstrap endpoint updates public schedules idempotently and deactivates
                superseded sandbox connectors.
              </p>
            </article>
          </div>
        </>
      )}

      {module === "citizen" && (
        <>
          <div className="metric-row">
            <MetricTile
              label="Submitted"
              value={
                (data["Moderation queue"] ?? []).filter((r) => text(r, "status") === "SUBMITTED")
                  .length
              }
              hint="Awaiting moderation"
              tone="warn"
            />
            <MetricTile
              label="Total reports"
              value={(data["Moderation queue"] ?? []).length}
              hint="Governed citizen reports"
            />
            <MetricTile
              label="Geotagged"
              value={
                (data["Moderation queue"] ?? []).filter(
                  (r) => r.latitude != null && r.longitude != null,
                ).length
              }
              hint="Available for hazard mapping"
            />
            <MetricTile
              label="Public portal"
              value={<Link to="/report-hazard">Open</Link>}
              hint="Offline-capable submission"
            />
          </div>
          <section className="data-section">
            <div className="section-heading">
              <div>
                <h2>Moderation queue</h2>
                <p>Review, validate, route and publish community hazard reports.</p>
              </div>
            </div>
            <DataTable rows={data["Moderation queue"] ?? []} limit={20} />
          </section>
        </>
      )}

      {module === "notifications" && (
        <div className="empty-state-rich">
          <div className="empty-icon">!</div>
          <h2>No active notifications</h2>
          <p>
            Alerts created by validated incidents, extreme conditions or workflow events will appear
            here with delivery status and responsible agency.
          </p>
        </div>
      )}
      {module === "administration" && (
        <>
          <div className="metric-row">
            <MetricTile
              label="Settings"
              value={(data["Non-secret settings"] ?? []).length}
              hint="Non-secret operational configuration"
            />
            <MetricTile label="Processing jobs" value={jobs.length} hint="Cross-platform health" />
            <MetricTile
              label="User management"
              value={<Link to="/users">Open</Link>}
              hint="Accounts, roles and institutions"
              tone="good"
            />
            <MetricTile
              label="Audit trail"
              value={<Link to="/audit">Review</Link>}
              hint="Append-only governance history"
            />
          </div>
          <section className="data-section">
            <div className="section-heading">
              <div>
                <h2>Recent processing activity</h2>
              </div>
            </div>
            <DataTable rows={jobs} />
          </section>
        </>
      )}

      {module === "analytics" && (
        <>
          <div className="metric-row">
            <MetricTile
              label="Historical records"
              value={history.length}
              hint="Open-Meteo multi-year reference"
            />
            <MetricTile
              label="NASA records"
              value={nasa.filter((r) => number(r, "temperature_c") !== null).length}
              hint="No-data sentinels suppressed"
            />
            <MetricTile
              label="Methodologies"
              value={(data.Methodologies ?? []).length}
              hint="Governed analytical methods"
            />
            <MetricTile
              label="CDS"
              value={String(liveData["Copernicus Climate Data Store readiness"]?.status ?? "CHECK")}
              hint={
                liveData["Copernicus Climate Data Store readiness"]?.status === "READY"
                  ? "Personal access token available server-side"
                  : "Set COPERNICUS_CDS_KEY in the deployment environment and accept dataset terms"
              }
              tone={
                liveData["Copernicus Climate Data Store readiness"]?.status === "READY"
                  ? "good"
                  : "warn"
              }
            />
          </div>
          <div className="analytics-grid">
            <LineChart
              title="Long-term maximum temperature"
              subtitle="Open-Meteo historical daily reference"
              points={series(history.slice(-180), "temperature_max_c", "date")}
              unit="°C"
            />
            <BarChart
              title="Long-term precipitation"
              subtitle="Recent historical daily totals"
              points={series(history.slice(-90), "precipitation_mm", "date")}
              unit=" mm"
            />
            <article className="viz-card prediction-launch">
              <header>
                <div>
                  <h3>Predictive climate trend</h3>
                  <p>
                    Run an explainable engineering baseline against the latest historical
                    temperature series.
                  </p>
                </div>
                <span className="reference-badge">MODEL v2</span>
              </header>
              <button className="icon-button" onClick={() => void runHeatForecast()}>
                Run 14-period heat trend forecast
              </button>
              <p className="compact-note">
                The result includes trend direction, model fit and an uncertainty band. It remains a
                demonstration baseline until an FCC-approved methodology and thresholds are
                registered.
              </p>
              {rowsFromLive(forecast, "forecast").length > 0 && (
                <div className="prediction-summary">
                  <div>
                    <span>Trend</span>
                    <strong>{String(forecast.trend_direction ?? "—").replaceAll("_", " ")}</strong>
                  </div>
                  <div>
                    <span>Slope</span>
                    <strong>
                      {typeof (forecast.metrics as Row | undefined)?.slope_per_period === "number"
                        ? `${((forecast.metrics as Row).slope_per_period as number).toFixed(3)} °C/period`
                        : "—"}
                    </strong>
                  </div>
                  <div>
                    <span>R²</span>
                    <strong>
                      {typeof (forecast.metrics as Row | undefined)?.r_squared === "number"
                        ? ((forecast.metrics as Row).r_squared as number).toFixed(3)
                        : "—"}
                    </strong>
                  </div>
                  <div>
                    <span>Observations</span>
                    <strong>
                      {text((forecast.metrics as Row | undefined) ?? {}, "observations")}
                    </strong>
                  </div>
                </div>
              )}
            </article>
            {rowsFromLive(forecast, "forecast").length > 0 && (
              <ForecastChart
                title="Observed + 14-period forecast"
                subtitle={String(forecast.warning ?? "Engineering trend baseline")}
                history={history
                  .slice(-28)
                  .map((r) => ({ label: text(r, "date"), value: number(r, "temperature_max_c") }))}
                forecast={rowsFromLive(forecast, "forecast").map((r) => ({
                  label: `P${text(r, "period")}`,
                  value: number(r, "value"),
                  lower: number(r, "lower"),
                  upper: number(r, "upper"),
                }))}
                unit="°C"
              />
            )}
          </div>
        </>
      )}

      {![
        "heat",
        "flood",
        "trees",
        "vulnerability",
        "processing",
        "citizen",
        "notifications",
        "administration",
        "analytics",
      ].includes(module) && (
        <div className="metric-row">
          <MetricTile label="Governed records" value={total} />
        </div>
      )}

      {config.live?.length && (
        <>
          <div className="section-heading">
            <div>
              <h2>Reference data explorer</h2>
              <p>Raw source detail remains available for provenance and technical inspection.</p>
            </div>
          </div>
          {config.live.map((def) =>
            liveData[def.label] ? (
              <LiveTable
                key={def.label}
                label={def.label}
                payload={liveData[def.label]}
                recordKey={def.recordKey}
                module={module}
              />
            ) : null,
          )}
        </>
      )}
      {config.endpoints.map(([label]) => {
        let surface = data[label] ?? [];
        if (module === "processing" && label === "Jobs") surface = jobs;
        if (module === "processing" && label === "Integration connectors")
          surface = surface.filter((r) => r.is_active !== false);
        if (module === "processing" && label === "Schedules")
          surface = surface.filter((r) => r.is_active !== false);
        return (
          <section className="data-section" key={label}>
            <div className="section-heading">
              <div>
                <h2>{label}</h2>
                <p>
                  {module === "processing"
                    ? "Active operational surface; retired sandbox history remains in the audit trail."
                    : "Governed CRAM data surface."}
                </p>
              </div>
            </div>
            <DataTable rows={surface} />
          </section>
        );
      })}
    </ModuleShell>
  );
}
