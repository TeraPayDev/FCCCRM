import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Icon } from "../components/Icon";
import "./overview.css";

export function SystemStatusPage() {
  const health = useQuery({ queryKey: ["system", "health"], queryFn: api.health, retry: 1 });
  const online = !health.isError;
  const apiStatus = health.isPending
    ? "Checking service"
    : health.isError
      ? "Service unavailable"
      : `Healthy · v${health.data.version}`;

  return (
    <main className="overview-page">
      <section className="overview-hero">
        <div className="overview-copy">
          <p className="eyebrow">Climate Risk Analytics Management Platform</p>
          <h1>Climate intelligence for a more resilient Freetown.</h1>
          <p>
            CRAM brings governed climate data, spatial intelligence, analytics and municipal
            operations into one secure decision-support platform.
          </p>
          <div className="hero-actions">
            <Link className="primary-link" to="/dashboards">
              Explore dashboards <Icon name="arrow" />
            </Link>
            <Link className="secondary-link" to="/datasets">
              Open data catalogue
            </Link>
          </div>
        </div>
        <div className="climate-visual" aria-hidden="true">
          <div className="visual-orbit orbit-one" />
          <div className="visual-orbit orbit-two" />
          <div className="visual-center">
            <Icon name="map" />
            <strong>CRAM</strong>
            <span>Freetown</span>
          </div>
          <div className="visual-chip chip-heat">
            <Icon name="heat" /> Heat
          </div>
          <div className="visual-chip chip-flood">
            <Icon name="flood" /> Flood
          </div>
          <div className="visual-chip chip-tree">
            <Icon name="trees" /> Trees
          </div>
        </div>
      </section>

      <section className="overview-stats">
        <article>
          <span className="stat-icon green">
            <Icon name="activity" />
          </span>
          <div>
            <small>Platform status</small>
            <strong className={online ? "text-success" : "text-danger"}>{apiStatus}</strong>
          </div>
        </article>
        <article>
          <span className="stat-icon blue">
            <Icon name="data" />
          </span>
          <div>
            <small>Data governance</small>
            <strong>Version-aware lifecycle</strong>
          </div>
        </article>
        <article>
          <span className="stat-icon teal">
            <Icon name="map" />
          </span>
          <div>
            <small>Spatial platform</small>
            <strong>PostGIS · GeoServer · MapLibre</strong>
          </div>
        </article>
        <article>
          <span className="stat-icon pale">
            <Icon name="check" />
          </span>
          <div>
            <small>Engineering baseline</small>
            <strong>Milestones 0–12 complete</strong>
          </div>
        </article>
      </section>

      <div className="overview-columns">
        <section className="overview-card">
          <header>
            <div>
              <p className="eyebrow">Climate modules</p>
              <h2>Risk intelligence workspace</h2>
            </div>
            <Link to="/dashboards">View all</Link>
          </header>
          <div className="quick-modules">
            <Link to="/heat">
              <span>
                <Icon name="heat" />
              </span>
              <div>
                <strong>Heat Analytics</strong>
                <small>Weather and heat indicators</small>
              </div>
            </Link>
            <Link to="/flood">
              <span>
                <Icon name="flood" />
              </span>
              <div>
                <strong>Flood Monitoring</strong>
                <small>Incidents, zones and risk</small>
              </div>
            </Link>
            <Link to="/trees">
              <span>
                <Icon name="trees" />
              </span>
              <div>
                <strong>Tree Monitoring</strong>
                <small>Interventions and survival</small>
              </div>
            </Link>
            <Link to="/vulnerability">
              <span>
                <Icon name="vulnerability" />
              </span>
              <div>
                <strong>Vulnerability</strong>
                <small>Climate and socio-economic risk</small>
              </div>
            </Link>
          </div>
        </section>
        <section className="overview-card governance-card">
          <header>
            <div>
              <p className="eyebrow">Governance</p>
              <h2>Trusted data by design</h2>
            </div>
          </header>
          <div className="governance-flow">
            <span>Register</span>
            <i>→</i>
            <span>Validate</span>
            <i>→</i>
            <span>Approve</span>
            <i>→</i>
            <span>Publish</span>
          </div>
          <p>
            Source preservation, dataset versioning, permission-separated approval and auditable
            publication maintain a reliable evidence trail.
          </p>
          <div className="governance-links">
            <Link to="/datasets">Data Catalogue</Link>
            <Link to="/approvals">Approval Queue</Link>
            <Link to="/audit">Audit Trail</Link>
          </div>
        </section>
      </div>
    </main>
  );
}
