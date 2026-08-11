import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Icon, type IconName } from "./Icon";
import "./app-layout.css";

const primary = [
  ["Overview", "/", "home"],
  ["Data Catalogue", "/datasets", "data"],
  ["GIS Explorer", "/map", "map"],
  ["Processing", "/processing", "processing"],
  ["Heat", "/heat", "heat"],
  ["Flood", "/flood", "flood"],
  ["Trees", "/trees", "trees"],
  ["Vulnerability", "/vulnerability", "vulnerability"],
] as const;
const operations = [
  ["Citizen Reports", "/citizen-reports", "citizen"],
  ["Notifications", "/notifications", "bell"],
  ["Dashboards", "/dashboards", "chart"],
  ["Reporting", "/reports", "report"],
  ["Knowledge Hub", "/knowledge", "knowledge"],
] as const;
const governance = [
  ["Organisations", "/organisations", "organisation"],
  ["Approvals", "/approvals", "check"],
  ["Audit Trail", "/audit", "audit"],
  ["Administration", "/administration", "settings"],
  ["Advanced Analytics", "/analytics", "activity"],
] as const;

function NavGroup({
  title,
  items,
}: {
  title: string;
  items: readonly (readonly [string, string, IconName])[];
}) {
  return (
    <div className="nav-group">
      <div className="nav-label">{title}</div>
      {items.map(([label, to, icon]) => (
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
  const location = useLocation();
  const pageName =
    [...primary, ...operations, ...governance].find((item) => location.pathname === item[1])?.[0] ??
    (location.pathname.startsWith("/datasets/") ? "Dataset Details" : "CRAM Platform");
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
          <NavGroup title="Platform" items={primary} />
          <NavGroup title="Operations" items={operations} />
          <NavGroup title="Governance" items={governance} />
        </nav>
        <div className="sidebar-footer">
          <span className="system-dot" /> Platform operational <small>CRAM v0.1.0</small>
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
            <NavLink to="/profile" className="profile-chip">
              <div className="avatar">CA</div>
              <div>
                <strong>CRAM Admin</strong>
                <span>Administrator</span>
              </div>
            </NavLink>
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
    </div>
  );
}
