import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { roadmapApi } from "../api/client";
import { loadTokens } from "../auth/session";
import { ClimateMap } from "../components/analytics/ClimateMap";
import { BarChart, LineChart, MetricTile } from "../components/analytics/Charts";
import { Icon } from "../components/Icon";
import { ModuleShell } from "../components/ModuleShell";

type Row = Record<string, unknown>;
const modules = [
  ["ETL / Processing", "/processing", "processing", "Automated ingestion and processor health."],
  ["Heat", "/heat", "heat", "Heat maps and temperature trends."],
  ["Flood", "/flood", "flood", "Rainfall, incidents and flood-risk inputs."],
  ["Trees", "/trees", "trees", "Tree locations, survival and canopy progress."],
  ["Vulnerability", "/vulnerability", "vulnerability", "Socio-economic and climate vulnerability."],
  ["Citizen Incidents", "/citizen-reports", "citizen", "Community hazard monitoring workflow."],
  ["Notifications", "/notifications", "bell", "Alerts and delivery status."],
  ["Reporting", "/reports", "report", "Executive and technical outputs."],
  ["Knowledge Hub", "/knowledge", "knowledge", "Methods, studies and publications."],
  ["User Management", "/users", "user", "Role-based access and partner accounts."],
  ["Advanced Analytics", "/analytics", "activity", "Historical trends and Earth observation."],
] as const;
function rows(payload: Row, key: string) {
  const v = payload[key];
  return Array.isArray(v) ? v.filter((x): x is Row => Boolean(x && typeof x === "object")) : [];
}
function n(r: Row, k: string) {
  const v = r[k];
  return typeof v === "number" && Number.isFinite(v) && v > -900 ? v : null;
}
function t(r: Row, k: string) {
  const v = r[k];
  return v == null ? "—" : String(v);
}
function features(payload: Row) {
  return rows(payload, "features") as Array<{
    type: "Feature";
    properties: Record<string, unknown>;
    geometry: { type: string; coordinates: unknown };
  }>;
}
export function DashboardsPage() {
  const [weather, setWeather] = useState<Row>({});
  const [grid, setGrid] = useState<Row>({});
  const [osm, setOsm] = useState<Row>({});
  const [citizens, setCitizens] = useState<Row[]>([]);
  const [jobs, setJobs] = useState<Row[]>([]);
  const [wb, setWb] = useState<Row>({});
  useEffect(() => {
    const tok = loadTokens();
    if (!tok) return;
    const a = tok.access_token;
    const timer = window.setTimeout(() => {
      void Promise.allSettled([
        roadmapApi.object(a, "/api/v1/public-data/weather/open-meteo").then(setWeather),
        roadmapApi.object(a, "/api/v1/public-data/weather/grid").then(setGrid),
        roadmapApi.object(a, "/api/v1/public-data/spatial/osm").then(setOsm),
        roadmapApi.list(a, "/api/v1/citizen-reports").then(setCitizens),
        roadmapApi.list(a, "/api/v1/processing/jobs").then(setJobs),
        roadmapApi.object(a, "/api/v1/public-data/vulnerability/world-bank").then(setWb),
      ]);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);
  const hourly = rows(weather, "hourly");
  const current = (weather.current as Row | undefined) ?? {};
  const failures = jobs.filter((j) => t(j, "status") === "FAILED").length;
  const treeCount = useMemo(
    () => features(osm).filter((f) => f.properties.kind === "tree").length,
    [osm],
  );
  const waterCount = useMemo(
    () => features(osm).filter((f) => f.properties.kind === "waterway").length,
    [osm],
  );
  const world = rows(wb, "records");
  return (
    <ModuleShell
      title="Executive Climate Dashboard"
      subtitle="Integrated city climate intelligence for FCC leadership, analysts and operational teams."
      eyebrow="Strategic decision support"
    >
      <section className="dashboard-banner">
        <div>
          <span className="status-pill">Live public feeds connected</span>
          <h2>Freetown climate intelligence at a glance</h2>
          <p>
            Current weather, public-reference spatial context and governed CRAM workflows in one
            decision-support view.
          </p>
        </div>
        <div className="banner-stat">
          <strong>{modules.length}</strong>
          <span>Operational capabilities</span>
        </div>
      </section>
      <div className="metric-row">
        <MetricTile
          label="Temperature"
          value={`${t(current, "temperature_2m")}°C`}
          hint="Open-Meteo · current"
          tone="good"
        />
        <MetricTile
          label="Humidity"
          value={`${t(current, "relative_humidity_2m")}%`}
          hint="Current reference"
        />
        <MetricTile
          label="24h precipitation"
          value={`${hourly
            .slice(0, 24)
            .reduce((s, r) => s + (n(r, "precipitation_mm") ?? 0), 0)
            .toFixed(1)} mm`}
          hint="Hourly total"
        />
        <MetricTile
          label="Citizen reports"
          value={citizens.length}
          hint="Community hazard submissions"
        />
        <MetricTile label="Mapped trees" value={treeCount} hint="OSM public reference" />
        <MetricTile label="Mapped waterways" value={waterCount} hint="Drainage context" />
        <MetricTile
          label="Failed jobs"
          value={failures}
          hint="Processing attention"
          tone={failures ? "bad" : "good"}
        />
        <MetricTile
          label="Socio-economic feeds"
          value={world.length}
          hint="World Bank reference indicators"
        />
      </div>
      <div className="analytics-grid dashboard-analytics">
        <LineChart
          title="Temperature outlook"
          subtitle="Open-Meteo hourly temperature"
          points={hourly.map((r) => ({ label: t(r, "observed_at"), value: n(r, "temperature_c") }))}
          unit="°C"
        />
        <BarChart
          title="Rainfall intensity"
          subtitle="Hourly precipitation"
          points={hourly.map((r) => ({
            label: t(r, "observed_at"),
            value: n(r, "precipitation_mm"),
          }))}
          unit=" mm"
        />
        <article className="viz-card map-span">
          <header>
            <div>
              <h3>Integrated climate situation map</h3>
              <p>
                Temperature surface, mapped waterways, trees and administrative context across
                Freetown
              </p>
            </div>
            <Link to="/map">Open full GIS Explorer →</Link>
          </header>
          <ClimateMap
            features={features(osm)}
            weatherGrid={features(grid)}
            mode="all"
            height={430}
          />
        </article>
      </div>
      <div className="section-heading">
        <div>
          <h2>Operational workspaces</h2>
          <p>Role-aware entry points for technical, management and governance workflows.</p>
        </div>
      </div>
      <section className="module-card">
        <div className="module-grid dashboard-module-grid">
          {modules.map(([name, path, icon, description]) => (
            <Link to={path} className="dashboard-module-card" key={path}>
              <span className="dashboard-icon">
                <Icon name={icon} />
              </span>
              <div>
                <strong>{name}</strong>
                <p>{description}</p>
              </div>
              <Icon name="arrow" className="dashboard-arrow" />
            </Link>
          ))}
        </div>
      </section>
    </ModuleShell>
  );
}
