import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, api } from "../api/client";
import { saveTokens } from "../auth/session";
import "./auth.css";

export function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("cramadmin");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
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
    <main className="login-layout">
      <section className="login-brand-panel">
        <div className="login-brand-mark">CR</div>
        <p className="login-kicker">Freetown City Council</p>
        <h1>Climate data, governance and spatial intelligence in one workspace.</h1>
        <p>
          CRAM connects institutional ownership, versioned data, validation, approval, GIS and audit
          controls through a single governed platform.
        </p>
        <div className="login-foundation">
          <span>Gate 2</span>
          <strong>Data Platform Complete</strong>
        </div>
      </section>
      <section className="login-form-panel">
        <div className="auth-card">
          <p className="page-eyebrow">Secure workspace</p>
          <h2>Sign in to CRAM</h2>
          <p className="auth-intro">
            Use your assigned CRAM account. Access is determined by your effective permissions and
            organisation.
          </p>
          <form onSubmit={submit}>
            <label>
              Username or email
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </label>
            {message && <p className="notice notice-error">{message}</p>}
            <button className="button-primary" type="submit" disabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <Link className="auth-back" to="/">
            ← Return to platform overview
          </Link>
        </div>
      </section>
    </main>
  );
}
