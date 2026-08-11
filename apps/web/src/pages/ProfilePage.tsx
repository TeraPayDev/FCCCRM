import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type CurrentUser } from "../api/client";
import { clearTokens, loadTokens } from "../auth/session";
import { PageHeader, StatusBadge } from "../components/Page";
import "./auth.css";

function initials(value: string) {
  return value
    .split(/[\s._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function ProfilePage() {
  const navigate = useNavigate();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const tokens = loadTokens();
    if (!tokens) {
      navigate("/login");
      return;
    }
    let cancelled = false;
    api
      .me(tokens.access_token)
      .then((value) => {
        if (!cancelled) setUser(value);
      })
      .catch(() => {
        if (!cancelled) {
          clearTokens();
          setError("Your session is invalid or expired.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  async function logout() {
    const tokens = loadTokens();
    if (tokens) await api.logout(tokens.access_token);
    clearTokens();
    navigate("/login");
  }

  return (
    <main className="profile-page">
      <PageHeader
        eyebrow="Identity & access"
        title="My CRAM access"
        description="Review the account, institutional context, roles and effective permissions applied to this session."
        actions={
          <button type="button" onClick={() => void logout()}>
            Sign out
          </button>
        }
      />
      {error && <p className="notice notice-error">{error}</p>}
      {!user && !error && (
        <section className="card">
          <p>Loading account…</p>
        </section>
      )}
      {user && (
        <div className="profile-grid">
          <section className="card profile-summary">
            <div className="profile-identity">
              <div className="profile-avatar">{initials(user.username)}</div>
              <div>
                <h2>{user.username}</h2>
                <p>{user.email}</p>
              </div>
            </div>
            <dl className="profile-list">
              <dt>Account status</dt>
              <dd>
                <StatusBadge value="Active" />
              </dd>
              <dt>Organisation</dt>
              <dd>{user.organisation_id ?? "Not assigned"}</dd>
              <dt>Roles</dt>
              <dd>{user.roles.map((role) => role.replaceAll("_", " ")).join(", ") || "None"}</dd>
            </dl>
          </section>
          <section className="card">
            <div className="card-header">
              <div>
                <h2>Effective permissions</h2>
                <p className="card-subtitle">
                  These server-issued permissions determine what CRAM actions are available.
                </p>
              </div>
              <span className="status-badge">{user.permissions.length} permissions</span>
            </div>
            <div className="permission-grid">
              {user.permissions.map((permission) => (
                <span className="permission-pill" key={permission}>
                  {permission}
                </span>
              ))}
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
