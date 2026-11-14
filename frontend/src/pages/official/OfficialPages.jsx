import { useEffect, useState } from "react";
import {
  NavLink, Outlet, useNavigate, useOutletContext
} from "react-router-dom";
import {
  LayoutDashboard, ClipboardList, Building2, ChartNoAxesCombined,
  BellRing, Settings, LogOut, Search, Clock3,
  CheckCircle2, AlertTriangle, ArrowUpRight, MapPin,
  CalendarDays, Users, FileText,
  ShieldAlert
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import officialService from "../../services/officialService";
import "./OfficialPages.css";

const navigation = [
  { label: "Overview", path: "/official/dashboard", icon: LayoutDashboard },
  { label: "Complaints", path: "/official/complaints", icon: ClipboardList },
  { label: "Projects", path: "/official/projects", icon: Building2 },
  { label: "Departments", path: "/official/departments", icon: Building2 },
  { label: "Officials & Workers", path: "/official/officials", icon: Users },
  { label: "Analytics", path: "/official/analytics", icon: ChartNoAxesCombined },
  { label: "Traffic Alerts", path: "/official/alerts", icon: BellRing }
];

function Heading({ eyebrow, title, description }) {
  return (
    <div className="op-heading">
      <div>
        <span className="op-eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <span className="op-date">
        <CalendarDays size={14} /> {new Date().toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }).toUpperCase()}
      </span>
    </div>
  );
}

function Panel({ children, className = "" }) {
  return <section className={`op-panel ${className}`}>{children}</section>;
}

// ============================================================================
// 1. OFFICIAL LAYOUT
// ============================================================================
export function OfficialLayout() {
  const navigate = useNavigate();
  const { user, logout, isSafetyOfficer, isWorker } = useAuth();

  // Authoritative navigation items based on role & safety clearance
  let navItems = navigation;
  if (isWorker) {
    // Workers can view only the overview dashboard
    navItems = navigation.filter((item) => item.path === "/official/dashboard");
  } else if (isSafetyOfficer) {
    // Safety officers have access to the Safety Register
    navItems = [
      ...navigation,
      { label: "Safety register", path: "/official/safety", icon: ShieldAlert },
    ];
  }

  return (
    <div className="op-app citynex-shell">
      <main className="op-main citynex-main">
        <header className="cn-topbar">
          <button className="cn-brand" onClick={() => navigate("/official/dashboard")}><span>C</span>CityNex</button>
          <nav className="cn-nav">
            {navItems.map(({ label, path }) => (
              <NavLink key={path} to={path}>
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="cn-user" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <i/>
            <b>{user?.full_name ? user.full_name[0].toUpperCase() : "O"}</b>
            <span>{user?.full_name || "Official Account"}<br/><small style={{ textTransform: "uppercase", fontSize: "10px", opacity: 0.75 }}>{user?.role || "Official"}</small></span>
            <button
              onClick={() => { logout(); navigate("/login"); }}
              style={{ background: "none", border: "none", color: "#ef4444", cursor: "pointer", display: "flex", alignItems: "center", padding: "4px 8px", marginLeft: "8px" }}
              title="Sign out"
              aria-label="Sign out"
            >
              <LogOut size={16} />
            </button>
          </div>
        </header>
        <div className="op-content cn-content"><Outlet context={{ theme: "light", setTheme: () => {} }}/></div>
      </main>
    </div>
  );
}

// ============================================================================
// 2. OFFICIAL & WORKER DASHBOARD
// ============================================================================
export function OfficialDashboard() {
  const navigate = useNavigate();
  const { user, isWorker } = useAuth();

  const [summary, setSummary] = useState(null);
  const [deptStats, setDeptStats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [departmentFilter, setDepartmentFilter] = useState("All Departments");

  async function loadDashboardData() {
    try {
      setLoading(true);
      setError(null);
      const [sumRes, depRes] = await Promise.allSettled([
        officialService.getDashboardSummary(),
        isWorker ? Promise.resolve([]) : officialService.getDepartmentStats(),
      ]);

      if (sumRes.status === "fulfilled") {
        setSummary(sumRes.value);
      } else {
        throw new Error(sumRes.reason?.userMessage || "Failed to load dashboard metrics.");
      }

      if (depRes.status === "fulfilled" && Array.isArray(depRes.value)) {
        setDeptStats(depRes.value);
      }
    } catch (err) {
      console.warn("Failed to load official dashboard:", err.message);
      setError(err.userMessage || err.message || "Failed to load dashboard metrics.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboardData();
  }, [isWorker]);

  if (loading) {
    return (
      <div className="op-loading-state" style={{ padding: "60px 20px", textAlign: "center", color: "var(--op-muted)" }}>
        <p>Loading real-time city operations metrics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="o1-dashboard">
        <div style={{ padding: "20px", background: "rgba(239,68,68,0.1)", borderRadius: "10px", color: "#ef4444" }}>
          <p>{error}</p>
          <button onClick={loadDashboardData} style={{ marginTop: "10px", padding: "8px 14px", cursor: "pointer" }}>Retry</button>
        </div>
      </div>
    );
  }

  // WORKER VIEW
  if (isWorker) {
    const totalTasks = summary?.total_assigned_tasks || 0;
    const pendingTasks = summary?.pending_tasks || 0;
    const inProgressTasks = summary?.in_progress_tasks || 0;
    const completedTasks = summary?.completed_tasks || 0;
    const recentTasks = summary?.recent_tasks || [];

    return (
      <div className="o1-dashboard" style={{ gridTemplateColumns: "1fr" }}>
        <div className="o1-main">
          <header className="o1-greeting">
            <div>
              <span className="o1-eyebrow">FIELD WORKER WORKSPACE</span>
              <h1>Welcome, {user?.full_name}!</h1>
              <p>Your current field tasks and operational assignments.</p>
            </div>
            <div className="o1-greeting-actions">
              <span className="o1-live"><i/> FIELD DISPATCH ACTIVE</span>
            </div>
          </header>

          <section className="o1-stat-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
            <div className="o1-stat-card">
              <div className="o1-stat-card-top"><span className="o1-stat-icon teal"><ClipboardList size={18}/></span></div>
              <span className="o1-stat-title">Total Tasks</span>
              <div className="o1-stat-bottom"><strong>{totalTasks}</strong></div>
              <small>All assigned tasks</small>
            </div>
            <div className="o1-stat-card">
              <div className="o1-stat-card-top"><span className="o1-stat-icon orange"><Clock3 size={18}/></span></div>
              <span className="o1-stat-title">Pending</span>
              <div className="o1-stat-bottom"><strong>{pendingTasks}</strong></div>
              <small>Awaiting start</small>
            </div>
            <div className="o1-stat-card">
              <div className="o1-stat-card-top"><span className="o1-stat-icon coral"><AlertTriangle size={18}/></span></div>
              <span className="o1-stat-title">In Progress</span>
              <div className="o1-stat-bottom"><strong>{inProgressTasks}</strong></div>
              <small>Work underway</small>
            </div>
            <div className="o1-stat-card">
              <div className="o1-stat-card-top"><span className="o1-stat-icon lime"><CheckCircle2 size={18}/></span></div>
              <span className="o1-stat-title">Completed</span>
              <div className="o1-stat-bottom"><strong>{completedTasks}</strong></div>
              <small>Successfully closed</small>
            </div>
          </section>

          <section className="o1-activity-section" style={{ marginTop: "24px" }}>
            <div className="o1-section-heading">
              <div><span className="o1-eyebrow">ACTIVE WORK</span><h2>Your Assigned Tasks</h2></div>
            </div>
            <div className="o1-activity-list">
              {recentTasks.length > 0 ? (
                recentTasks.map((t) => (
                  <div className="o1-activity-item" key={t.id}>
                    <span className="o1-activity-symbol"><ClipboardList size={16}/></span>
                    <div>
                      <strong>{t.task_description}</strong>
                      <small>Task #{String(t.id).slice(0, 8)} · {new Date(t.created_at).toLocaleDateString("en-IN")}</small>
                    </div>
                    <span className={`o2-status ${t.status.toLowerCase().replaceAll(" ", "-")}`}>{t.status}</span>
                  </div>
                ))
              ) : (
                <div style={{ padding: "20px", color: "var(--op-muted)" }}>No tasks currently assigned to your account.</div>
              )}
            </div>
          </section>
        </div>
      </div>
    );
  }

  // OFFICIAL VIEW
  const total = summary?.total_complaints || 0;
  const pending = summary?.pending_complaints || 0;
  const inProgress = summary?.in_progress_complaints || 0;
  const resolved = summary?.resolved_complaints || 0;
  const highPriority = summary?.high_priority_complaints || 0;
  const resolutionRate = total > 0 ? Math.round((resolved / total) * 100) : 100;
  const recentComplaints = summary?.recent_complaints || [];

  const stats = [
    { label: "Total complaints", value: String(total), sub: "Municipal scope", icon: ClipboardList, color: "teal", filter: "All" },
    { label: "Pending", value: String(pending), sub: "Awaiting triage", icon: Clock3, color: "orange", filter: "Submitted" },
    { label: "High priority", value: String(highPriority), sub: "Critical / High", icon: AlertTriangle, color: "coral", filter: "High" },
    { label: "Resolved", value: String(resolved), sub: "Closed successfully", icon: CheckCircle2, color: "lime", filter: "Resolved" }
  ];

  return (
    <div className="o1-dashboard">
      <div className="o1-main">
        <header className="o1-greeting">
          <div>
            <span className="o1-eyebrow">CITYNEX / OFFICIAL WORKSPACE</span>
            <h1>Hello, {user?.full_name || "Administrator"}!</h1>
            <p>Live municipal operations and department activity.</p>
            {deptStats.length > 0 && (
              <select
                value={departmentFilter}
                onChange={e => setDepartmentFilter(e.target.value)}
                className="o1-dept-select"
              >
                <option>All Departments</option>
                {deptStats.map(d => <option key={d.department_id} value={d.department_name}>{d.department_name}</option>)}
              </select>
            )}
          </div>
          <div className="o1-greeting-actions">
            <span className="o1-live"><i/> LIVE BACKEND SYNC</span>
          </div>
        </header>

        <section className="o1-hero-metric">
          <div className="o1-hero-top">
            <div>
              <span className="o1-eyebrow">CITY RESOLUTION RATE</span>
              <div className="o1-hero-number">{resolutionRate}<span>%</span></div>
              <p>{resolutionRate >= 80 ? "Optimal performance" : "Requires attention"} <span>· Live database sync</span></p>
            </div>
            <div className="o1-hero-mini">
              <span>ACTIVE PROGRESS</span>
              <strong>{inProgress} active</strong>
              <small>Complaints undergoing repair</small>
            </div>
          </div>
          <div className="o1-range">
            <div className="o1-range-segment slow"><i/><i/><i/><i/></div>
            <div className="o1-range-segment average"><i/><i/><i/><i/></div>
            <div className="o1-range-segment fast"><i/><i/><i/><i/></div>
            <div className="o1-range-marker" style={{ left: `${Math.min(resolutionRate, 95)}%` }}><b/></div>
          </div>
          <div className="o1-range-labels"><span>0% · Needs attention</span><span>60% · Average</span><span>80% · Excellent</span><span>100%</span></div>
        </section>

        <section className="o1-stat-grid">
          {stats.map((stat) => {
            const Icon = stat.icon;
            return (
              <button className="o1-stat-card" key={stat.label} onClick={() => navigate(`/official/complaints?filter=${stat.filter}`)}>
                <div className="o1-stat-card-top">
                  <span className={`o1-stat-icon ${stat.color}`}><Icon size={18}/></span>
                  <span className="o1-stat-arrow"><ArrowUpRight size={16}/></span>
                </div>
                <span className="o1-stat-title">{stat.label}</span>
                <div className="o1-stat-bottom">
                  <strong>{stat.value}</strong>
                </div>
                <small>{stat.sub}</small>
              </button>
            );
          })}
        </section>

        {deptStats.length > 0 && (
          <>
            <section className="o1-section-heading">
              <div><span className="o1-eyebrow">DEPARTMENT PERFORMANCE</span><h2>Department breakdown</h2></div>
              <button onClick={() => navigate("/official/departments")}>View all <ArrowUpRight size={15}/></button>
            </section>

            <section className="o1-glass-grid">
              {deptStats
                .filter(d => departmentFilter === "All Departments" || d.department_name === departmentFilter)
                .map(d => (
                  <button className="o1-glass-card olive" key={d.department_id} onClick={() => navigate("/official/departments")}>
                    <div className="o1-glass-head">
                      <span className="o1-glass-symbol"><Building2 size={18}/></span>
                      <span className="o1-glass-open"><ArrowUpRight size={17}/></span>
                    </div>
                    <span className="o1-glass-title">{d.department_name}</span>
                    <span className="o1-glass-caption">Assigned complaints</span>
                    <strong>{d.total_complaints}</strong>
                    <div className="o1-glass-foot"><span>Resolution rate</span><b>{Math.round(d.resolution_rate)}%</b></div>
                  </button>
                ))}
            </section>
          </>
        )}

        <section className="o1-activity-section">
          <div className="o1-section-heading">
            <div><span className="o1-eyebrow">CITY UPDATES</span><h2>Recent complaints</h2></div>
            <button onClick={() => navigate("/official/complaints")}>View all <ArrowUpRight size={15}/></button>
          </div>
          <div className="o1-activity-list">
            {recentComplaints.length > 0 ? (
              recentComplaints.map((item) => (
                <div className="o1-activity-item" key={item.id} onClick={() => navigate(`/official/complaints`)} style={{ cursor: "pointer" }}>
                  <span className="o1-activity-symbol"><ClipboardList size={16}/></span>
                  <div>
                    <strong>{item.title}</strong>
                    <small>{item.category} · #{String(item.id).slice(0, 8)} · {new Date(item.created_at).toLocaleDateString("en-IN")}</small>
                  </div>
                  <span className={`o2-status ${item.status.toLowerCase().replaceAll(" ", "-")}`}>{item.status}</span>
                </div>
              ))
            ) : (
              <div style={{ padding: "20px", color: "var(--op-muted)" }}>No recent complaints logged in this period.</div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

// ============================================================================
// 3. OFFICIAL COMPLAINTS MANAGEMENT
// ============================================================================
export function OfficialComplaints() {
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [activeDepartment, setActiveDepartment] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Status update & duplicate linking states
  const [updateStatus, setUpdateStatus] = useState("Submitted");
  const [updateRemarks, setUpdateRemarks] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  async function loadComplaints() {
    try {
      setLoading(true);
      setError(null);
      const params = {};
      if (statusFilter !== "All") params.status = statusFilter;
      const data = await officialService.getComplaints(params);
      setComplaints(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn("Failed to load official complaints:", err.message);
      setError(err.userMessage || "Failed to load municipal complaints.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadComplaints();
  }, [statusFilter]);

  async function openComplaintDetail(item) {
    try {
      setLoadingDetail(true);
      setActionMessage(null);
      setSelected(item);
      setUpdateStatus(item.status);
      setUpdateRemarks("");
      const fullDetail = await officialService.getComplaintById(item.id);
      setSelected(fullDetail);
      setUpdateStatus(fullDetail.status);
    } catch (err) {
      console.warn("Failed to load complaint detail:", err.message);
    } finally {
      setLoadingDetail(false);
    }
  }

  async function handleStatusUpdate(e) {
    e.preventDefault();
    if (!selected || updateRemarks.trim().length < 3) {
      setActionMessage({ error: "Remarks must be at least 3 characters long." });
      return;
    }

    try {
      setIsUpdating(true);
      setActionMessage(null);
      const updated = await officialService.updateComplaintStatus(selected.id, {
        status: updateStatus,
        remarks: updateRemarks.trim(),
      });
      setActionMessage({ success: `Status updated to ${updateStatus}.` });
      setSelected(prev => ({ ...prev, status: updated.status, updates: [...(prev.updates || []), { id: Date.now(), status: updated.status, remarks: updateRemarks, actor_name: "Municipal Official", created_at: new Date().toISOString() }] }));
      loadComplaints();
    } catch (err) {
      setActionMessage({ error: err.userMessage || "Failed to update status." });
    } finally {
      setIsUpdating(false);
    }
  }

  async function handleLinkDuplicate(masterId) {
    if (!selected || !masterId) return;
    try {
      setIsUpdating(true);
      setActionMessage(null);
      await officialService.linkDuplicateComplaint(selected.id, masterId);
      setActionMessage({ success: `Linked as duplicate of master incident #${String(masterId).slice(0, 8)}.` });
      loadComplaints();
    } catch (err) {
      setActionMessage({ error: err.userMessage || "Failed to link duplicate." });
    } finally {
      setIsUpdating(false);
    }
  }

  const filtered = complaints.filter(item =>
    (activeDepartment === "All" || (item.department_name || item.department) === activeDepartment) &&
    `${item.id} ${item.title} ${item.category} ${item.citizen_name || ""}`.toLowerCase().includes(query.toLowerCase())
  );

  const statuses = [
    "All", "Submitted", "Under Review", "Assigned", "In Progress", "Resolved", "Rejected", "Needs More Information"
  ];

  return (
    <div className="o2-complaints">
      <div className="o2-left-profile">
        <div className="o2-profile-head">
          <div className="o2-profile-avatar">OF</div>
          <b>Municipal Desk</b>
          <small>CIVIC OPERATIONS REGISTER</small>
          <span className="o2-profile-status"><i/> AUTHENTICATED SESSION</span>
        </div>
        <div style={{ padding: "16px", color: "var(--op-muted)", fontSize: "11px", lineHeight: "1.6" }}>
          <p>Complaints registered by citizens across Goa are triaged, categorized, and assigned to municipal field departments.</p>
        </div>
      </div>

      <div className="o2-content">
        <div className="o2-list-toolbar">
          <div className="o2-list-title"><span className="o1-eyebrow">OFFICIAL RECORDS</span><h1>Complaints</h1></div>
          <div className="o2-search">
            <Search size={16}/>
            <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search title, ID, category..."/>
          </div>
          <select value={statusFilter} onChange={e=>setStatusFilter(e.target.value)} className="o2-filter">
            {statuses.map(s=><option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        {error && (
          <div style={{ padding: "14px", background: "rgba(239,68,68,0.1)", borderRadius: "8px", color: "#ef4444", marginBottom: "16px" }}>
            {error}
          </div>
        )}

        <div className="o2-table-head">
          <span className="o2-check-cell">#</span>
          <span>COMPLAINT DETAILS</span>
          <span>DEPARTMENT</span>
          <span>DATE</span>
        </div>

        <div className="o2-file-list">
          {loading ? (
            <div className="o2-empty">Loading complaints from database...</div>
          ) : filtered.length > 0 ? (
            filtered.map((item, idx) => (
              <div className={`o2-file-row ${selected?.id === item.id ? "active" : ""}`} key={item.id}>
                <span className="o2-check-cell">{idx + 1}</span>
                <button className="o2-file-main" onClick={() => openComplaintDetail(item)}>
                  <span className="o2-file-icon document">DOC</span>
                  <span className="o2-file-copy">
                    <b>{item.title}</b>
                    <small>#{String(item.id).slice(0, 8)} · {item.category} · Priority: {item.priority}</small>
                    <em>{item.issue_type} · Reports: {item.report_count || 1}</em>
                  </span>
                </button>
                <span className="o2-file-department">
                  {item.department_name || "General Desk"}
                  <small className={`o2-status ${item.status.toLowerCase().replaceAll(" ", "-")}`}>{item.status}</small>
                </span>
                <span className="o2-file-date">{new Date(item.created_at).toLocaleDateString("en-IN")}</span>
              </div>
            ))
          ) : (
            <div className="o2-empty">No complaints match your criteria.</div>
          )}
        </div>
        <div className="o2-list-footer">
          <span>{filtered.length} RECORDS DISPLAYED</span>
        </div>
      </div>

      {/* DETAIL & ACTION DRAWER */}
      {selected && (
        <div className="o2-detail-backdrop" onClick={() => setSelected(null)}>
          <aside className="o2-detail-drawer" onClick={e => e.stopPropagation()}>
            <div className="o2-drawer-head">
              <span>COMPLAINT DOSSIER</span>
              <button onClick={() => setSelected(null)}>✕</button>
            </div>
            <small className="o2-drawer-id">ID: {selected.id}</small>
            <h2>{selected.title}</h2>
            <p>{selected.description}</p>

            <div className="o2-drawer-meta">
              <span>{selected.department_name || "General Desk"}</span>
              <span>{selected.category}</span>
              <span>{selected.priority} priority</span>
            </div>

            <div className="o2-drawer-field">
              <small>LOCATION COORDINATES</small>
              <b><MapPin size={14}/> {selected.latitude?.toFixed(4)}, {selected.longitude?.toFixed(4)}</b>
            </div>

            <div className="o2-drawer-field">
              <small>REPORT COUNT</small>
              <b>{selected.report_count || 1} citizen reports</b>
            </div>

            {selected.image_signed_url && (
              <div className="o2-drawer-field">
                <small>ATTACHED PHOTOGRAPH</small>
                <img src={selected.image_signed_url} alt="Evidence" style={{ width: "100%", maxHeight: "180px", objectFit: "cover", borderRadius: "8px", marginTop: "6px" }}/>
              </div>
            )}

            {/* ADVISORY DUPLICATE SUGGESTIONS */}
            {selected.duplicates && selected.duplicates.length > 0 && (
              <div className="o2-drawer-field" style={{ background: "rgba(255,181,71,0.08)", padding: "10px", borderRadius: "8px" }}>
                <small style={{ color: "#d97706" }}>PROXIMITY DUPLICATE SUGGESTIONS</small>
                {selected.duplicates.map(d => (
                  <div key={d.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "8px", fontSize: "11px" }}>
                    <span>#{String(d.id).slice(0, 8)} · {d.title}</span>
                    <button
                      onClick={() => handleLinkDuplicate(d.id)}
                      disabled={isUpdating}
                      style={{ padding: "4px 8px", background: "#d97706", color: "white", border: 0, borderRadius: "6px", fontSize: "10px", cursor: "pointer" }}
                    >
                      Link Master
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* STATUS UPDATE FORM */}
            <form onSubmit={handleStatusUpdate} style={{ marginTop: "16px" }}>
              <div className="o2-drawer-field">
                <small>UPDATE STATUS</small>
                <select value={updateStatus} onChange={e => setUpdateStatus(e.target.value)} disabled={isUpdating}>
                  {statuses.filter(s => s !== "All").map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>

              <div className="o2-drawer-field">
                <small>OFFICIAL REMARKS (REQUIRED)</small>
                <input
                  value={updateRemarks}
                  onChange={e => setUpdateRemarks(e.target.value)}
                  placeholder="Explain action taken or dispatch details..."
                  required
                  minLength={3}
                  disabled={isUpdating}
                  style={{ width: "100%", padding: "9px", border: "1px solid #DDE2D7", borderRadius: "8px" }}
                />
              </div>

              {actionMessage?.error && <p style={{ color: "#ef4444", fontSize: "11px" }}>{actionMessage.error}</p>}
              {actionMessage?.success && <p style={{ color: "#10b981", fontSize: "11px" }}>{actionMessage.success}</p>}

              <button className="o2-drawer-action" type="submit" disabled={isUpdating} style={{ marginTop: "12px" }}>
                {isUpdating ? "Saving..." : "Update Complaint Status"}
              </button>
            </form>

            {/* TIMELINE */}
            <div className="o2-drawer-timeline">
              <b>STATUS HISTORY TIMELINE</b>
              {selected.updates && selected.updates.length > 0 ? (
                selected.updates.map(u => (
                  <div key={u.id} style={{ fontSize: "11px", marginBottom: "8px", paddingLeft: "8px", borderLeft: "2px solid #00BCB4" }}>
                    <strong>{u.status}</strong> · {u.actor_name || "Official"}
                    <p style={{ margin: "2px 0 0", color: "#68766F" }}>{u.remarks}</p>
                    <small style={{ color: "#9aa8b2" }}>{new Date(u.created_at).toLocaleString("en-IN")}</small>
                  </div>
                ))
              ) : (
                <p style={{ fontSize: "11px", color: "var(--op-muted)" }}>Initial report submitted.</p>
              )}
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// 4. OFFICIAL DEPARTMENTS
// ============================================================================
export function OfficialDepartments() {
  const navigate = useNavigate();
  const [deptStats, setDeptStats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadDepts() {
      try {
        setLoading(true);
        const data = await officialService.getDepartmentStats();
        setDeptStats(Array.isArray(data) ? data : []);
      } catch (err) {
        setError(err.userMessage || "Failed to load department statistics.");
      } finally {
        setLoading(false);
      }
    }
    loadDepts();
  }, []);

  return (
    <div className="o3-departments">
      <div className="o3-heading">
        <span className="o1-eyebrow">GOVERNMENT INFRASTRUCTURE</span>
        <h1>Municipal Departments</h1>
        <p>Operational workload, resolution performance, and active complaints by municipal division.</p>
      </div>

      {loading ? (
        <div style={{ padding: "40px", color: "var(--op-muted)", textAlign: "center" }}>Loading departments...</div>
      ) : error ? (
        <div style={{ padding: "20px", color: "#ef4444" }}>{error}</div>
      ) : (
        <div className="o3-department-grid">
          {deptStats.map(d => (
            <div className="o3-department-card" key={d.department_id}>
              <div className="o3-card-shade"/>
              <div className="o3-card-content">
                <div className="o3-card-top">
                  <span>MUNICIPAL DIVISION</span>
                  <b>{Math.round(d.resolution_rate)}% RESOLVED</b>
                </div>
                <div>
                  <h2>{d.department_name}</h2>
                  <p>Active workload: {d.pending_complaints} pending · {d.in_progress_complaints} in progress</p>
                  <div className="o3-card-tags">
                    <span>Total: {d.total_complaints}</span>
                    <span>Resolved: {d.resolved_complaints}</span>
                  </div>
                </div>
                <button onClick={() => navigate(`/official/complaints`)}>
                  View Complaints <ArrowUpRight size={14}/>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// 5. OFFICIALS & WORKERS DIRECTORY (ASSIGNMENT MANAGEMENT)
// ============================================================================
export function OfficialDirectory() {
  const [workers, setWorkers] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedWorker, setSelectedWorker] = useState(null);
  const [search, setSearch] = useState("");

  // Assignment creation modal state
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [assignComplaintId, setAssignComplaintId] = useState("");
  const [assignTaskDesc, setAssignTaskDesc] = useState("");
  const [assignStatus, setAssignStatus] = useState(null);

  async function loadDirectoryData() {
    try {
      setLoading(true);
      setError(null);
      const [wRes, aRes] = await Promise.allSettled([
        officialService.getWorkers(),
        officialService.getAssignments(),
      ]);

      if (wRes.status === "fulfilled" && Array.isArray(wRes.value)) {
        setWorkers(wRes.value);
        if (wRes.value.length > 0 && !selectedWorker) {
          setSelectedWorker(wRes.value[0]);
        }
      }
      if (aRes.status === "fulfilled" && Array.isArray(aRes.value)) {
        setAssignments(aRes.value);
      }
    } catch (err) {
      console.warn("Failed to load worker directory:", err.message);
      setError(err.userMessage || "Failed to load directory.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDirectoryData();
  }, []);

  async function handleCreateAssignment(e) {
    e.preventDefault();
    if (!selectedWorker || assignTaskDesc.trim().length < 3) {
      setAssignStatus({ error: "Task description must be at least 3 characters long." });
      return;
    }

    try {
      setAssignStatus({ loading: true });
      const payload = {
        worker_id: selectedWorker.id,
        task_description: assignTaskDesc.trim(),
        complaint_id: assignComplaintId.trim() || undefined,
      };
      await officialService.createAssignment(payload);
      setAssignStatus({ success: "Task assigned successfully to field worker!" });
      setAssignTaskDesc("");
      setAssignComplaintId("");
      loadDirectoryData();
      setTimeout(() => setShowAssignModal(false), 1500);
    } catch (err) {
      setAssignStatus({ error: err.userMessage || "Failed to create assignment." });
    }
  }

  const visible = workers.filter(w =>
    `${w.name} ${w.department_name || ""} ${w.availability}`.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="cn-directory">
      <div className="cn-directory-heading">
        <div>
          <span className="cn-dir-eyebrow">CITYNEX / FIELD DISPATCH</span>
          <h1>Field Workers &amp; Operations<span>.</span></h1>
          <p>Deploy field workers, create task assignments, and monitor real-time worker availability.</p>
        </div>
        <div className="cn-dir-live"><i/> DISPATCH DIRECTORY ACTIVE</div>
      </div>

      <div className="cn-dir-summary">
        <div><span>FIELD WORKERS</span><strong>{workers.length}</strong><small>Registered in roster</small></div>
        <div><span>AVAILABLE NOW</span><strong>{workers.filter(w => w.availability === "Available").length}</strong><small>Ready for dispatch</small></div>
        <div><span>BUSY IN FIELD</span><strong>{workers.filter(w => w.availability === "Busy").length}</strong><small>Active assignments</small></div>
        <div><span>TOTAL ASSIGNMENTS</span><strong>{assignments.length}</strong><small>Tracked task orders</small></div>
      </div>

      <div className="cn-dir-layout">
        <section className="cn-dir-main">
          <div className="cn-dir-toolbar">
            <div className="cn-dir-search">
              <Search size={17}/>
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search worker, department, status..."/>
            </div>
          </div>

          <div className="cn-official-list">
            {loading ? (
              <div className="cn-dir-empty">Loading field workers roster...</div>
            ) : visible.length > 0 ? (
              visible.map((worker, idx) => (
                <button
                  key={worker.id}
                  className={`cn-official-row ${selectedWorker?.id === worker.id ? "chosen" : ""}`}
                  onClick={() => setSelectedWorker(worker)}
                >
                  <span className={`cn-official-avatar avatar-${idx % 5}`}>{worker.name[0]}</span>
                  <span className="cn-official-info">
                    <strong>{worker.name}</strong>
                    <small>{worker.department_name || "Municipal Operations"}</small>
                    <em>Active tasks: {worker.active_task_count || 0}</em>
                  </span>
                  <span className={`cn-official-presence ${worker.availability.toLowerCase()}`}>
                    <i/> {worker.availability}
                  </span>
                  <ArrowUpRight size={17}/>
                </button>
              ))
            ) : (
              <div className="cn-dir-empty">No workers found.</div>
            )}
          </div>
        </section>

        {selectedWorker && (
          <aside className="cn-official-detail">
            <div className="cn-detail-top">
              <span>WORKER DOSSIER</span>
              <span className="cn-detail-active">LIVE STATUS</span>
            </div>
            <div className="cn-detail-avatar">{selectedWorker.name[0]}</div>
            <h2>{selectedWorker.name}</h2>
            <p>{selectedWorker.department_name || "Municipal Operations"}</p>
            <div className="cn-detail-dept">ID: {String(selectedWorker.id).slice(0, 8)}</div>

            <div className="cn-detail-separator"/>
            <div className="cn-detail-field">
              <small>CURRENT AVAILABILITY</small>
              <strong><i className={`cn-detail-status ${selectedWorker.availability.toLowerCase()}`}/> {selectedWorker.availability}</strong>
            </div>
            <div className="cn-detail-field">
              <small>ACTIVE TASK COUNT</small>
              <strong>{selectedWorker.active_task_count || 0} tasks</strong>
            </div>

            <button
              onClick={() => { setShowAssignModal(true); setAssignStatus(null); }}
              style={{ width: "100%", marginTop: "16px", padding: "12px", background: "#00BCB4", color: "#10201D", border: 0, borderRadius: "10px", fontWeight: "800", cursor: "pointer" }}
            >
              + Dispatch Task Assignment
            </button>
          </aside>
        )}
      </div>

      {/* CREATE ASSIGNMENT MODAL */}
      {showAssignModal && selectedWorker && (
        <div className="o2-detail-backdrop" onClick={() => setShowAssignModal(false)}>
          <aside className="o2-detail-drawer" onClick={e => e.stopPropagation()} style={{ width: "420px" }}>
            <div className="o2-drawer-head">
              <span>DISPATCH ASSIGNMENT</span>
              <button onClick={() => setShowAssignModal(false)}>✕</button>
            </div>
            <h2 style={{ marginTop: "16px" }}>Assign to {selectedWorker.name}</h2>
            <p>Deploy field task for complaint repair or traffic hazard mitigation.</p>

            <form onSubmit={handleCreateAssignment}>
              <div className="o2-drawer-field">
                <small>TASK INSTRUCTIONS (REQUIRED)</small>
                <textarea
                  rows="3"
                  value={assignTaskDesc}
                  onChange={e => setAssignTaskDesc(e.target.value)}
                  placeholder="e.g. Inspect road pothole and lay cold-mix patch..."
                  required
                  minLength={3}
                  style={{ width: "100%", padding: "8px", border: "1px solid #DDE2D7", borderRadius: "8px" }}
                />
              </div>

              <div className="o2-drawer-field">
                <small>COMPLAINT UUID (OPTIONAL)</small>
                <input
                  value={assignComplaintId}
                  onChange={e => setAssignComplaintId(e.target.value)}
                  placeholder="Paste complaint UUID if linking to specific report"
                  style={{ width: "100%", padding: "8px", border: "1px solid #DDE2D7", borderRadius: "8px" }}
                />
              </div>

              {assignStatus?.error && <p style={{ color: "#ef4444", fontSize: "11px" }}>{assignStatus.error}</p>}
              {assignStatus?.success && <p style={{ color: "#10b981", fontSize: "11px" }}>{assignStatus.success}</p>}

              <button className="o2-drawer-action" type="submit" disabled={assignStatus?.loading} style={{ marginTop: "16px" }}>
                {assignStatus?.loading ? "Assigning..." : "Confirm & Dispatch"}
              </button>
            </form>
          </aside>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// 6. OFFICIAL PROJECTS & CITIZEN FEEDBACK
// ============================================================================
export function OfficialProjectsFeedback() {
  const [activeTab, setActiveTab] = useState("Projects");
  const [projects, setProjects] = useState([]);
  const [feedback, setFeedback] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // New project modal
  const [showAdd, setShowAdd] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newDeptId, setNewDeptId] = useState("11111111-1111-1111-1111-111111111111");
  const [newStartDate, setNewStartDate] = useState("2026-01-01");
  const [newEndDate, setNewEndDate] = useState("2026-12-31");
  const [newLat, setNewLat] = useState("15.498");
  const [newLon, setNewLon] = useState("73.827");
  const [formStatus, setFormStatus] = useState(null);

  async function loadData() {
    try {
      setLoading(true);
      setError(null);
      const [pRes, fRes] = await Promise.allSettled([
        officialService.getProjects(),
        officialService.getFeedback(),
      ]);

      if (pRes.status === "fulfilled" && Array.isArray(pRes.value)) {
        setProjects(pRes.value);
      }
      if (fRes.status === "fulfilled" && Array.isArray(fRes.value)) {
        setFeedback(fRes.value);
      }
    } catch (err) {
      console.warn("Failed to load projects/feedback:", err.message);
      setError(err.userMessage || "Failed to load data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleAddProject(e) {
    e.preventDefault();
    try {
      setFormStatus({ loading: true });
      await officialService.createProject({
        title: newTitle.trim(),
        description: newDesc.trim(),
        department_id: newDeptId,
        latitude: parseFloat(newLat),
        longitude: parseFloat(newLon),
        start_date: newStartDate,
        expected_end_date: newEndDate,
        is_published: true,
      });
      setFormStatus({ success: "Project created and published!" });
      loadData();
      setTimeout(() => setShowAdd(false), 1200);
    } catch (err) {
      setFormStatus({ error: err.userMessage || "Failed to create project." });
    }
  }

  async function handleConvertToComplaint(feedbackItem) {
    try {
      await officialService.convertFeedbackToComplaint(feedbackItem.id, {
        priority: "Medium",
        severity: 6,
      });
      alert(`Feedback converted to tracked complaint!`);
      loadData();
    } catch (err) {
      alert(`Failed to convert feedback: ${err.userMessage || err.message}`);
    }
  }

  return (
    <div className="of-projects-page">
      <header className="of-projects-heading">
        <div>
          <span className="of-eyebrow">CITYNEX / DEVELOPMENT &amp; CITIZEN FEEDBACK</span>
          <h1>Municipal Infrastructure Initiatives</h1>
          <p>Oversee city development projects and analyze citizen community feedback.</p>
        </div>
      </header>

      <div className="of-project-tabs">
        <button className={activeTab === "Projects" ? "active" : ""} onClick={() => setActiveTab("Projects")}>
          Projects ({projects.length})
        </button>
        <button className={activeTab === "Feedback" ? "active" : ""} onClick={() => setActiveTab("Feedback")}>
          Citizen Feedback ({feedback.length})
        </button>
        <div className="of-tabs-spacer"/>
        {activeTab === "Projects" && (
          <button className="of-add-project" onClick={() => { setShowAdd(true); setFormStatus(null); }}>
            + Create Municipal Project
          </button>
        )}
      </div>

      {loading ? (
        <div style={{ padding: "40px", color: "var(--op-muted)", textAlign: "center" }}>Loading records from backend...</div>
      ) : activeTab === "Projects" ? (
        <div className="of-project-cards">
          {projects.map((p, idx) => (
            <article className={`of-project-card of-project-card-${idx % 3}`} key={p.id}>
              <div className="of-project-overlay"/>
              <div className="of-project-card-top">
                <span>{p.department_name || "Public Works"}</span>
                <span className={`o2-status ${p.status.toLowerCase()}`}>{p.status}</span>
              </div>
              <div className="of-project-card-bottom">
                <h2>{p.title}</h2>
                <p style={{ color: "#E4EAE3", fontSize: "11px", margin: "6px 0 10px" }}>{p.description}</p>
                <div style={{ fontSize: "10px", color: "rgba(255,255,255,0.7)" }}>
                  Timeline: {p.start_date} to {p.expected_end_date} · {p.is_published ? "Published" : "Draft"}
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="o2-content" style={{ marginTop: "16px" }}>
          <div className="o2-file-list">
            {feedback.length > 0 ? (
              feedback.map(f => (
                <div className="o2-file-row" key={f.id} style={{ gridTemplateColumns: "1fr 140px 140px" }}>
                  <div>
                    <b>{f.project_title || "Municipal Project"}</b>
                    <p style={{ margin: "4px 0", fontSize: "11px", color: "#263B36" }}>{f.message}</p>
                    <small style={{ color: "#89958D" }}>Category: {f.category} · Citizen: {f.citizen_name || "Anonymous"}</small>
                  </div>
                  <span style={{ fontSize: "11px", color: "#89958D" }}>{new Date(f.created_at).toLocaleDateString("en-IN")}</span>
                  <div>
                    {f.complaint_id ? (
                      <span className="o2-status resolved">Converted #{String(f.complaint_id).slice(0, 8)}</span>
                    ) : (
                      <button
                        onClick={() => handleConvertToComplaint(f)}
                        style={{ padding: "6px 10px", background: "#172B2A", color: "white", border: 0, borderRadius: "6px", fontSize: "10px", cursor: "pointer" }}
                      >
                        Convert to Complaint
                      </button>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="o2-empty">No citizen feedback registered yet.</div>
            )}
          </div>
        </div>
      )}

      {/* CREATE PROJECT MODAL */}
      {showAdd && (
        <div className="o2-detail-backdrop" onClick={() => setShowAdd(false)}>
          <aside className="o2-detail-drawer" onClick={e => e.stopPropagation()} style={{ width: "460px" }}>
            <div className="o2-drawer-head">
              <span>NEW MUNICIPAL PROJECT</span>
              <button onClick={() => setShowAdd(false)}>✕</button>
            </div>
            <h2 style={{ marginTop: "16px" }}>Create Project</h2>
            <form onSubmit={handleAddProject}>
              <div className="o2-drawer-field">
                <small>PROJECT TITLE</small>
                <input value={newTitle} onChange={e => setNewTitle(e.target.value)} required minLength={3} placeholder="e.g. Mandovi Bridge Deck Resurfacing" style={{ width: "100%", padding: "8px", border: "1px solid #DDE2D7", borderRadius: "8px" }}/>
              </div>
              <div className="o2-drawer-field">
                <small>DESCRIPTION</small>
                <textarea rows="3" value={newDesc} onChange={e => setNewDesc(e.target.value)} required minLength={5} placeholder="Project scope, objectives and citizen benefits..." style={{ width: "100%", padding: "8px", border: "1px solid #DDE2D7", borderRadius: "8px" }}/>
              </div>
              <div className="o2-drawer-field">
                <small>START DATE &amp; END DATE</small>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                  <input type="date" value={newStartDate} onChange={e => setNewStartDate(e.target.value)} required style={{ padding: "8px", border: "1px solid #DDE2D7", borderRadius: "8px" }}/>
                  <input type="date" value={newEndDate} onChange={e => setNewEndDate(e.target.value)} required style={{ padding: "8px", border: "1px solid #DDE2D7", borderRadius: "8px" }}/>
                </div>
              </div>
              {formStatus?.error && <p style={{ color: "#ef4444", fontSize: "11px" }}>{formStatus.error}</p>}
              {formStatus?.success && <p style={{ color: "#10b981", fontSize: "11px" }}>{formStatus.success}</p>}
              <button className="o2-drawer-action" type="submit" disabled={formStatus?.loading} style={{ marginTop: "16px" }}>
                {formStatus?.loading ? "Saving..." : "Create & Publish"}
              </button>
            </form>
          </aside>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// 7. OFFICIAL ANALYTICS
// ============================================================================
export function OfficialAnalytics() {
  const [priorities, setPriorities] = useState(null);
  const [deptStats, setDeptStats] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAnalytics() {
      try {
        setLoading(true);
        const [pRes, dRes] = await Promise.allSettled([
          officialService.getPriorityBreakdown(),
          officialService.getDepartmentStats(),
        ]);
        if (pRes.status === "fulfilled") setPriorities(pRes.value);
        if (dRes.status === "fulfilled" && Array.isArray(dRes.value)) setDeptStats(dRes.value);
      } finally {
        setLoading(false);
      }
    }
    loadAnalytics();
  }, []);

  return (
    <>
      <Heading
        eyebrow="ANALYTICS &amp; PERFORMANCE"
        title="Municipal Operations Analytics"
        description="Priority distribution and department resolution rates from live operations."
      />
      {loading ? (
        <div style={{ padding: "40px", color: "var(--op-muted)" }}>Loading analytics...</div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
          <Panel>
            <span className="op-eyebrow">PRIORITY DISTRIBUTION</span>
            <h2>Complaints by Priority</h2>
            <div style={{ marginTop: "16px", display: "flex", flexDirection: "column", gap: "10px" }}>
              <div><span>Critical: </span><strong>{priorities?.critical || 0}</strong></div>
              <div><span>High: </span><strong>{priorities?.high || 0}</strong></div>
              <div><span>Medium: </span><strong>{priorities?.medium || 0}</strong></div>
              <div><span>Low: </span><strong>{priorities?.low || 0}</strong></div>
              <div style={{ marginTop: "10px", fontWeight: "bold" }}>Total Complaints: {priorities?.total || 0}</div>
            </div>
          </Panel>

          <Panel>
            <span className="op-eyebrow">RESOLUTION RATES</span>
            <h2>Department Efficiency</h2>
            <div style={{ marginTop: "16px", display: "flex", flexDirection: "column", gap: "12px" }}>
              {deptStats.map(d => (
                <div key={d.department_id}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
                    <span>{d.department_name}</span>
                    <strong>{Math.round(d.resolution_rate)}%</strong>
                  </div>
                  <div style={{ width: "100%", height: "8px", background: "rgba(255,255,255,0.1)", borderRadius: "4px", overflow: "hidden" }}>
                    <div style={{ width: `${Math.min(d.resolution_rate, 100)}%`, height: "100%", background: "#00BCB4" }}/>
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      )}
    </>
  );
}

// ============================================================================
// 8. OFFICIAL ALERTS (TRAFFIC CONGESTION DEMO FEED)
// ============================================================================
export function OfficialAlerts() {
  const [hotspots, setHotspots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [level, setLevel] = useState("High");
  const [desc, setDesc] = useState("");
  const [lat, setLat] = useState("15.492");
  const [lon, setLon] = useState("73.815");

  async function loadHotspots() {
    try {
      setLoading(true);
      const data = await officialService.getMapHotspots();
      setHotspots(Array.isArray(data) ? data : []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadHotspots();
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    try {
      await officialService.createMapHotspot({
        latitude: parseFloat(lat),
        longitude: parseFloat(lon),
        congestion_level: level,
        description: desc.trim(),
      });
      setDesc("");
      setShowAdd(false);
      loadHotspots();
    } catch (err) {
      alert(`Failed to register hotspot: ${err.userMessage || err.message}`);
    }
  }

  return (
    <>
      <Heading
        eyebrow="CITIZEN TRANSIT &amp; TRAFFIC"
        title="Traffic Hotspot Feeds"
        description="Observed and demo traffic congestion hotspots published on the city map."
      />
      <div style={{ marginBottom: "16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: "11px", color: "#f59e0b", fontWeight: "bold" }}>● Simulated Demo Feed for MVP</span>
        <button onClick={() => setShowAdd(!showAdd)} style={{ padding: "8px 14px", background: "#00BCB4", color: "#10201D", border: 0, borderRadius: "8px", fontWeight: "800", cursor: "pointer" }}>
          + Register Traffic Hotspot
        </button>
      </div>

      {showAdd && (
        <Panel style={{ marginBottom: "20px" }}>
          <h3>Register Demo Congestion Hotspot</h3>
          <form onSubmit={handleCreate} style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "12px" }}>
            <label>
              Congestion Level:
              <select value={level} onChange={e => setLevel(e.target.value)} style={{ padding: "8px", marginLeft: "10px" }}>
                <option value="High">High</option>
                <option value="Medium">Medium</option>
                <option value="Low">Low</option>
              </select>
            </label>
            <input value={desc} onChange={e => setDesc(e.target.value)} placeholder="Description of congestion..." required minLength={5} style={{ padding: "8px" }}/>
            <button type="submit" style={{ padding: "8px", background: "#172B2A", color: "white", cursor: "pointer" }}>Save Hotspot</button>
          </form>
        </Panel>
      )}

      {loading ? (
        <div style={{ padding: "30px", color: "var(--op-muted)" }}>Loading hotspots...</div>
      ) : (
        <div className="o2-file-list">
          {hotspots.map(h => (
            <div className="o2-file-row" key={h.id} style={{ gridTemplateColumns: "100px 1fr 140px" }}>
              <span className={`o2-status ${h.congestion_level.toLowerCase()}`}>{h.congestion_level}</span>
              <div>
                <strong>{h.description}</strong>
                <small style={{ display: "block", color: "#89958D" }}>Coordinates: {h.latitude}, {h.longitude} · Source: {h.source}</small>
              </div>
              <span style={{ fontSize: "11px", color: "#89958D" }}>{new Date(h.observed_at).toLocaleString("en-IN")}</span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

// ============================================================================
// 9. OFFICIAL SAFETY REGISTER (SAFETY OFFICERS ONLY)
// ============================================================================
export function OfficialSafetyRegister() {
  const { user, isSafetyOfficer } = useAuth();
  const [reports, setReports] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedReport, setSelectedReport] = useState(null);
  const [investigationNotes, setInvestigationNotes] = useState("");
  const [investigationStatus, setInvestigationStatus] = useState("Under Review");
  const [isUpdating, setIsUpdating] = useState(false);

  async function loadSafetyData() {
    try {
      setLoading(true);
      setError(null);
      const [rRes, dRes] = await Promise.allSettled([
        officialService.getSafetyReports(),
        officialService.getSafetyDashboard(),
      ]);

      if (rRes.status === "fulfilled" && Array.isArray(rRes.value)) {
        setReports(rRes.value);
      } else {
        throw new Error(rRes.reason?.userMessage || "Access denied or failed to load safety register.");
      }

      if (dRes.status === "fulfilled") {
        setDashboard(dRes.value);
      }
    } catch (err) {
      console.warn("Safety register error:", err.message);
      setError(err.userMessage || err.message || "Failed to load safety reports.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (isSafetyOfficer) {
      loadSafetyData();
    }
  }, [isSafetyOfficer]);

  async function handleUpdateInvestigation(e) {
    e.preventDefault();
    if (!selectedReport) return;
    try {
      setIsUpdating(true);
      await officialService.updateSafetyReport(selectedReport.id, {
        status: investigationStatus,
        investigation_notes: investigationNotes.trim() || undefined,
      });
      alert("Safety report investigation updated.");
      setSelectedReport(null);
      loadSafetyData();
    } catch (err) {
      alert(`Update failed: ${err.userMessage || err.message}`);
    } finally {
      setIsUpdating(false);
    }
  }

  if (!isSafetyOfficer) {
    return (
      <div style={{ padding: "40px", textAlign: "center" }}>
        <h2>Access Restricted</h2>
        <p>This register is strictly reserved for designated municipal safety officers.</p>
      </div>
    );
  }

  return (
    <>
      <Heading
        eyebrow="RESTRICTED SAFETY OPERATIONS"
        title="Infrastructure Safety Register"
        description="Confidential safety reports and infrastructure hazard triage for designated safety officers."
      />

      {dashboard && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", marginBottom: "20px" }}>
          <Panel><span>TOTAL REPORTS</span><h3>{dashboard.total_safety_reports}</h3></Panel>
          <Panel><span>PENDING INSPECTIONS</span><h3>{dashboard.pending_investigations}</h3></Panel>
          <Panel><span>ACTIVE IN FIELD</span><h3>{dashboard.in_progress_investigations}</h3></Panel>
          <Panel><span>HIGH SEVERITY</span><h3 style={{ color: "#ef4444" }}>{dashboard.high_severity_count}</h3></Panel>
        </div>
      )}

      {loading ? (
        <div style={{ padding: "40px", color: "var(--op-muted)" }}>Loading confidential safety reports...</div>
      ) : error ? (
        <div style={{ padding: "20px", color: "#ef4444" }}>{error}</div>
      ) : (
        <div className="o2-file-list">
          {reports.map(r => (
            <div className="o2-file-row" key={r.id} style={{ gridTemplateColumns: "1fr 140px 100px" }} onClick={() => { setSelectedReport(r); setInvestigationStatus(r.status); setInvestigationNotes(r.investigation_notes || ""); }}>
              <div>
                <b>{r.title || r.safety_category}</b>
                <p style={{ margin: "2px 0", fontSize: "11px", color: "#263B36" }}>{r.description}</p>
                <small style={{ color: "#89958D" }}>Category: {r.safety_category} · Severity: {r.severity}/10 · #{String(r.id).slice(0, 8)}</small>
              </div>
              <span className={`o2-status ${r.status.toLowerCase().replaceAll(" ", "-")}`}>{r.status}</span>
              <span style={{ fontSize: "11px", color: "#89958D" }}>{new Date(r.created_at).toLocaleDateString("en-IN")}</span>
            </div>
          ))}
          {reports.length === 0 && <div className="o2-empty">No active safety reports in this register.</div>}
        </div>
      )}

      {/* DETAIL MODAL */}
      {selectedReport && (
        <div className="o2-detail-backdrop" onClick={() => setSelectedReport(null)}>
          <aside className="o2-detail-drawer" onClick={e => e.stopPropagation()}>
            <div className="o2-drawer-head">
              <span>SAFETY REPORT #{String(selectedReport.id).slice(0, 8)}</span>
              <button onClick={() => setSelectedReport(null)}>✕</button>
            </div>
            <h2 style={{ marginTop: "16px" }}>{selectedReport.title || selectedReport.safety_category}</h2>
            <p>{selectedReport.description}</p>

            <div className="o2-drawer-meta">
              <span>Category: {selectedReport.safety_category}</span>
              <span>Severity: {selectedReport.severity}/10</span>
              <span>Priority: {selectedReport.priority}</span>
            </div>

            <form onSubmit={handleUpdateInvestigation} style={{ marginTop: "16px" }}>
              <div className="o2-drawer-field">
                <small>INVESTIGATION STATUS</small>
                <select value={investigationStatus} onChange={e => setInvestigationStatus(e.target.value)} disabled={isUpdating}>
                  <option value="Under Review">Under Review</option>
                  <option value="In Progress">In Progress</option>
                  <option value="Resolved">Resolved</option>
                  <option value="Rejected">Rejected</option>
                </select>
              </div>

              <div className="o2-drawer-field">
                <small>OFFICER INVESTIGATION NOTES</small>
                <textarea
                  rows="4"
                  value={investigationNotes}
                  onChange={e => setInvestigationNotes(e.target.value)}
                  placeholder="Record on-site findings, lighting crew actions, CCTV review..."
                  disabled={isUpdating}
                  style={{ width: "100%", padding: "8px", border: "1px solid #DDE2D7", borderRadius: "8px" }}
                />
              </div>

              <button className="o2-drawer-action" type="submit" disabled={isUpdating} style={{ marginTop: "16px" }}>
                {isUpdating ? "Saving..." : "Update Investigation Record"}
              </button>
            </form>
          </aside>
        </div>
      )}
    </>
  );
}

// ============================================================================
// 10. OFFICIAL SETTINGS
// ============================================================================
export function OfficialSettings() {
  const { user, isSafetyOfficer, isWorker } = useAuth();

  return (
    <>
      <Heading
        eyebrow="ACCOUNT PREFERENCES"
        title="Settings &amp; Profile"
        description="Manage your municipal workspace account and authentication credentials."
      />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
        <Panel>
          <span className="op-eyebrow">OPERATOR PROFILE</span>
          <h2>{user?.full_name || "Official Account"}</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "16px", fontSize: "12px" }}>
            <div><span>Email: </span><strong>{user?.email || "official@goa.gov.in"}</strong></div>
            <div><span>Role: </span><strong style={{ textTransform: "uppercase" }}>{user?.role || "official"}</strong></div>
            <div><span>Account ID: </span><code>{user?.id}</code></div>
            <div><span>Department Scope: </span><strong>{user?.department_id || "All Municipal Departments"}</strong></div>
            <div><span>Safety Clearance: </span><strong style={{ color: isSafetyOfficer ? "#10b981" : "inherit" }}>{isSafetyOfficer ? "Designated Safety Officer" : "Standard Official"}</strong></div>
            <div><span>Worker Dispatch: </span><strong>{isWorker ? "Field Worker" : "Operations Desk"}</strong></div>
          </div>
        </Panel>
      </div>
    </>
  );
}
