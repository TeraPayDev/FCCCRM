import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { loadTokens } from "../auth/session";
import { PageHeader, StatusBadge } from "../components/Page";

export function SystemStatusPage() {
  const tokens = loadTokens();
  const health = useQuery({ queryKey: ["system", "health"], queryFn: api.health, retry: 1 });
  const me = useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => api.me(tokens!.access_token),
    enabled: Boolean(tokens),
    retry: false,
  });
  const can = (permission: string) => me.data?.permissions.includes(permission) ?? false;

  const apiStatus = health.isPending ? "Checking" : health.isError ? "Unavailable" : "Healthy";
  const capabilities = [
    {
      title: "Data catalogue",
      description: "Register institutional datasets, manage versions and review source metadata.",
      to: "/datasets",
      permission: "datasets.read",
      tag: "Data",
    },
    {
      title: "Approval queue",
      description: "Review validated dataset versions through the governed publishing workflow.",
      to: "/approvals",
      permission: "datasets.approve",
      tag: "Governance",
    },
    {
      title: "GIS workspace",
      description: "Inspect the CRAM spatial foundation and published GeoServer layers.",
      to: "/map",
      permission: "gis.read",
      tag: "Spatial",
    },
    {
      title: "Audit trail",
      description: "Trace privileged, security and data-governance activity across the platform.",
      to: "/audit",
      permission: "audit.read",
      tag: "Audit",
    },
    {
      title: "Organisations",
      description: "Manage institutional ownership and user-to-organisation assignments.",
      to: "/organisations",
      permission: "users.manage",
      tag: "Admin",
    },
  ].filter((item) => can(item.permission));

  return (
    <main className="system-page">
      <PageHeader
        eyebrow="Platform overview"
        title="CRAM operational workspace"
        description="A governed climate-risk data platform for Freetown City Council and partner institutions."
        actions={
          !tokens ? (
            <Link className="button button-primary" to="/login">
              Sign in to CRAM
            </Link>
          ) : (
            <Link className="button" to="/profile">
              View my access
            </Link>
          )
        }
      />

      <section className="grid-3" aria-label="Platform status">
        <article className="metric-card">
          <span className="metric-label">API service</span>
          <div className="metric-value">
            <StatusBadge value={apiStatus} />
          </div>
          <span className="metric-detail">
            {health.data
              ? `${health.data.service} · v${health.data.version}`
              : "Connectivity check"}
          </span>
        </article>
        <article className="metric-card">
          <span className="metric-label">Session</span>
          <div className="metric-value">
            {me.data ? me.data.username : tokens ? "Loading" : "Guest"}
          </div>
          <span className="metric-detail">
            {me.data?.roles.map((role) => role.replaceAll("_", " ")).join(", ") ||
              "Sign in for governed workspace access"}
          </span>
        </article>
        <article className="metric-card">
          <span className="metric-label">Available workspaces</span>
          <div className="metric-value">{capabilities.length}</div>
          <span className="metric-detail">Based on your effective permissions</span>
        </article>
      </section>

      <section className="card system-workspaces">
        <div className="card-header">
          <div>
            <h2>Your workspace</h2>
            <p className="card-subtitle">
              Only areas permitted for the current account are surfaced here.
            </p>
          </div>
        </div>
        {capabilities.length ? (
          <div className="workspace-grid">
            {capabilities.map((item) => (
              <Link className="workspace-card" key={item.to} to={item.to}>
                <span className="workspace-tag">{item.tag}</span>
                <strong>{item.title}</strong>
                <p>{item.description}</p>
                <span className="workspace-link">Open workspace →</span>
              </Link>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-state-mark">CR</div>
            <strong>{tokens ? "No workspace permissions available" : "Sign in to begin"}</strong>
            <p>
              {tokens
                ? "Your account does not currently expose a managed workspace."
                : "Use your CRAM account to access datasets, GIS and governance tools."}
            </p>
          </div>
        )}
      </section>

      <section className="card system-foundation">
        <div>
          <p className="page-eyebrow">Current foundation</p>
          <h2>Gate 2 — Data Platform Complete</h2>
          <p>
            Catalogue, CSV preservation, versioning, validation, approval, publication and audit are
            available as the governed data-platform foundation.
          </p>
        </div>
        <StatusBadge value="Passed" />
      </section>
    </main>
  );
}
