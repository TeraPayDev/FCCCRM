import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { api, type CurrentUser } from "../api/client";
import { clearTokens, loadTokens } from "../auth/session";
import { Icon, type IconName } from "./Icon";
import { AssistantWidget } from "./AssistantWidget";
import "./app-layout.css";

type NavItem = readonly [string, string, IconName, string?];
const primary: readonly NavItem[] = [
  ["Overview", "/", "home"],
  ["Data Catalogue", "/datasets", "data", "datasets.read"],
  ["GIS Explorer", "/map", "map", "gis.read"],
  ["Processing", "/processing", "processing", "analytics.read"],
  ["Heat", "/heat", "heat", "analytics.read"],
  ["Flood", "/flood", "flood", "analytics.read"],
  ["Trees", "/trees", "trees", "analytics.read"],
  ["Vulnerability", "/vulnerability", "vulnerability", "analytics.read"],
];
const operations: readonly NavItem[] = [
  ["Citizen Reports", "/citizen-reports", "citizen", "citizen_reports.read"],
  ["Notifications", "/notifications", "bell"],
  ["Dashboards", "/dashboards", "chart"],
  ["Reporting", "/reports", "report", "reports.read"],
  ["Knowledge Hub", "/knowledge", "knowledge", "reports.read"],
];
const governance: readonly NavItem[] = [
  ["Organisations", "/organisations", "organisation", "users.read"],
  ["User Management", "/users", "user", "users.read"],
  ["Approvals", "/approvals", "check", "datasets.approve"],
  ["Audit Trail", "/audit", "audit", "audit.read"],
  ["Administration", "/administration", "settings", "users.manage"],
  ["Advanced Analytics", "/analytics", "activity", "analytics.read"],
];
function NavGroup({
  title,
  items,
  user,
}: {
  title: string;
  items: readonly NavItem[];
  user: CurrentUser | null;
}) {
  const allowed = items.filter(
    ([, , , permission]) => !permission || user?.permissions.includes(permission),
  );
  if (!allowed.length) return null;
  return (
    <div className="nav-group">
      <div className="nav-label">{title}</div>
      {allowed.map(([label, to, icon]) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          className={({ isActive }) => `side-link${isActive ? " active" : ""}`}
        >
          <Icon name={icon} />
          <span>{label}</span>
        </NavLink>
      ))}
    </div>
  );
}
export function AppLayout() {
  const [open, setOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const location = useLocation();
  const navigate = useNavigate();
  const menuRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const t = loadTokens();
    if (t)
      void api
        .me(t.access_token)
        .then(setUser)
        .catch(() => undefined);
  }, []);
  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setProfileOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);
  const all = [...primary, ...operations, ...governance];
  const pageName =
    all.find((i) => location.pathname === i[1])?.[0] ??
    (location.pathname.startsWith("/datasets/")
      ? "Dataset Details"
      : location.pathname.startsWith("/users/")
        ? "User Management"
        : location.pathname === "/system-status"
          ? "System Status"
          : "CRAM Platform");
  const role = user?.roles[0]?.replaceAll("_", " ") ?? "Authenticated user";
  const initials = (user?.username ?? "CRAM")
    .split(/[._-]/)
    .map((x) => x[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  async function logout() {
    const t = loadTokens();
    try {
      if (t) await api.logout(t.access_token);
    } finally {
      clearTokens();
      navigate("/login");
    }
  }
  return (
    <div className="app-frame">
      <aside className={`app-sidebar${open ? " open" : ""}`}>
        <div className="brand-panel">
          <div className="brand-mark">
            <span>CR</span>
          </div>
          <div>
            <strong>CRAM</strong>
            <small>Climate Risk Analytics</small>
          </div>
          <button className="mobile-close" onClick={() => setOpen(false)} aria-label="Close menu">
            <Icon name="close" />
          </button>
        </div>
        <nav className="side-nav" onClick={() => setOpen(false)}>
          <NavGroup title="Platform" items={primary} user={user} />
          <NavGroup title="Operations" items={operations} user={user} />
          <NavGroup title="Governance" items={governance} user={user} />
        </nav>
        <div className="sidebar-footer">
          <span className="system-dot" /> Platform operational{" "}
          <small>Decision-support prototype</small>
        </div>
      </aside>
      {open && (
        <button
          className="sidebar-scrim"
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
        />
      )}
      <div className="app-main">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="menu-button"
              onClick={() => setOpen(true)}
              aria-label="Open navigation"
            >
              <Icon name="menu" />
            </button>
            <div>
              <span className="topbar-kicker">Freetown City Council</span>
              <strong>{pageName}</strong>
            </div>
          </div>
          <div className="topbar-actions">
            <div className="environment-pill">
              <span /> Development
            </div>
            <div className="profile-menu" ref={menuRef}>
              <button
                className="profile-chip"
                onClick={() => setProfileOpen((v) => !v)}
                aria-expanded={profileOpen}
              >
                <div className="avatar">{initials}</div>
                <div>
                  <strong>{user?.username ?? "CRAM user"}</strong>
                  <span>{role}</span>
                </div>
                <Icon name="chevron" className="profile-chevron" />
              </button>
              {profileOpen && (
                <div className="profile-dropdown">
                  <div className="profile-dropdown-head">
                    <div className="avatar">{initials}</div>
                    <div>
                      <strong>{user?.username}</strong>
                      <span>{user?.email}</span>
                      <small>{role}</small>
                    </div>
                  </div>
                  <NavLink to="/profile" onClick={() => setProfileOpen(false)}>
                    <Icon name="user" /> My profile
                  </NavLink>
                  <NavLink to="/system-status" onClick={() => setProfileOpen(false)}>
                    <Icon name="activity" /> System status
                  </NavLink>
                  {user?.permissions.includes("users.manage") && (
                    <NavLink to="/users" onClick={() => setProfileOpen(false)}>
                      <Icon name="shield" /> Access management
                    </NavLink>
                  )}
                  <div className="profile-divider" />
                  <button onClick={() => void logout()}>
                    <Icon name="logout" /> Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>
        <div className="content-shell">
          <Outlet />
        </div>
        <footer className="app-footer">
          <span>Climate Risk Analytics Management Platform</span>
          <span>Freetown City Council • Yestech Solutions SL Ltd</span>
        </footer>
      </div>

      <AssistantWidget />
    </div>
  );
}
