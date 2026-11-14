
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Activity, Bell, Building2, ChevronDown, CircleHelp,
  ClipboardList, FileText, LayoutDashboard, Map,
  MapPinned, Menu, Search, Settings, ShieldAlert,
  ShieldCheck, Sparkles, Users, X, Mic
} from "lucide-react";
import "./AppLayout.css";

const citizenNav = [
  { label: "Overview", path: "/citizen/dashboard", icon: LayoutDashboard },
  { label: "Snap & Speak", path: "/citizen/report", icon: Mic },
  { label: "My Complaints", path: "/citizen/complaints", icon: ClipboardList },
  { label: "City Projects", path: "/citizen/projects", icon: Building2 },
  { label: "City Map", path: "/citizen/map", icon: Map },
  { label: "Safety & Alerts", path: "/citizen/safety", icon: ShieldAlert },
];

const officialNav = [
  { label: "City Overview", path: "/official/dashboard", icon: LayoutDashboard },
  { label: "Complaints", path: "/official/complaints", icon: ClipboardList },
  { label: "Departments", path: "/official/departments", icon: Building2 },
  { label: "Analytics", path: "/official/analytics", icon: Activity },
  { label: "Public Alerts", path: "/official/alerts", icon: ShieldAlert },
];

export default function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();

  const isOfficial = location.pathname.startsWith("/official");
  const navItems = isOfficial ? officialNav : citizenNav;
  const role = isOfficial ? "Government Official" : "Citizen";

  const [theme, setTheme] = useState(
    () => localStorage.getItem("smartland-theme") || "light"
  );
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("smartland-theme", theme);
  }, [theme]);

  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  return (
    <div className={`smart-shell ${theme}-theme`}>
      <div className="shell-atmosphere" />

      <header className="shell-topbar">
        <Link to="/" className="shell-brand">
          <span className="shell-brand-mark">S</span>
          <span className="shell-brand-name">
            SMART LAND<span>.</span>
            <small>GOA'S DIGITAL CITY</small>
          </span>
        </Link>

        <nav className="shell-topnav">
          <span className="shell-live">
            <i /> CITY INTELLIGENCE
          </span>
          <span className="shell-topnav-divider" />
          <span className="shell-location">GOA, INDIA</span>
        </nav>

        <div className="shell-top-actions">
          <button className="shell-icon-button" aria-label="Search">
            <Search size={17} />
          </button>
          <button className="shell-icon-button" aria-label="Notifications">
            <Bell size={17} />
            <i className="notification-dot" />
          </button>
          <button
            className="shell-profile"
            onClick={() => navigate(isOfficial ? "/official/settings" : "/citizen/settings")}
          >
            <span className="shell-avatar">{isOfficial ? "O" : "C"}</span>
            <span className="shell-profile-copy">
              <strong>{isOfficial ? "Official account" : "Citizen account"}</strong>
              <small>{role}</small>
            </span>
            <ChevronDown size={14} />
          </button>
          <button
            className="shell-mobile-menu"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="Toggle navigation"
          >
            {sidebarOpen ? <X /> : <Menu />}
          </button>
        </div>
      </header>

      <div className="shell-workspace">
        <aside className={`shell-sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
          <div className="shell-sidebar-heading">
            <span className="shell-section-label">WORKSPACE</span>
            <span className="shell-role-tag">
              {isOfficial ? <ShieldCheck size={13} /> : <Users size={13} />}
              {isOfficial ? "OFFICIAL" : "CITIZEN"}
            </span>
          </div>

          <div className="shell-nav-group">
            <span className="shell-nav-caption">YOUR CITY</span>
            {navItems.map(({ label, path, icon: Icon }) => (
              <NavLink
                key={path}
                to={path}
                className={({ isActive }) =>
                  `shell-nav-link ${isActive ? "active" : ""}`
                }
              >
                <Icon size={17} />
                <span>{label}</span>
                {label === "Safety & Alerts" && <i className="nav-status-dot" />}
              </NavLink>
            ))}
          </div>

          <div className="shell-sidebar-bottom">
            <div className="shell-help-card">
              <span className="shell-help-icon"><Sparkles size={17} /></span>
              <strong>Building a better Goa.</strong>
              <p>Connected services. Informed communities. Smarter decisions.</p>
            </div>

            <NavLink
              to={isOfficial ? "/official/settings" : "/citizen/settings"}
              className={({ isActive }) =>
                `shell-nav-link shell-settings-link ${isActive ? "active" : ""}`
              }
            >
              <Settings size={17} />
              <span>Settings</span>
            </NavLink>

            <button className="shell-nav-link shell-logout" onClick={() => navigate("/login")}>
              <CircleHelp size={17} />
              <span>Help & sign out</span>
            </button>
          </div>
        </aside>

        <main className="shell-main">
          <div className="shell-page-topline">
            <div className="shell-breadcrumb">
              <span>SMART LAND</span>
              <span>/</span>
              <strong>{isOfficial ? "OFFICIAL PORTAL" : "CITIZEN PORTAL"}</strong>
            </div>
            <div className="shell-page-status">
              <i /> PLATFORM ACTIVE
            </div>
          </div>

          <div className="shell-content">
            <Outlet context={{ theme, setTheme, isOfficial }} />
          </div>

          <footer className="shell-footer">
            <span>SMART LAND · MADE FOR GOA</span>
            <span>CONNECTED. TRANSPARENT. SMARTER.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
