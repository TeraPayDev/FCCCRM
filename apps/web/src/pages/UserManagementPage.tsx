import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type RoleSummary, type UserAdmin } from "../api/client";
import { loadTokens } from "../auth/session";
import { Icon } from "../components/Icon";
import { MetricTile } from "../components/analytics/Charts";
import { ModuleShell } from "../components/ModuleShell";
import "./users.css";

const roleLabels: Record<string, string> = {
  system_administrator: "System Administrator",
  fcc_administrator: "FCC Administrator",
  data_steward: "Data Steward",
  climate_analyst: "Climate Analyst",
  agency_analyst: "Agency Analyst",
  executive_user: "Executive User",
  public_user: "Public User",
};

export function UserManagementPage() {
  const navigate = useNavigate();
  const [users, setUsers] = useState<UserAdmin[]>([]);
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [message, setMessage] = useState("");
  const reload = async () => {
    const t = loadTokens();
    if (!t) {
      navigate("/login?reason=expired");
      return;
    }
    try {
      const [u, r] = await Promise.all([api.users(t.access_token), api.roles(t.access_token)]);
      setUsers(u);
      setRoles(r);
      setMessage("");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Unable to load users.");
    }
  };
  useEffect(() => {
    const timer = window.setTimeout(() => void reload(), 0);
    return () => window.clearTimeout(timer); // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const filtered = useMemo(
    () =>
      users.filter((u) => {
        const hay =
          `${u.username} ${u.email} ${u.organisation_name ?? ""} ${u.roles.join(" ")}`.toLowerCase();
        return (
          (!query || hay.includes(query.toLowerCase())) &&
          (status === "all" || (status === "active" ? u.is_active : !u.is_active))
        );
      }),
    [users, query, status],
  );
  const active = users.filter((u) => u.is_active).length;
  return (
    <ModuleShell
      title="User & Access Management"
      subtitle="Manage accounts, institutional ownership and role-based access from one governed workspace."
      eyebrow="Identity & access governance"
    >
      <div className="metric-row">
        <MetricTile label="Users" value={users.length} hint="Registered accounts" />
        <MetricTile label="Active" value={active} hint="Enabled accounts" tone="good" />
        <MetricTile label="Roles" value={roles.length} hint="RBAC profiles" />
        <MetricTile
          label="Disabled"
          value={users.length - active}
          hint="Access suspended"
          tone={users.length - active ? "warn" : "good"}
        />
      </div>
      <section className="user-list-card">
        <div className="user-list-toolbar">
          <div>
            <h2>Accounts</h2>
            <p>Search, review and edit CRAM users without changing data ownership history.</p>
          </div>
          <Link className="button icon-button" to="/users/new">
            <Icon name="plus" /> Add user
          </Link>
        </div>
        <div className="user-filters">
          <label className="search-field">
            <Icon name="search" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search name, email, institution or role"
            />
          </label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            aria-label="Filter user status"
          >
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="disabled">Disabled</option>
          </select>
        </div>
        {message && <div className="module-message">{message}</div>}
        <div className="table-wrap">
          <table className="module-table user-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Institution</th>
                <th>Role</th>
                <th>Status</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((u) => (
                <tr key={u.id}>
                  <td>
                    <div className="user-cell">
                      <span className="mini-avatar">{u.username.slice(0, 2).toUpperCase()}</span>
                      <div>
                        <strong>{u.username}</strong>
                        <small>{u.email}</small>
                      </div>
                    </div>
                  </td>
                  <td>{u.organisation_name ?? "No institution"}</td>
                  <td>
                    {u.roles.map((r) => (
                      <span className="role-chip" key={r}>
                        {roleLabels[r] ?? r}
                      </span>
                    ))}
                  </td>
                  <td>
                    <span className={`account-status ${u.is_active ? "active" : "inactive"}`}>
                      {u.is_active ? "Active" : "Disabled"}
                    </span>
                  </td>
                  <td>{new Date(u.created_at).toLocaleDateString()}</td>
                  <td>
                    <Link className="small-action icon-button" to={`/users/${u.id}/edit`}>
                      <Icon name="edit" /> Edit
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!filtered.length && (
          <div className="empty-inline">No users match the current filters.</div>
        )}
      </section>
    </ModuleShell>
  );
}
