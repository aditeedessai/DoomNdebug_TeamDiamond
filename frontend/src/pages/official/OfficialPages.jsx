
import { useState } from "react";
import {
  NavLink, Outlet, useNavigate, useOutletContext
} from "react-router-dom";
import {
  LayoutDashboard, ClipboardList, Building2, ChartNoAxesCombined,
  BellRing, Settings, LogOut, Menu, X, Search, Clock3,
  CheckCircle2, AlertTriangle, ArrowUpRight, MapPin,
  CalendarDays, Users, TrendingUp, Sun, Moon, FileText, ChevronRight
} from "lucide-react";
import "./OfficialPages.css";

const initialComplaints = [
  { id: "SL-2026-104", title: "Garbage accumulation near market", area: "Margao", department: "Waste Management", priority: "High", status: "Submitted", date: "14 Nov 2026" },
  { id: "SL-2026-103", title: "Streetlight outage", area: "Verna", department: "Electricity", priority: "Medium", status: "In Progress", date: "13 Nov 2026" },
  { id: "SL-2026-102", title: "Damaged road surface", area: "Vasco", department: "Public Works", priority: "High", status: "In Progress", date: "12 Nov 2026" },
  { id: "SL-2026-101", title: "Water leakage", area: "Panaji", department: "Water Supply", priority: "Low", status: "Resolved", date: "11 Nov 2026" },
  { id: "SL-2026-100", title: "Blocked drainage", area: "Ponda", department: "Public Works", priority: "Medium", status: "Submitted", date: "10 Nov 2026" }
];

const navigation = [
  { label: "Overview", path: "/official/dashboard", icon: LayoutDashboard },
  { label: "Complaints", path: "/official/complaints", icon: ClipboardList },
  { label: "Projects", path: "/official/projects", icon: Building2 },
  { label: "Departments", path: "/official/departments", icon: Building2 },
  { label: "Officials", path: "/official/officials", icon: Users },
  { label: "Analytics", path: "/official/analytics", icon: ChartNoAxesCombined },
  { label: "Public alerts", path: "/official/alerts", icon: BellRing }
];

function Heading({ eyebrow, title, description }) {
  return (
    <div className="op-heading">
      <div>
        <span className="op-eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <span className="op-date"><CalendarDays size={14} /> 14 NOV 2026</span>
    </div>
  );
}

function Panel({ children, className = "" }) {
  return <section className={`op-panel ${className}`}>{children}</section>;
}

export function OfficialLayout() {
  const navigate = useNavigate();
  return (
    <div className="op-app citynex-shell">
      <main className="op-main citynex-main">
        <header className="cn-topbar">
          <button className="cn-brand" onClick={() => navigate("/official/dashboard")}><span>C</span>CityNex</button>
          <nav className="cn-nav">{navigation.map(({label,path}) => <NavLink key={path} to={path}>{label}</NavLink>)}</nav>
          <div className="cn-user"><i/> LIVE CITY DATA <b>O</b><span>Goa Municipal<br/>Administration</span></div>
        </header>
        <div className="op-content cn-content"><Outlet context={{theme:"light",setTheme:()=>{}}}/></div>
      </main>
    </div>
  );
}



function ComplaintTable({ items, compact = false }) {
  return (
    <div className="op-table-wrap">
      <table className="op-table">
        <thead>
          <tr>
            <th>COMPLAINT</th>
            <th>LOCATION</th>
            {!compact && <th>DEPARTMENT</th>}
            <th>PRIORITY</th>
            <th>STATUS</th>
          </tr>
        </thead>
        <tbody>
          {items.map(item => (
            <tr key={item.id}>
              <td><strong>{item.title}</strong><small>{item.id} · {item.date}</small></td>
              <td>{item.area}</td>
              {!compact && <td>{item.department}</td>}
              <td><span className={`op-priority ${item.priority.toLowerCase()}`}>{item.priority}</span></td>
              <td><span className={`op-status ${item.status.toLowerCase().replaceAll(" ", "-")}`}>{item.status}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


const departments = [
  { name: "Public Works", lead: "Infrastructure division", count: 62, resolved: 44, color: "coral" },
  { name: "Waste Management", lead: "Sanitation division", count: 48, resolved: 39, color: "teal" },
  { name: "Electricity", lead: "Power and street lighting", count: 37, resolved: 29, color: "lime" },
  { name: "Water Supply", lead: "Water and utilities", count: 29, resolved: 24, color: "amber" }
];


export function OfficialDashboard() {
  const navigate = useNavigate();
  const [department, setDepartment] = useState("All Departments");
  const [panelTab, setPanelTab] = useState("Timeline");

  const departments = [
    { name: "Public Works", count: 62, days: "2.4 days", variant: "olive" },
    { name: "Sanitation", count: 48, days: "1.8 days", variant: "terracotta" },
    { name: "Water Supply", count: 29, days: "3.1 days", variant: "teal" }
  ];

  const stats = [
    { label: "Total complaints", value: "248", sub: "Reports received", icon: ClipboardList, color: "teal", filter: "All" },
    { label: "Pending", value: "36", sub: "Awaiting action", icon: Clock3, color: "orange", filter: "Submitted" },
    { label: "High priority", value: "23", sub: "Requires attention", icon: AlertTriangle, color: "coral", filter: "High" },
    { label: "Resolved", value: "189", sub: "Successfully closed", icon: CheckCircle2, color: "lime", filter: "Resolved" }
  ];

  const activities = [
    { title: "New complaint received", detail: "Damaged road · Margao", time: "12 min ago", icon: ClipboardList },
    { title: "Complaint assigned", detail: "Streetlight outage · Vasco", time: "38 min ago", icon: Users },
    { title: "Issue marked resolved", detail: "Water leakage · Panaji", time: "1 hr ago", icon: CheckCircle2 }
  ];

  return (
    <div className="o1-dashboard">
      <div className="o1-main">
        <header className="o1-greeting">
          <div>
            <span className="o1-eyebrow">CITYNEX / OFFICIAL WORKSPACE</span>
            <h1>Hello, Administrator!</h1>
            <p>Here's today's city operations.</p>
            <select value={department} onChange={e => setDepartment(e.target.value)} className="o1-dept-select">
              <option>All Departments</option>
              {departments.map(d => <option key={d.name}>{d.name}</option>)}
            </select>
          </div>
          <div className="o1-greeting-actions">
            <span className="o1-live"><i/> LIVE CITY DATA</span>
            <button className="o1-avatar">AD</button>
          </div>
        </header>

        <section className="o1-hero-metric">
          <div className="o1-hero-top">
            <div>
              <span className="o1-eyebrow">CITY RESOLUTION RATE</span>
              <div className="o1-hero-number">84<span>%</span><small>+6 pts</small></div>
              <p>Excellent <span>· Updated today</span></p>
            </div>
            <div className="o1-hero-mini">
              <span>ON-TIME RESOLUTION</span>
              <strong>24 / 38</strong>
              <small>Complaints within SLA</small>
            </div>
          </div>
          <div className="o1-range">
            <div className="o1-range-segment slow"><i/><i/><i/><i/></div>
            <div className="o1-range-segment average"><i/><i/><i/><i/></div>
            <div className="o1-range-segment fast"><i/><i/><i/><i/></div>
            <div className="o1-range-marker"><b/></div>
          </div>
          <div className="o1-range-labels"><span>0% · Needs attention</span><span>60% · Average</span><span>80% · Excellent</span><span>100%</span></div>
        </section>

        <section className="o1-stat-grid">
          {stats.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <button className="o1-stat-card" key={stat.label} onClick={() => navigate(`/official/complaints?filter=${stat.filter}`)}>
                <div className="o1-stat-card-top">
                  <span className={`o1-stat-icon ${stat.color}`}><Icon size={18}/></span>
                  {index === 2 && <span className="o1-alert-dot"/>}
                  <span className="o1-stat-arrow"><ArrowUpRight size={16}/></span>
                </div>
                <span className="o1-stat-title">{stat.label}</span>
                <div className="o1-stat-bottom">
                  <strong>{stat.value}</strong>
                  <span className="o1-dot-matrix">
                    {Array.from({length:10},(_,i)=><i key={i} className={i < (index === 0 ? 8 : index === 1 ? 3 : index === 2 ? 2 : 9) ? "filled" : ""}/>)}
                  </span>
                </div>
                <small>{stat.sub}</small>
              </button>
            );
          })}
        </section>

        <section className="o1-section-heading">
          <div><span className="o1-eyebrow">DEPARTMENT PERFORMANCE</span><h2>Department breakdown</h2></div>
          <button onClick={() => navigate("/official/departments")}>View all <ArrowUpRight size={15}/></button>
        </section>

        <section className="o1-glass-grid">
          {departments.filter(d => department === "All Departments" || d.name === department).map(d => (
            <button className={`o1-glass-card ${d.variant}`} key={d.name} onClick={() => navigate("/official/departments")}>
              <div className="o1-glass-head">
                <span className="o1-glass-symbol"><Building2 size={18}/></span>
                <span className="o1-glass-open"><ArrowUpRight size={17}/></span>
              </div>
              <span className="o1-glass-title">{d.name}</span>
              <span className="o1-glass-caption">Assigned complaints</span>
              <strong>{d.count}</strong>
              <div className="o1-glass-foot"><span>Average resolution</span><b>{d.days}</b></div>
            </button>
          ))}
        </section>

        <section className="o1-activity-section">
          <div className="o1-section-heading">
            <div><span className="o1-eyebrow">CITY UPDATES</span><h2>Recent activity</h2></div>
            <button onClick={() => navigate("/official/complaints")}>See register <ArrowUpRight size={15}/></button>
          </div>
          <div className="o1-activity-list">
            {activities.map((a,i) => {
              const Icon = a.icon;
              return <button key={i} className="o1-activity-row" onClick={() => navigate("/official/complaints")}>
                <span className="o1-activity-icon"><Icon size={17}/></span>
                <span className="o1-activity-copy"><b>{a.title}</b><small>{a.detail}</small></span>
                <span className="o1-activity-time">{a.time}</span>
                <ChevronRight size={16}/>
              </button>;
            })}
          </div>
        </section>

        <section className="o1-bottom-grid">
          <article className="o1-chart-card">
            <div className="o1-card-heading"><div><span className="o1-eyebrow">LAST 30 DAYS</span><h2>Complaints trend</h2></div><span className="o1-chart-total">248 <small>reports</small></span></div>
            <div className="o1-chart-legend"><span><i/> Received</span><span><i/> Resolved</span></div>
            <svg viewBox="0 0 540 150" preserveAspectRatio="none" className="o1-chart-svg">
              <path d="M0 118H540 M0 78H540 M0 38H540" stroke="rgba(0,0,0,.07)" strokeDasharray="3 5" fill="none"/>
              <path d="M0 104 C30 96 40 65 75 78 S120 110 150 82 S195 42 225 63 S270 100 300 70 S340 50 375 66 S420 104 450 61 S500 36 540 44" fill="none" stroke="#0E0E0E" strokeWidth="2.5" strokeLinecap="round"/>
              <path d="M0 125 C35 119 55 105 80 111 S130 125 160 106 S210 92 240 105 S290 118 320 95 S370 88 400 99 S455 112 485 85 S520 82 540 74" fill="none" stroke="#00BCB4" strokeWidth="2.5" strokeLinecap="round"/>
              <circle cx="375" cy="66" r="15" fill="#E1EE32"/><text x="375" y="70" textAnchor="middle" fontSize="10" fontWeight="700" fill="#0E0E0E">84</text>
            </svg>
            <div className="o1-chart-axis"><span>01 NOV</span><span>07 NOV</span><span>14 NOV</span><span>21 NOV</span><span>30 NOV</span></div>
          </article>

          <article className="o1-priority-card">
            <div className="o1-card-heading"><div><span className="o1-eyebrow">OPEN REPORTS</span><h2>Priority breakdown</h2></div></div>
            <div className="o1-priority-total">36 <small>open complaints</small></div>
            <div className="o1-priority-bar"><i/><i/><i/><i/></div>
            <div className="o1-priority-list">
              <span><i className="critical"/>Critical <b>04</b></span>
              <span><i className="high"/>High <b>09</b></span>
              <span><i className="medium"/>Medium <b>14</b></span>
              <span><i className="low"/>Low <b>09</b></span>
            </div>
          </article>
        </section>
      </div>

      <aside className="o1-detail-panel">
        <div className="o1-detail-top">
          <span className="o1-detail-logo"><Building2 size={17}/></span>
          <b>CityNex Operations</b>
          <button aria-label="Close panel"><span>×</span></button>
        </div>
        <span className="o1-detail-label">RESOLUTION PERFORMANCE</span>
        <div className="o1-detail-number">84<small>%</small></div>
        <div className="o1-detail-ring"><span>84%</span></div>
        <div className="o1-detail-caption">Overall city resolution rate</div>
        <div className="o1-detail-progress">
          <div><span>Monthly target</span><b>84 / 90%</b></div>
          <i><span/></i>
          <small>6 percentage points to target</small>
        </div>
        <div className="o1-detail-tabs">
          {["Details","Timeline","Updates"].map(t => <button key={t} className={panelTab===t?"active":""} onClick={()=>setPanelTab(t)}>{t}</button>)}
        </div>
        {panelTab === "Timeline" && <div className="o1-panel-body">
          <div className="o1-panel-year"><b>November 2026</b><small>Monthly service activity</small></div>
          <div className="o1-month-grid">
            {["01","02","03","04","05","06","07","08","09","10","11","12"].map((m,i)=><div key={m} className={i%4===0?"marked":""}><small>{m} NOV</small><span>{i<9?"✓":i===9?"•":"×"}</span></div>)}
          </div>
        </div>}
        {panelTab === "Details" && <div className="o1-panel-body"><p>Citywide complaints are being monitored across all municipal departments. The current resolution rate is above the operational baseline.</p><div className="o1-panel-fact"><small>TOTAL REPORTS</small><b>248</b></div><div className="o1-panel-fact"><small>RESOLVED</small><b>189</b></div><div className="o1-panel-fact"><small>OPEN</small><b>36</b></div></div>}
        {panelTab === "Updates" && <div className="o1-panel-body"><div className="o1-panel-update"><b>Resolution rate improved</b><small>Today · +6 points this month</small></div><div className="o1-panel-update"><b>New reports registered</b><small>Today · 12 new submissions</small></div><div className="o1-panel-update"><b>Department review completed</b><small>Yesterday · 4 departments</small></div></div>}
        <button className="o1-panel-action" onClick={()=>navigate("/official/complaints")}>Open complaint register <ArrowUpRight size={16}/></button>
      </aside>
    </div>
  );
}


const complaintFiles = [
  { id:"CN-2026-104", title:"Garbage accumulation near market", subtitle:"Market Road · Margao", department:"Sanitation", category:"Waste Management", date:"Nov 14, 2026", status:"Submitted", priority:"High", citizen:"Riya Naik", reports:3, type:"image", description:"Uncollected waste has accumulated near the market entrance, causing inconvenience to pedestrians and nearby shops." },
  { id:"CN-2026-103", title:"Damaged streetlight near junction", subtitle:"Airport Road · Vasco", department:"Public Works", category:"Street Lighting", date:"Nov 13, 2026", status:"In Progress", priority:"Medium", citizen:"Aarav Kamat", reports:1, type:"document", description:"Streetlight is not functioning near the road junction." },
  { id:"CN-2026-102", title:"Water leakage on main road", subtitle:"Church Street · Panaji", department:"Water Supply", category:"Water Supply", date:"Nov 12, 2026", status:"Under Review", priority:"High", citizen:"Mira Dessai", reports:2, type:"image", description:"Continuous water leakage is affecting the road surface." },
  { id:"CN-2026-101", title:"Pothole reported on service road", subtitle:"Verna Industrial Estate · Verna", department:"Public Works", category:"Roads", date:"Nov 11, 2026", status:"Resolved", priority:"Low", citizen:"Neil Rodrigues", reports:1, type:"document", description:"A pothole was reported on the service road and has been repaired." },
  { id:"CN-2026-100", title:"Blocked drainage outside school", subtitle:"Ponda Municipal Area · Ponda", department:"Sanitation", category:"Drainage", date:"Nov 10, 2026", status:"Assigned", priority:"Medium", citizen:"Sana Fernandes", reports:4, type:"image", description:"Drainage is blocked near the school entrance." }
];

export function OfficialComplaints() {
  const [activeDepartment, setActiveDepartment] = useState("All");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(null);
  const [checked, setChecked] = useState([]);
  const [statusFilter, setStatusFilter] = useState("All");
  const [uploadedName, setUploadedName] = useState("");

  const deptCards = [
    { name:"Public Works", number:"2", date:"Nov 14, 2026", initials:["AN","RK","JD"] },
    { name:"Sanitation", number:"2", date:"Nov 13, 2026", initials:["RD","SF","MK"] },
    { name:"Water Supply", number:"1", date:"Nov 12, 2026", initials:["PK","ND"] }
  ];

  const filtered = complaintFiles.filter(item =>
    (activeDepartment === "All" || item.department === activeDepartment) &&
    (statusFilter === "All" || item.status === statusFilter) &&
    `${item.id} ${item.title} ${item.subtitle} ${item.citizen}`.toLowerCase().includes(query.toLowerCase())
  );

  const toggleChecked = id => setChecked(old => old.includes(id) ? old.filter(x=>x!==id) : [...old,id]);

  return (
    <div className="o2-complaints">
      <div className="o2-left-profile">
        <div className="o2-profile-head">
          <div className="o2-profile-avatar">AD</div>
          <b>Administrator</b>
          <small>GOA MUNICIPAL OFFICE</small>
          <span className="o2-profile-status"><i/> ACTIVE SESSION</span>
        </div>
        <div className="o2-upload-area">
          <label className="o2-upload-icon">
            <input type="file" multiple onChange={e=>setUploadedName(Array.from(e.target.files || []).map(f=>f.name).join(", "))}/>
            <span>↑</span>
          </label>
          <b>Drop files here</b>
          <p>PDF, DOC, XLSX, image files, etc.<br/>Files up to 15 MB.</p>
          {uploadedName && <small className="o2-uploaded">{uploadedName}</small>}
        </div>
        <div className="o2-upload-foot"><span>COMPLAINT EVIDENCE</span><small>Secure document area</small></div>
      </div>

      <div className="o2-content">
        <div className="o2-department-cards">
          {deptCards.map((d,i)=><button key={d.name} onClick={()=>setActiveDepartment(activeDepartment===d.name?"All":d.name)} className={`o2-dept-card dept-${i} ${activeDepartment===d.name?"selected":""}`}>
            <div className="o2-dept-card-top"><span>{d.number}</span><span>•••</span></div>
            <h3>{d.name}</h3>
            <p>{d.date}</p>
            <div className="o2-avatar-stack">{d.initials.map((x,j)=><i key={j}>{x}</i>)}</div>
            <span className="o2-dept-card-hint">{activeDepartment===d.name?"Selected department":"View department reports"}</span>
          </button>)}
        </div>

        <div className="o2-list-toolbar">
          <div className="o2-list-title"><span className="o1-eyebrow">OFFICIAL RECORDS</span><h1>Complaints</h1></div>
          <div className="o2-search"><Search size={16}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Quick Search"/></div>
          <select value={statusFilter} onChange={e=>setStatusFilter(e.target.value)} className="o2-filter">
            {["All","Submitted","Under Review","Assigned","In Progress","Resolved"].map(s=><option key={s}>{s}</option>)}
          </select>
        </div>

        <div className="o2-table-head"><span className="o2-check-cell"> </span><span>NAME</span><span>DEPARTMENT</span><span>DATE</span></div>
        <div className="o2-file-list">
          {filtered.map(item=><div className={`o2-file-row ${selected?.id===item.id?"active":""}`} key={item.id}>
            <label className="o2-check-cell"><input type="checkbox" checked={checked.includes(item.id)} onChange={()=>toggleChecked(item.id)}/></label>
            <button className="o2-file-main" onClick={()=>setSelected(item)}>
              <span className={`o2-file-icon ${item.type}`}>{item.type==="image"?"▧":"DOC"}</span>
              <span className="o2-file-copy"><b>{item.title}</b><small>{item.id} · {item.citizen} · {item.reports>1?`${item.reports} similar reports`:"1 report"}</small><em>{item.subtitle}</em></span>
            </button>
            <span className="o2-file-department">{item.department}<small className={`o2-status ${item.status.toLowerCase().replaceAll(" ","-")}`}>{item.status}</small></span>
            <span className="o2-file-date">{item.date}</span>
          </div>)}
          {filtered.length===0 && <div className="o2-empty">No complaints match your search.</div>}
        </div>
        <div className="o2-list-footer"><span>{filtered.length} RECORDS SHOWN</span><span>{checked.length} SELECTED</span></div>
      </div>

      {selected && <div className="o2-detail-backdrop" onClick={()=>setSelected(null)}>
        <aside className="o2-detail-drawer" onClick={e=>e.stopPropagation()}>
          <div className="o2-drawer-head"><span>COMPLAINT DETAILS</span><button onClick={()=>setSelected(null)}>×</button></div>
          <small className="o2-drawer-id">{selected.id}</small>
          <h2>{selected.title}</h2>
          <p>{selected.description}</p>
          <div className="o2-drawer-meta"><span>{selected.department}</span><span>{selected.priority} priority</span></div>
          <div className="o2-drawer-field"><small>REPORTED BY</small><b>{selected.citizen}</b></div>
          <div className="o2-drawer-field"><small>LOCATION</small><b><MapPin size={14}/>{selected.subtitle}</b></div>
          <div className="o2-drawer-field"><small>SIMILAR REPORTS</small><b>{selected.reports}</b></div>
          <div className="o2-drawer-field"><small>STATUS</small><select defaultValue={selected.status} onChange={e=>selected.status=e.target.value}><option>Submitted</option><option>Under Review</option><option>Assigned</option><option>In Progress</option><option>Resolved</option></select></div>
          <div className="o2-drawer-timeline"><b>STATUS TIMELINE</b><span>Submitted ✓</span><span>Under Review ✓</span><span>Assigned ○</span><span>In Progress ○</span><span>Resolved ○</span></div>
          <button className="o2-drawer-action" onClick={()=>setSelected(null)}>Save and close</button>
        </aside>
      </div>}
    </div>
  );
}


const cityDepartments = [
  { name:"Public Works", subtitle:"Roads · Infrastructure · Street lighting", count:"62", resolved:"44", image:"https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=900&q=85", tag:"INFRASTRUCTURE", color:"teal" },
  { name:"Sanitation", subtitle:"Waste management · Drainage · Cleanliness", count:"48", resolved:"39", image:"https://images.unsplash.com/photo-1532996122724-e3c354a0b15b?auto=format&fit=crop&w=900&q=85", tag:"CLEAN CITY", color:"lime" },
  { name:"Water Supply", subtitle:"Pipelines · Water quality · Utilities", count:"29", resolved:"24", image:"https://images.unsplash.com/photo-1530053969600-caed2596d242?auto=format&fit=crop&w=900&q=85", tag:"WATER & UTILITIES", color:"coral" }
];

export function OfficialDepartments() {
  const navigate = useNavigate();

  return (
    <div className="o3-departments">
      <div className="o3-heading">
        <span className="o1-eyebrow">CITYNEX / MUNICIPAL ADMINISTRATION</span>
        <h1>Departments</h1>
        <p>Explore departments and their current service performance.</p>
      </div>
      <div className="o3-department-grid">
        {cityDepartments.map((d,i)=><article className={`o3-department-card card-${i}`} key={d.name}>
          <img src={d.image} alt={d.name}/>
          <div className="o3-card-shade"/>
          <div className="o3-card-content">
            <div className="o3-card-top"><span>{d.tag}</span><b>{d.count} REPORTS</b></div>
            <div>
              <h2>{d.name}</h2>
              <p>{d.subtitle}</p>
              <div className="o3-card-tags"><span>{d.resolved} resolved</span><span>{Number(d.count)-Number(d.resolved)} active</span></div>
            </div>
            <button onClick={()=>navigate("/official/complaints?department="+encodeURIComponent(d.name))}>View department <ArrowUpRight size={15}/></button>
          </div>
        </article>)}
      </div>
    </div>
  );
}


export function OfficialAnalytics() {
  const bars = [
    { label: "Public Works", value: 82 },
    { label: "Waste", value: 68 },
    { label: "Electricity", value: 76 },
    { label: "Water", value: 91 },
    { label: "Safety", value: 58 }
  ];

  return (
    <>
      <Heading
        eyebrow="DATA AND PERFORMANCE"
        title="City intelligence."
        description="Understand complaint trends and department response performance."
      />

      <div className="op-stat-grid">
        <div className="op-stat"><span>Reports this month</span><strong>186</strong><small>Illustrative data</small><FileText /></div>
        <div className="op-stat"><span>Resolution rate</span><strong>84%</strong><small>Across departments</small><CheckCircle2 /></div>
        <div className="op-stat"><span>Average response</span><strong>2.4d</strong><small>Time to first action</small><Clock3 /></div>
        <div className="op-stat"><span>Active departments</span><strong>12</strong><small>Connected divisions</small><Users /></div>
      </div>

      <Panel>
        <span className="op-eyebrow">DEPARTMENT PERFORMANCE</span>
        <h2>Resolution by department</h2>
        <div className="op-bar-chart">
          {bars.map(b => (
            <div className="op-bar-row" key={b.label}>
              <span>{b.label}</span>
              <div><i style={{ width: `${b.value}%` }} /></div>
              <strong>{b.value}%</strong>
            </div>
          ))}
        </div>
      </Panel>

      <Panel>
        <span className="op-eyebrow">REPORT INSIGHTS</span>
        <h2>Operational observations</h2>
        <div className="op-insight"><TrendingUp /><div><strong>Strong water supply resolution</strong><span>Water Supply shows the highest illustrative resolution rate in this dashboard.</span></div></div>
        <div className="op-insight"><AlertTriangle /><div><strong>Review high-priority complaints</strong><span>Prioritise unresolved infrastructure and sanitation reports.</span></div></div>
      </Panel>
    </>
  );
}

export function OfficialAlerts() {
  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [level, setLevel] = useState("General");
  const [alerts, setAlerts] = useState([
    { title: "Public advisory: monsoon preparedness", message: "Follow official safety guidance during heavy rainfall.", level: "Advisory", date: "12 Nov 2026" },
    { title: "Water supply maintenance", message: "Scheduled maintenance in selected areas.", level: "General", date: "10 Nov 2026" }
  ]);

  function publish(e) {
    e.preventDefault();
    setAlerts(old => [
      { title, message, level, date: new Date().toLocaleDateString("en-IN") },
      ...old
    ]);
    setTitle("");
    setMessage("");
  }

  return (
    <>
      <Heading
        eyebrow="PUBLIC COMMUNICATIONS"
        title="Alerts centre."
        description="Prepare public notices and manage community-facing announcements."
      />

      <Panel>
        <span className="op-eyebrow">CREATE ANNOUNCEMENT</span>
        <h2>Publish a public alert</h2>
        <form className="op-alert-form" onSubmit={publish}>
          <label>Alert title<input value={title} onChange={e => setTitle(e.target.value)} placeholder="Enter announcement title" required /></label>
          <label>Message<textarea value={message} onChange={e => setMessage(e.target.value)} rows="4" placeholder="Write the public announcement..." required /></label>
          <label>Alert type
            <select value={level} onChange={e => setLevel(e.target.value)}>
              <option>General</option><option>Advisory</option><option>Emergency</option>
            </select>
          </label>
          <button className="op-primary-button" type="submit">Publish alert <ArrowUpRight size={16} /></button>
        </form>
      </Panel>

      <Panel>
        <span className="op-eyebrow">ANNOUNCEMENT REGISTER</span>
        <h2>Recent public alerts</h2>
        {alerts.map((a, i) => (
          <div className="op-alert-item" key={`${a.title}-${i}`}>
            <div>
              <span className={`op-alert-level ${a.level.toLowerCase()}`}>{a.level}</span>
              <h3>{a.title}</h3>
              <p>{a.message}</p>
              <small>{a.date}</small>
            </div>
          </div>
        ))}
      </Panel>
    </>
  );
}

export function OfficialSettings() {
  const { theme, setTheme } = useOutletContext();

  return (
    <>
      <Heading
        eyebrow="OFFICIAL ACCOUNT"
        title="Settings."
        description="Manage your workspace appearance and administrator profile."
      />
      <div className="op-settings-grid">
        <Panel>
          <span className="op-eyebrow">APPEARANCE</span>
          <h2>Display preference</h2>
          <p className="op-muted">Your theme preference is shared across the SMART LAND portal.</p>
          <div className="op-theme-options">
            <button className={theme === "light" ? "chosen" : ""} onClick={() => setTheme("light")}><Sun /><strong>Light mode</strong></button>
            <button className={theme === "dark" ? "chosen" : ""} onClick={() => setTheme("dark")}><Moon /><strong>Dark mode</strong></button>
          </div>
        </Panel>

        <Panel>
          <span className="op-eyebrow">ADMINISTRATOR PROFILE</span>
          <h2>Official account</h2>
          <div className="op-profile-row"><Users /><div><span>Account type</span><strong>Government Official</strong></div></div>
          <div className="op-profile-row"><Building2 /><div><span>Department</span><strong>Administration</strong></div></div>
          <div className="op-profile-row"><MapPin /><div><span>Jurisdiction</span><strong>Goa, India</strong></div></div>
          <p className="op-muted">Connect verified official identity and role permissions to the backend.</p>
        </Panel>
      </div>
    </>
  );
}


const officialDirectory = [
  { name: "Melvin Sherman", role: "Chief Municipal Officer", department: "Administration", area: "Panaji", email: "melvin.sherman@citynex.gov.in", phone: "+91 832 240 1001", status: "Available", initials: "MS" },
  { name: "Ananya Naik", role: "Executive Engineer", department: "Public Works", area: "Margao", email: "ananya.naik@citynex.gov.in", phone: "+91 832 240 1002", status: "On duty", initials: "AN" },
  { name: "Rohan Dessai", role: "Sanitation Officer", department: "Waste Management", area: "Mapusa", email: "rohan.dessai@citynex.gov.in", phone: "+91 832 240 1003", status: "Available", initials: "RD" },
  { name: "Priya Kamat", role: "Water Supply Engineer", department: "Water Supply", area: "Ponda", email: "priya.kamat@citynex.gov.in", phone: "+91 832 240 1004", status: "On duty", initials: "PK" },
  { name: "Aarav Parsekar", role: "Electrical Inspector", department: "Electricity", area: "Vasco", email: "aarav.parsekar@citynex.gov.in", phone: "+91 832 240 1005", status: "Unavailable", initials: "AP" },
  { name: "Sana Fernandes", role: "Public Health Officer", department: "Public Health", area: "Panaji", email: "sana.fernandes@citynex.gov.in", phone: "+91 832 240 1006", status: "Available", initials: "SF" },
  { name: "Neil Rodrigues", role: "Traffic Operations Officer", department: "Traffic & Roads", area: "Verna", email: "neil.rodrigues@citynex.gov.in", phone: "+91 832 240 1007", status: "On duty", initials: "NR" },
  { name: "Mira Sawant", role: "Emergency Coordination Officer", department: "Emergency Services", area: "Margao", email: "mira.sawant@citynex.gov.in", phone: "+91 832 240 1008", status: "Available", initials: "MS" }
];

export function OfficialDirectory() {
  const [department, setDepartment] = useState("All Departments");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(officialDirectory[0]);
  const departmentsList = ["All Departments", ...new Set(officialDirectory.map(o => o.department))];
  const visible = officialDirectory.filter(o =>
    (department === "All Departments" || o.department === department) &&
    `${o.name} ${o.role} ${o.area} ${o.department}`.toLowerCase().includes(search.toLowerCase())
  );


  return (
    <div className="cn-directory">
      <div className="cn-directory-heading">
        <div>
          <span className="cn-dir-eyebrow">CITYNEX / GOVERNMENT WORKSPACE</span>
          <h1>Officials directory<span>.</span></h1>
          <p>Find government officials and view their department, role and assigned jurisdiction.</p>
        </div>
        <div className="cn-dir-live"><i/> DIRECTORY ACTIVE <small>DEMO DIRECTORY DATA</small></div>
      </div>

      <div className="cn-dir-summary">
        <div><span>REGISTERED OFFICIALS</span><strong>{officialDirectory.length.toString().padStart(2,"0")}</strong><small>Across departments</small></div>
        <div><span>DEPARTMENTS</span><strong>{departmentsList.length - 1}</strong><small>Represented in directory</small></div>
        <div><span>AVAILABLE NOW</span><strong>{officialDirectory.filter(o => o.status === "Available").length}</strong><small>Demo availability status</small></div>
        <div><span>JURISDICTIONS</span><strong>{new Set(officialDirectory.map(o => o.area)).size}</strong><small>Assigned areas</small></div>
      </div>

      <div className="cn-dir-layout">
        <section className="cn-dir-main">
          <div className="cn-dir-toolbar">
            <div className="cn-dir-search"><Search size={17}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search official, role or area..."/></div>
            <select value={department} onChange={e=>setDepartment(e.target.value)}>
              {departmentsList.map(d=><option key={d}>{d}</option>)}
            </select>
          </div>
          <div className="cn-dir-dept-pills">
            {departmentsList.map(d=><button key={d} className={department===d?"selected":""} onClick={()=>setDepartment(d)}>{d}</button>)}
          </div>
          <div className="cn-official-list">
            {visible.map((official, index)=>(
              <button key={official.email} className={`cn-official-row ${selected.email===official.email?"chosen":""}`} onClick={()=>setSelected(official)}>
                <span className={`cn-official-avatar avatar-${index%5}`}>{official.initials}</span>
                <span className="cn-official-info"><strong>{official.name}</strong><small>{official.role}</small><em>{official.department} · {official.area}</em></span>
                <span className={`cn-official-presence ${official.status.toLowerCase().replaceAll(" ","-")}`}><i/>{official.status}</span>
                <ArrowUpRight size={17}/>
              </button>
            ))}
            {visible.length===0 && <div className="cn-dir-empty">No officials match this department or search.</div>}
          </div>
        </section>

        <aside className="cn-official-detail">
          <div className="cn-detail-top">
            <span>OFFICIAL PROFILE</span>
            <span className="cn-detail-active">VERIFIED DEMO</span>
          </div>
          <div className="cn-detail-avatar">{selected.initials}</div>
          <h2>{selected.name}</h2>
          <p>{selected.role}</p>
          <div className="cn-detail-dept">{selected.department}</div>
          <div className="cn-detail-separator"/>
          <div className="cn-detail-field"><small>ASSIGNED JURISDICTION</small><strong><MapPin size={14}/>{selected.area}, Goa</strong></div>
          <div className="cn-detail-field"><small>OFFICIAL EMAIL</small><strong><FileText size={14}/>{selected.email}</strong></div>
          <div className="cn-detail-field"><small>CONTACT NUMBER</small><strong><BellRing size={14}/>{selected.phone}</strong></div>
          <div className="cn-detail-field"><small>CURRENT AVAILABILITY</small><strong><i className={`cn-detail-status ${selected.status.toLowerCase().replaceAll(" ","-")}`}/>{selected.status}</strong></div>
          <div className="cn-detail-note">Access to personal contact details and assignment actions should be restricted to authorised administrators in the live system.</div>
        </aside>
      </div>
    </div>
  );
}


const projectData = [
  {
    id: 1,
    title: "Transparent Funding",
    category: "Local projects & initiatives",
    description: "Making municipal funding transparent and accessible. Track public spending, project budgets and development progress.",
    tags: ["Infrastructure", "Public funding"],
    image: "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=900&q=85",
    status: "In Progress",
    progress: 72,
    budget: "₹24.5 L",
    location: "Panaji"
  },
  {
    id: 2,
    title: "Inspiration & Impact",
    category: "Community development",
    description: "Supporting local initiatives that improve neighbourhoods, public spaces and community participation.",
    tags: ["Community", "Development"],
    image: "https://images.unsplash.com/photo-1511818966892-d7d671e672a2?auto=format&fit=crop&w=900&q=85",
    status: "Ongoing",
    progress: 48,
    budget: "₹18.2 L",
    location: "Margao"
  },
  {
    id: 3,
    title: "Participation & Involvement",
    category: "Democratic decision",
    description: "Giving citizens a voice in local decisions through public feedback, consultations and participatory planning.",
    tags: ["Citizen voice", "Public feedback"],
    image: "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=900&q=85",
    status: "Planning",
    progress: 25,
    budget: "₹12.8 L",
    location: "Vasco"
  }
];

const feedbackData = [
  {
    id: 1,
    initials: "RN",
    name: "Riya Naik",
    project: "Transparent Funding",
    date: "14 Nov 2026",
    rating: 5,
    message: "The project updates are helpful. It would be great to see more frequent updates on the actual expenditure and completion milestones.",
    converted: false
  },
  {
    id: 2,
    initials: "AK",
    name: "Aarav Kamat",
    project: "Inspiration & Impact",
    date: "13 Nov 2026",
    rating: 4,
    message: "Good initiative for the community. I would like to know how residents can volunteer and participate in upcoming activities.",
    converted: false
  },
  {
    id: 3,
    initials: "MD",
    name: "Mira Dessai",
    project: "Participation & Involvement",
    date: "12 Nov 2026",
    rating: 5,
    message: "Citizen participation is important. Please make sure feedback from every ward is considered before final decisions.",
    converted: true
  },
  {
    id: 4,
    initials: "SF",
    name: "Sana Fernandes",
    project: "Transparent Funding",
    date: "11 Nov 2026",
    rating: 3,
    message: "The funding information is useful, but the project timeline could be easier to understand.",
    converted: false
  }
];

export function OfficialProjectsFeedback() {
  const [activeTab, setActiveTab] = useState("Projects");
  const [selectedProject, setSelectedProject] = useState(null);
  const [feedback, setFeedback] = useState(feedbackData);
  const [feedbackFilter, setFeedbackFilter] = useState("All");
  const [showAdd, setShowAdd] = useState(false);
  const [newProject, setNewProject] = useState({
    title: "",
    category: "",
    description: ""
  });

  const filteredFeedback = feedback.filter(item =>
    feedbackFilter === "All" || item.project === feedbackFilter
  );

  const convertFeedback = id => {
    setFeedback(old =>
      old.map(item =>
        item.id === id ? { ...item, converted: true } : item
      )
    );
  };

  const addProject = e => {
    e.preventDefault();
    alert("Project form captured. Connect the backend to save this project permanently.");
    setShowAdd(false);
    setNewProject({ title: "", category: "", description: "" });
  };

  return (
    <div className="of-projects-page">

      <header className="of-projects-heading">
        <div>
          <span className="of-eyebrow">CITYNEX / DEVELOPMENT & PARTICIPATION</span>
          <h1>We help local communities & organisations build better cities.</h1>
          <p>
            Explore municipal initiatives, follow project progress and
            understand what citizens are saying about public development.
          </p>
        </div>
        <button className="of-learn-button" onClick={() => setActiveTab("Feedback")}>
          View feedback <span>↗</span>
        </button>
      </header>

      <div className="of-project-tabs">
        <button
          className={activeTab === "Projects" ? "active" : ""}
          onClick={() => setActiveTab("Projects")}
        >
          Projects <span>03</span>
        </button>

        <button
          className={activeTab === "Feedback" ? "active" : ""}
          onClick={() => setActiveTab("Feedback")}
        >
          Citizen feedback <span>{feedback.length.toString().padStart(2, "0")}</span>
        </button>

        <div className="of-tabs-spacer"/>

        {activeTab === "Projects" && (
          <button className="of-add-project" onClick={() => setShowAdd(true)}>
            + Add project
          </button>
        )}
      </div>

      {activeTab === "Projects" && (
        <>
          <div className="of-project-cards">
            {projectData.map((project, index) => (
              <article className={`of-project-card of-project-card-${index}`} key={project.id}>
                <img src={project.image} alt={project.title}/>
                <div className="of-project-overlay"/>

                <div className="of-project-card-top">
                  <span>{project.category}</span>
                  <button onClick={() => setSelectedProject(project)} aria-label="View project">
                    ↗
                  </button>
                </div>

                <div className="of-project-card-bottom">
                  <div className="of-project-card-index">
                    0{index + 1} / CITY DEVELOPMENT
                  </div>
                  <h2>{project.title}</h2>
                  <p>{project.description}</p>

                  <div className="of-project-tags">
                    {project.tags.map(tag => <span key={tag}>{tag}</span>)}
                  </div>

                  <button
                    className="of-project-explore"
                    onClick={() => setSelectedProject(project)}
                  >
                    Explore project <span>↗</span>
                  </button>
                </div>
              </article>
            ))}
          </div>

          <section className="of-project-summary">
            <div>
              <span className="of-eyebrow">CITY DEVELOPMENT OVERVIEW</span>
              <h2>Projects at a glance</h2>
            </div>
            <div className="of-project-summary-stats">
              <div><strong>03</strong><small>Active projects</small></div>
              <div><strong>₹55.5 L</strong><small>Combined budgets</small></div>
              <div><strong>48%</strong><small>Average progress</small></div>
            </div>
          </section>
        </>
      )}

      {activeTab === "Feedback" && (
        <section className="of-feedback-section">
          <div className="of-feedback-header">
            <div>
              <span className="of-eyebrow">CITIZEN VOICE / PROJECT RESPONSES</span>
              <h2>What citizens are saying.</h2>
              <p>Review feedback and convert actionable reports into complaints.</p>
            </div>

            <label className="of-feedback-filter">
              <span>Project</span>
              <select
                value={feedbackFilter}
                onChange={e => setFeedbackFilter(e.target.value)}
              >
                <option value="All">All projects</option>
                {projectData.map(project => (
                  <option key={project.id} value={project.title}>
                    {project.title}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="of-feedback-overview">
            <div><strong>{feedback.length.toString().padStart(2, "0")}</strong><small>Total feedback</small></div>
            <div><strong>{feedback.filter(f => f.converted).length.toString().padStart(2, "0")}</strong><small>Converted to complaints</small></div>
            <div>
              <strong>4.3</strong>
              <small>Average citizen rating</small>
            </div>
          </div>

          <div className="of-feedback-list">
            {filteredFeedback.map(item => (
              <article className="of-feedback-row" key={item.id}>
                <div className="of-feedback-avatar">{item.initials}</div>

                <div className="of-feedback-copy">
                  <div className="of-feedback-person">
                    <strong>{item.name}</strong>
                    <span>{item.date}</span>
                  </div>

                  <div className="of-feedback-project">{item.project}</div>

                  <div className="of-rating-stars">
                    {"★".repeat(item.rating)}
                    <span>{"★".repeat(5 - item.rating)}</span>
                  </div>

                  <p>{item.message}</p>
                </div>

                <div className="of-feedback-actions">
                  {item.converted ? (
                    <span className="of-converted">✓ Converted</span>
                  ) : (
                    <button onClick={() => convertFeedback(item.id)}>
                      Convert to complaint ↗
                    </button>
                  )}
                </div>
              </article>
            ))}

            {filteredFeedback.length === 0 && (
              <div className="of-feedback-empty">No feedback found for this project.</div>
            )}
          </div>
        </section>
      )}

      {selectedProject && (
        <div className="of-project-modal-backdrop" onClick={() => setSelectedProject(null)}>
          <aside className="of-project-modal" onClick={e => e.stopPropagation()}>
            <button className="of-project-modal-close" onClick={() => setSelectedProject(null)}>×</button>
            <img src={selectedProject.image} alt={selectedProject.title}/>
            <span className="of-eyebrow">CITY DEVELOPMENT PROJECT</span>
            <h2>{selectedProject.title}</h2>
            <p>{selectedProject.description}</p>

            <div className="of-project-modal-stats">
              <div><small>STATUS</small><b>{selectedProject.status}</b></div>
              <div><small>LOCATION</small><b>{selectedProject.location}, Goa</b></div>
              <div><small>PROJECT BUDGET</small><b>{selectedProject.budget}</b></div>
              <div><small>COMPLETION</small><b>{selectedProject.progress}%</b></div>
            </div>

            <div className="of-project-progress">
              <span style={{ width: `${selectedProject.progress}%` }}/>
            </div>

            <button className="of-project-modal-action" onClick={() => {
              setSelectedProject(null);
              setActiveTab("Feedback");
              setFeedbackFilter(selectedProject.title);
            }}>
              View citizen feedback ↗
            </button>
          </aside>
        </div>
      )}

      {showAdd && (
        <div className="of-project-modal-backdrop" onClick={() => setShowAdd(false)}>
          <form className="of-add-modal" onClick={e => e.stopPropagation()} onSubmit={addProject}>
            <button type="button" className="of-project-modal-close" onClick={() => setShowAdd(false)}>×</button>
            <span className="of-eyebrow">CITYNEX / PROJECT MANAGEMENT</span>
            <h2>Add a project.</h2>

            <label>
              Project name
              <input
                required
                value={newProject.title}
                onChange={e => setNewProject({ ...newProject, title: e.target.value })}
                placeholder="Enter project name"
              />
            </label>

            <label>
              Category
              <input
                required
                value={newProject.category}
                onChange={e => setNewProject({ ...newProject, category: e.target.value })}
                placeholder="e.g. Infrastructure"
              />
            </label>

            <label>
              Description
              <textarea
                required
                value={newProject.description}
                onChange={e => setNewProject({ ...newProject, description: e.target.value })}
                placeholder="Describe the project..."
              />
            </label>

            <button type="submit" className="of-project-modal-action">
              Save project ↗
            </button>
            <small className="of-demo-note">
              Demo form only — connect your backend to persist new projects.
            </small>
          </form>
        </div>
      )}

    </div>
  );
}
