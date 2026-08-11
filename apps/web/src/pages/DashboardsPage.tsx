import { Link } from "react-router-dom";
import { Icon } from "../components/Icon";
import { ModuleShell } from "../components/ModuleShell";

const modules = [
  [
    "ETL / Processing",
    "/processing",
    "processing",
    "Background transformation jobs and processor health.",
  ],
  ["Heat", "/heat", "heat", "Weather observations and approved heat indicators."],
  ["Flood", "/flood", "flood", "Flood incidents, zones and risk inputs."],
  ["Trees", "/trees", "trees", "Tree interventions, inspections and catchment progress."],
  [
    "Vulnerability",
    "/vulnerability",
    "vulnerability",
    "Socio-economic and climate vulnerability analysis.",
  ],
  [
    "Citizen Incidents",
    "/citizen-reports",
    "citizen",
    "Moderated public hazard reporting workflow.",
  ],
  ["Notifications", "/notifications", "bell", "Alerts and delivery status across channels."],
  ["Reporting", "/reports", "report", "Reproducible formal operational outputs."],
  [
    "Knowledge Hub",
    "/knowledge",
    "knowledge",
    "Searchable, permission-aware knowledge repository.",
  ],
  ["Administration", "/administration", "settings", "Platform settings and operational controls."],
  [
    "Advanced Analytics",
    "/analytics",
    "activity",
    "Versioned methodology and scenario foundations.",
  ],
] as const;

export function DashboardsPage() {
  return (
    <ModuleShell
      title="Operational Dashboards"
      subtitle="A single presentation layer for CRAM's climate, data-governance and municipal operations modules."
      eyebrow="Presentation & decision support"
    >
      <section className="dashboard-banner">
        <div>
          <span className="status-pill">Platform online</span>
          <h2>Climate intelligence at a glance</h2>
          <p>
            Explore governed data and traceable climate-risk outputs from one integrated workspace.
          </p>
        </div>
        <div className="banner-stat">
          <strong>11</strong>
          <span>Operational modules</span>
        </div>
      </section>
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
