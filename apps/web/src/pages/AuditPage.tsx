import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { milestone78Api, type AuditEvent } from "../api/client";
import { loadTokens } from "../auth/session";
import { Icon } from "../components/Icon";
import "./audit.css";

export function AuditPage() {
  const navigate = useNavigate();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [action, setAction] = useState("");
  const [resourceType, setResourceType] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [error, setError] = useState("");

  async function load(query = "") {
    const tokens = loadTokens();
    if (!tokens) return navigate("/login");
    try {
      setEvents(await milestone78Api.auditEvents(tokens.access_token, query));
      setError("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load audit records.");
    }
  }
  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, []);
  function applyFilters() {
    const params = new URLSearchParams();
    if (action.trim()) params.set("action", action.trim());
    if (resourceType.trim()) params.set("resource_type", resourceType.trim());
    if (from) params.set("occurred_from", new Date(`${from}T00:00:00`).toISOString());
    if (to) params.set("occurred_to", new Date(`${to}T23:59:59`).toISOString());
    void load(params.toString());
  }
  function reset() {
    setAction("");
    setResourceType("");
    setFrom("");
    setTo("");
    void load();
  }

  return (
    <main className="audit-page">
      <section className="audit-panel">
        <header>
          <div>
            <p className="eyebrow">Security & governance</p>
            <h1>CRAM Audit Trail</h1>
            <p>
              Append-only evidence of authentication, data lifecycle, administration and operational
              actions.
            </p>
          </div>
          <button className="secondary-action icon-button" onClick={() => void load()}>
            <Icon name="refresh" /> Refresh
          </button>
        </header>
        <div className="audit-filters">
          <label>
            Action
            <input
              value={action}
              onChange={(e) => setAction(e.target.value)}
              placeholder="dataset.publish"
            />
          </label>
          <label>
            Resource type
            <input
              value={resourceType}
              onChange={(e) => setResourceType(e.target.value)}
              placeholder="dataset_version"
            />
          </label>
          <label>
            From
            <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
          </label>
          <label>
            To
            <input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
          </label>
          <button className="icon-button" onClick={applyFilters}>
            <Icon name="filter" /> Apply filters
          </button>
          <button className="secondary-action" onClick={reset}>
            Reset
          </button>
        </div>
        {error && <p className="audit-error">{error}</p>}
        <div className="audit-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Action</th>
                <th>Resource</th>
                <th>Actor</th>
                <th>Organisation</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.id}>
                  <td>{new Date(event.occurred_at).toLocaleString()}</td>
                  <td>
                    <span className="audit-action">{event.action}</span>
                  </td>
                  <td>
                    {event.resource_type}
                    {event.resource_id ? ` / ${event.resource_id}` : ""}
                  </td>
                  <td>{event.actor_user_id ?? "System"}</td>
                  <td>{event.organisation_id ?? "—"}</td>
                  <td>
                    <details className="audit-details">
                      <summary>View</summary>
                      <code>{JSON.stringify(event.details, null, 2)}</code>
                    </details>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
