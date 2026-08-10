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
      navigate("/profile");
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Login failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <h1>CRAM Sign In</h1>
        <p>Authenticate with your CRAM account.</p>
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
          {message && <p className="auth-error">{message}</p>}
          <button type="submit" disabled={busy}>
            {busy ? "Signing in..." : "Sign in"}
          </button>
        </form>
        <Link to="/">Return to system status</Link>
      </section>
    </main>
  );
}
