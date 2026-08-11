import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { clearTokens, loadTokens } from "../auth/session";
import "./app-shell.css";

type IconName =
  "home" | "data" | "approval" | "map" | "organisation" | "audit" | "profile" | "status";

function Icon({ name }: { name: IconName }) {
  const paths: Record<IconName, ReactNode> = {
    home: (
      <>
        <path d="M3 11.5 12 4l9 7.5" />
        <path d="M5.5 10.5V20h13v-9.5" />
        <path d="M9 20v-6h6v6" />
      </>
    ),
    data: (
      <>
        <ellipse cx="12" cy="5" rx="7.5" ry="3" />
        <path d="M4.5 5v6c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3V5" />
        <path d="M4.5 11v6c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3v-6" />
      </>
    ),
    approval: (
      <>
        <path d="M8 3h8l4 4v14H4V3h4Z" />
        <path d="M8 3v5h8V3" />
        <path d="m8 15 2.2 2.2L16 11.5" />
      </>
    ),
    map: (
      <>
        <path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3Z" />
        <path d="M9 3v15M15 6v15" />
      </>
    ),
    organisation: (
      <>
        <circle cx="12" cy="7" r="3" />
        <path d="M6.5 20v-2.2A4.8 4.8 0 0 1 11.3 13h1.4a4.8 4.8 0 0 1 4.8 4.8V20" />
        <path d="M4 8.5h3M17 8.5h3" />
      </>
    ),
    audit: (
      <>
        <path d="M5 3h14v18H5z" />
        <path d="M8 7h8M8 11h8M8 15h5" />
        <path d="m15 17 1.5 1.5L20 15" />
      </>
    ),
    profile: (
      <>
        <circle cx="12" cy="8" r="4" />
        <path d="M4.5 21a7.5 7.5 0 0 1 15 0" />
      </>
    ),
    status: (
      <>
        <path d="M4 13h3l2-5 4 10 2-5h5" />
        <circle cx="12" cy="12" r="10" />
      </>
    ),
  };
  return (
    <svg
      className="nav-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  );
}

function initials(value: string) {
  return value
    .split(/[\s._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function AppShell() {
  const navigate = useNavigate();
  const tokens = loadTokens();
  const me = useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => api.me(tokens!.access_token),
    enabled: Boolean(tokens),
    retry: false,
  });

  const permissions = me.data?.permissions ?? [];
  const can = (permission: string) => permissions.includes(permission);

  async function signOut() {
    if (tokens) {
      try {
        await api.logout(tokens.access_token);
      } catch {
        // Clearing the local session remains the authoritative client-side logout action.
      }
    }
    clearTokens();
    navigate("/login");
  }

  const primary = [
    { to: "/", label: "Overview", icon: "home" as const, show: true },
    { to: "/datasets", label: "Data catalogue", icon: "data" as const, show: can("datasets.read") },
    {
      to: "/approvals",
      label: "Approval queue",
      icon: "approval" as const,
      show: can("datasets.approve"),
    },
    { to: "/map", label: "GIS map", icon: "map" as const, show: can("gis.read") },
  ];

  const governance = [
    {
      to: "/organisations",
      label: "Organisations",
      icon: "organisation" as const,
      show: can("users.manage"),
    },
    { to: "/audit", label: "Audit trail", icon: "audit" as const, show: can("audit.read") },
  ];

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="brand-block">
          <div className="brand-mark" aria-hidden="true">
            <span>CR</span>
          </div>
          <div>
            <strong>CRAM</strong>
            <span>Climate Risk Analytics</span>
          </div>
        </div>

        <nav className="sidebar-nav" aria-label="Primary navigation">
          <p className="nav-section-label">Workspace</p>
          {primary
            .filter((item) => item.show)
            .map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}
              >
                <Icon name={item.icon} />
                <span>{item.label}</span>
              </NavLink>
            ))}

          {governance.some((item) => item.show) && (
            <p className="nav-section-label nav-section-spaced">Governance</p>
          )}
          {governance
            .filter((item) => item.show)
            .map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}
              >
                <Icon name={item.icon} />
                <span>{item.label}</span>
              </NavLink>
            ))}
        </nav>

        <div className="sidebar-footer">
          <NavLink
            to="/profile"
            className={({ isActive }) => `profile-chip${isActive ? " active" : ""}`}
          >
            <span className="avatar">{initials(me.data?.username ?? "CR")}</span>
            <span className="profile-chip-copy">
              <strong>{me.data?.username ?? (tokens ? "Loading account" : "Guest")}</strong>
              <small>{me.data?.roles[0]?.replaceAll("_", " ") ?? "CRAM workspace"}</small>
            </span>
          </NavLink>
          {tokens ? (
            <button
              className="text-button sidebar-signout"
              type="button"
              onClick={() => void signOut()}
            >
              Sign out
            </button>
          ) : (
            <NavLink className="button button-primary sidebar-login" to="/login">
              Sign in
            </NavLink>
          )}
        </div>
      </aside>

      <div className="app-main">
        <header className="app-topbar">
          <div className="topbar-product">
            <span className="topbar-kicker">Freetown City Council</span>
            <strong>Climate Risk Analytics Management Platform</strong>
          </div>
          <div className="topbar-status">
            <span className="environment-pill">Development</span>
            <NavLink className="topbar-link" to="/about">
              About
            </NavLink>
          </div>
        </header>
        <div className="app-content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
