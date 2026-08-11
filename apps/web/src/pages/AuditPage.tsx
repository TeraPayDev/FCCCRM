import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { milestone78Api, type AuditEvent } from "../api/client";
import { loadTokens } from "../auth/session";
import { EmptyState, PageHeader } from "../components/Page";
import "./audit.css";

export function AuditPage() {
  const navigate = useNavigate();

  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [action, setAction] = useState("");
  const [resourceType, setResourceType] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(
    async (query = "") => {
      const tokens = loadTokens();

      if (!tokens) {
        navigate("/login");
        return;
      }

      setLoading(true);

      try {
        const auditEvents = await milestone78Api.auditEvents(tokens.access_token, query);

        setEvents(auditEvents);
        setError("");
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Unable to load audit records.");
      } finally {
        setLoading(false);
      }
    },
    [navigate],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);

    return () => {
      window.clearTimeout(timer);
    };
  }, [load]);

  function applyFilters() {
    const params = new URLSearchParams();

    if (action.trim()) {
      params.set("action", action.trim());
    }

    if (resourceType.trim()) {
      params.set("resource_type", resourceType.trim());
    }

    void load(params.toString());
  }

  function clearFilters() {
    setAction("");
    setResourceType("");
    void load();
  }

  return (
    <main className="audit-page">
      <PageHeader
        eyebrow="Governance"
        title="Audit trail"
        description="Append-oriented security, identity and data-governance activity with actor and resource traceability."
      />

      <section className="audit-panel">
        <div className="audit-filters">
          <label>
            Action
            <input
              value={action}
              onChange={(event) => setAction(event.target.value)}
              placeholder="dataset.publish"
            />
          </label>

          <label>
            Resource type
            <input
              value={resourceType}
              onChange={(event) => setResourceType(event.target.value)}
              placeholder="dataset_version"
            />
          </label>

          <button className="button-primary" type="button" onClick={applyFilters}>
            Apply filters
          </button>

          <button className="text-button" type="button" onClick={clearFilters}>
            Clear
          </button>
        </div>

        {error && <p className="notice notice-error">{error}</p>}

        {loading ? (
          <p className="audit-loading">Loading audit activity…</p>
        ) : events.length ? (
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
                    <td className="audit-time">{new Date(event.occurred_at).toLocaleString()}</td>

                    <td>
                      <span className="audit-action">{event.action}</span>
                    </td>

                    <td>
                      {event.resource_type}

                      {event.resource_id ? (
                        <>
                          <br />
                          <code>{event.resource_id.slice(0, 8)}…</code>
                        </>
                      ) : null}
                    </td>

                    <td>
                      <code>
                        {event.actor_user_id?.slice(0, 8) ?? "System"}
                        {event.actor_user_id ? "…" : ""}
                      </code>
                    </td>

                    <td>
                      {event.organisation_id ? (
                        <code>{event.organisation_id.slice(0, 8)}…</code>
                      ) : (
                        "—"
                      )}
                    </td>

                    <td>
                      <details>
                        <summary>View metadata</summary>
                        <pre>{JSON.stringify(event.details, null, 2)}</pre>
                      </details>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No audit events found"
            description="Adjust the filters to broaden the audit query."
          />
        )}
      </section>
    </main>
  );
}
