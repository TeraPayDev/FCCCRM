import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type CurrentUser } from "../api/client";
import { clearTokens, loadTokens } from "../auth/session";
import { Icon } from "../components/Icon";
import "./auth.css";
import "./profile.css";

function humanize(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function ProfilePage() {
  const navigate = useNavigate();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [error, setError] = useState("");
  const [permissionsOpen, setPermissionsOpen] = useState(false);

  useEffect(() => {
    const tokens = loadTokens();
    if (!tokens) {
      navigate("/login");
      return;
    }
    api
      .me(tokens.access_token)
      .then(setUser)
      .catch(() => {
        clearTokens();
        setError("Your session is invalid or expired.");
      });
  }, [navigate]);

  const initials = useMemo(() => {
    if (!user) return "CR";
    return user.username
      .split(/[._-]/)
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();
  }, [user]);

  async function logout() {
    const tokens = loadTokens();
    try {
      if (tokens) await api.logout(tokens.access_token);
    } finally {
      clearTokens();
      navigate("/login");
    }
  }

  return (
    <main className="profile-page">
      <section className="profile-hero">
        <div className="profile-avatar-large">{initials}</div>
        <div className="profile-hero-copy">
          <span className="eyebrow">Identity & access</span>
          <h1>{user?.username ?? "CRAM account"}</h1>
          <p>Your account, institutional access and effective CRAM permissions.</p>
        </div>
        <div className="profile-status">
          <span /> Active session
        </div>
      </section>

      {error && <div className="auth-error">{error}</div>}
      {!user && !error && <div className="profile-loading">Loading account…</div>}

      {user && (
        <div className="profile-layout">
          <section className="profile-card">
            <div className="profile-card-head">
              <div>
                <span className="eyebrow">Account</span>
                <h2>Profile details</h2>
              </div>
              <Icon name="user" />
            </div>
            <dl className="profile-details">
              <div>
                <dt>Username</dt>
                <dd>{user.username}</dd>
              </div>
              <div>
                <dt>Email address</dt>
                <dd>{user.email}</dd>
              </div>
              <div>
                <dt>Institution assignment</dt>
                <dd>
                  {user.organisation_id ? "Institution-linked account" : "No institution assigned"}
                </dd>
              </div>
              <div>
                <dt>Account state</dt>
                <dd>
                  <span className="profile-badge good">Enabled</span>
                </dd>
              </div>
            </dl>
          </section>

          <section className="profile-card">
            <div className="profile-card-head">
              <div>
                <span className="eyebrow">Access</span>
                <h2>Role membership</h2>
              </div>
              <Icon name="shield" />
            </div>
            <div className="profile-role-list">
              {user.roles.length ? (
                user.roles.map((role) => <span key={role}>{humanize(role)}</span>)
              ) : (
                <p>No roles assigned.</p>
              )}
            </div>
            <p className="profile-note">
              Roles determine which CRAM modules and governance actions are available to this
              account.
            </p>
          </section>

          <section className="profile-card profile-permissions-card">
            <button
              className="profile-permissions-toggle"
              onClick={() => setPermissionsOpen((value) => !value)}
            >
              <span>
                <span className="eyebrow">Authorization</span>
                <strong>Effective permissions</strong>
                <small>{user.permissions.length} permissions currently granted</small>
              </span>
              <Icon name="chevron" className={permissionsOpen ? "rotated" : ""} />
            </button>
            {permissionsOpen && (
              <div className="profile-permissions">
                {user.permissions.map((permission) => (
                  <span key={permission}>{permission}</span>
                ))}
              </div>
            )}
          </section>

          <section className="profile-card profile-security-card">
            <div className="profile-card-head">
              <div>
                <span className="eyebrow">Security</span>
                <h2>Session & account</h2>
              </div>
              <Icon name="activity" />
            </div>
            <div className="profile-security-row">
              <span>
                <strong>Authenticated session</strong>
                <small>
                  CRAM automatically renews valid sessions and returns expired sessions to sign-in.
                </small>
              </span>
              <span className="profile-badge good">Protected</span>
            </div>
            <div className="profile-actions">
              {user.permissions.includes("users.manage") && (
                <button className="secondary-action" onClick={() => navigate("/users")}>
                  <Icon name="shield" /> Access management
                </button>
              )}
              <button className="danger-secondary" onClick={() => void logout()}>
                <Icon name="logout" /> Sign out
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
