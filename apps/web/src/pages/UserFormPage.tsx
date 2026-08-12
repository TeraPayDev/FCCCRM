import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, type Organisation, type RoleSummary, type UserAdmin } from "../api/client";
import { loadTokens } from "../auth/session";
import { Icon } from "../components/Icon";
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
export function UserFormPage() {
  const { userId } = useParams();
  const editing = Boolean(userId);
  const navigate = useNavigate();
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [orgs, setOrgs] = useState<Organisation[]>([]);
  const [current, setCurrent] = useState<UserAdmin | null>(null);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [organisationId, setOrganisationId] = useState("");
  const [roleCode, setRoleCode] = useState("climate_analyst");
  const [active, setActive] = useState(true);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const t = loadTokens();
    if (!t) {
      navigate("/login?reason=expired");
      return;
    }
    void Promise.all([
      api.roles(t.access_token),
      api.organisations(t.access_token),
      userId ? api.user(t.access_token, userId) : Promise.resolve(null),
    ])
      .then(([r, o, u]) => {
        setRoles(r);
        setOrgs(o);
        if (u) {
          setCurrent(u);
          setUsername(u.username);
          setEmail(u.email);
          setOrganisationId(u.organisation_id ?? "");
          setRoleCode(u.roles[0] ?? "climate_analyst");
          setActive(u.is_active);
        }
      })
      .catch((e) => setMessage(e instanceof Error ? e.message : "Unable to load account."));
  }, [navigate, userId]);
  async function submit(e: FormEvent) {
    e.preventDefault();
    const t = loadTokens();
    if (!t) return;
    setBusy(true);
    setMessage("");
    try {
      if (editing && userId) {
        await api.updateUser(t.access_token, userId, {
          email,
          organisation_id: organisationId || null,
          role_codes: [roleCode],
          is_active: active,
          ...(password ? { password } : {}),
        });
      } else {
        await api.createUser(t.access_token, {
          username,
          email,
          password,
          organisation_id: organisationId || null,
          role_codes: [roleCode],
        });
      }
      navigate("/users");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to save user.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <ModuleShell
      title={editing ? `Edit ${current?.username ?? "user"}` : "Create CRAM User"}
      subtitle={
        editing
          ? "Update institutional ownership, role, status or reset the user's password."
          : "Create a role-specific account for an FCC, partner-agency, analyst or executive workflow."
      }
      eyebrow="Identity & access governance"
      actions={
        <Link className="button secondary-button icon-button" to="/users">
          <Icon name="arrow" /> Back to users
        </Link>
      }
    >
      <section className="user-form-layout">
        <form className="user-form-card" onSubmit={submit}>
          <div className="form-section-heading">
            <span className="form-icon">
              <Icon name="user" />
            </span>
            <div>
              <h2>Account details</h2>
              <p>Use named accounts so audit events remain attributable.</p>
            </div>
          </div>
          {message && <div className="module-message">{message}</div>}
          <div className="form-grid">
            <label>
              Username
              <input
                value={username}
                disabled={editing}
                onChange={(e) => setUsername(e.target.value)}
                required
                minLength={3}
                placeholder="e.g. fcc.analyst"
              />
            </label>
            <label>
              Email address
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="name@institution.gov.sl"
              />
            </label>
            <label>
              Institution
              <select value={organisationId} onChange={(e) => setOrganisationId(e.target.value)}>
                <option value="">No institution</option>
                {orgs
                  .filter((o) => o.is_active)
                  .map((o) => (
                    <option value={o.id} key={o.id}>
                      {o.code} — {o.name}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              Primary role
              <select value={roleCode} onChange={(e) => setRoleCode(e.target.value)}>
                {roles.map((r) => (
                  <option value={r.code} key={r.code}>
                    {roleLabels[r.code] ?? r.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-wide">
              {editing ? "New password (optional)" : "Temporary password"}
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required={!editing}
                minLength={12}
                placeholder={
                  editing ? "Leave blank to keep current password" : "Minimum 12 characters"
                }
              />
            </label>
            {editing && (
              <label className="toggle-row form-wide">
                <input
                  type="checkbox"
                  checked={active}
                  onChange={(e) => setActive(e.target.checked)}
                />
                <span>
                  <strong>Account active</strong>
                  <small>Disabling the account invalidates future authenticated access.</small>
                </span>
              </label>
            )}
          </div>
          <div className="form-actions">
            <button disabled={busy} className="icon-button" type="submit">
              <Icon name="check" />
              {busy ? "Saving…" : editing ? "Save changes" : "Create user"}
            </button>
            <Link className="button secondary-button" to="/users">
              Cancel
            </Link>
          </div>
        </form>
        <aside className="access-guide">
          <div className="form-icon">
            <Icon name="shield" />
          </div>
          <h3>Role guidance</h3>
          <p>
            Assign the narrowest role that supports the user's job. CRAM navigation and API access
            are permission-aware.
          </p>
          <ul>
            <li>
              <strong>Data Steward</strong> manages datasets and validation.
            </li>
            <li>
              <strong>Climate Analyst</strong> uses GIS and analytics.
            </li>
            <li>
              <strong>Agency Analyst</strong> supports partner-institution workflows.
            </li>
            <li>
              <strong>Executive User</strong> focuses on dashboards and reports.
            </li>
            <li>
              <strong>Administrators</strong> manage governance and access.
            </li>
          </ul>
        </aside>
      </section>
    </ModuleShell>
  );
}
