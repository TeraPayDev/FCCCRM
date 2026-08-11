import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type CurrentUser } from "../api/client";
import { clearTokens, loadTokens } from "../auth/session";
import "./auth.css";

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
    api
      .me(tokens.access_token)
      .then(setUser)
      .catch(() => {
        clearTokens();
        setError("Your session is invalid or expired.");
      });
  }, [navigate]);

  async function logout() {
    const tokens = loadTokens();
    if (tokens) await api.logout(tokens.access_token);
    clearTokens();
    navigate("/login");
  }

  return (
    <main className="auth-page">
      <section className="auth-card auth-profile">
        <h1>CRAM Identity</h1>
        {error && <p className="auth-error">{error}</p>}
        {!user && !error && <p>Loading account...</p>}
        {user && (
          <>
            <dl>
              <dt>Username</dt>
              <dd>{user.username}</dd>
              <dt>Email</dt>
              <dd>{user.email}</dd>
              <dt>Roles</dt>
              <dd>{user.roles.join(", ") || "None"}</dd>
              <dt>Permissions</dt>
              <dd>{user.permissions.join(", ") || "None"}</dd>
            </dl>
            <button type="button" onClick={logout}>
              Sign out
            </button>
            {user.permissions.includes("users.manage") && (
              <Link to="/organisations">Organisation administration</Link>
            )}
            {user.permissions.includes("audit.read") && <Link to="/audit">Audit viewer</Link>}
            {user.permissions.includes("gis.read") && <Link to="/map">GIS map</Link>}
          </>
        )}
        <Link to="/">System status</Link>
      </section>
    </main>
  );
}
