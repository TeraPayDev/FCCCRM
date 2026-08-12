import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ApiError, api } from "../api/client";
import { saveTokens } from "../auth/session";
import { Icon } from "../components/Icon";
import "./auth.css";

export function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [username, setUsername] = useState("cramadmin");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState(
    searchParams.get("reason") === "expired" ? "Your session expired. Please sign in again." : "",
  );
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const tokens = await api.login(username, password);
      saveTokens(tokens);
      navigate("/");
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Login failed.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-page">
      <section className="login-brand-panel">
        <div className="login-brand">
          <div className="brand-mark login-mark">
            <span>CR</span>
          </div>
          <div>
            <strong>CRAM</strong>
            <span>Climate Risk Analytics Management Platform</span>
          </div>
        </div>
        <div className="login-message">
          <p className="eyebrow">Freetown City Council</p>
          <h1>Evidence-driven climate resilience starts here.</h1>
          <p>
            Secure access to governed climate data, spatial intelligence, risk analytics and
            municipal decision support.
          </p>
          <div className="login-features">
            <span>
              <Icon name="check" /> Governed climate data
            </span>
            <span>
              <Icon name="check" /> Spatial risk intelligence
            </span>
            <span>
              <Icon name="check" /> Traceable decisions
            </span>
          </div>
        </div>
        <div className="login-landscape" aria-hidden="true">
          <i />
          <i />
          <i />
        </div>
      </section>
      <section className="login-form-panel">
        <div className="auth-card">
          <div className="mobile-login-brand">
            <div className="brand-mark">
              <span>CR</span>
            </div>
            <strong>CRAM</strong>
          </div>
          <p className="eyebrow">Secure workspace</p>
          <h2>Welcome back</h2>
          <p className="auth-subtitle">Sign in with your authorized CRAM account.</p>
          <form onSubmit={submit}>
            <label>
              Username or email
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                placeholder="Enter username or email"
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                placeholder="Enter password"
              />
            </label>
            {message && <p className="auth-error">{message}</p>}
            <button type="submit" disabled={busy}>
              {busy ? "Signing in…" : "Sign in to CRAM"}
              <Icon name="arrow" />
            </button>
          </form>
          <div className="login-security">
            <span className="system-dot" /> Protected by CRAM role-based access control
          </div>
        </div>
      </section>
    </main>
  );
}
