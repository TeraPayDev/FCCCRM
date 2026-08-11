import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { milestone78Api, type AuditEvent } from "../api/client";
import { loadTokens } from "../auth/session";
import "./audit.css";

export function AuditPage() {
  const navigate = useNavigate();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [action, setAction] = useState("");
  const [resourceType, setResourceType] = useState("");
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
    void load(params.toString());
  }

  return (
    <main className="audit-page">
      <section className="audit-panel">
        <header>
          <div>
            <h1>CRAM Audit</h1>
            <p>Append-only security and governance activity.</p>
          </div>
          <Link to="/profile">Profile</Link>
        </header>
        <div className="audit-filters">
          <label>
            Action
            <input
              value={action}
              onChange={(e) => setAction(e.target.value)}
              placeholder="organisation.update"
            />
          </label>
          <label>
            Resource type
            <input
              value={resourceType}
              onChange={(e) => setResourceType(e.target.value)}
              placeholder="organisation"
            />
          </label>
          <button type="button" onClick={applyFilters}>
            Filter
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
                  <td>{event.action}</td>
                  <td>
                    {event.resource_type}
                    {event.resource_id ? ` / ${event.resource_id}` : ""}
                  </td>
                  <td>{event.actor_user_id ?? "System/unknown"}</td>
                  <td>{event.organisation_id ?? "—"}</td>
                  <td>
                    <code>{JSON.stringify(event.details)}</code>
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
