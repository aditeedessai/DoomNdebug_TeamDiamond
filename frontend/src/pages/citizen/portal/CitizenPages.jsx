
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { useState } from "react";
import { useOutletContext, useNavigate } from "react-router-dom";
import {
  ArrowUpRight, ArrowRight, Upload, Mic, MapPin, Search,
  Clock3, CheckCircle2, AlertTriangle, Camera, Sun, Moon,
  UserRound, Mail, Phone, Lock, Building2, FileText,
  Activity, ShieldCheck, Navigation
} from "lucide-react";
import "./CitizenPages.css";

const initialComplaints = [
  { id: "SL-2026-001", title: "Garbage accumulation", category: "Waste Management", location: "Margao, Goa", status: "In Progress", date: "12 Nov 2026" },
  { id: "SL-2026-002", title: "Streetlight not working", category: "Electricity", location: "Verna, Goa", status: "Resolved", date: "10 Nov 2026" },
  { id: "SL-2026-003", title: "Road damage", category: "Roads", location: "Vasco, Goa", status: "Submitted", date: "09 Nov 2026" },
];

function PageHeading({ eyebrow, title, description, action }) {
  return (
    <div className="cp-heading">
      <div>
        <span className="cp-eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}

function Panel({ children, className = "" }) {
  return <section className={`cp-panel ${className}`}>{children}</section>;
}

export function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", phone: "", password: "" });
  const [message, setMessage] = useState("");

  function update(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  function submit(e) {
    e.preventDefault();
    localStorage.setItem("smartland-citizen", JSON.stringify({ name: form.name, email: form.email, phone: form.phone }));
    setMessage("Account details saved for this demo. You can now sign in.");
  }

  return (
    <div className="cp-auth-page">
      <div className="cp-auth-intro">
        <span className="cp-eyebrow">JOIN SMART LAND · GOA</span>
        <h1>Your city.<br /><span>Your say.</span></h1>
        <p>Create your citizen account to report issues, track civic services and participate in building a better Goa.</p>
        <div className="cp-auth-points"><ShieldCheck /> Your civic voice matters</div>
      </div>
      <Panel className="cp-register-card">
        <span className="cp-eyebrow">CITIZEN REGISTRATION</span>
        <h2>Create your account</h2>
        <p>Enter your details to get started.</p>
        <form className="cp-form" onSubmit={submit}>
          <label>Full name<input name="name" value={form.name} onChange={update} placeholder="Your full name" required /></label>
          <label>Email address<input name="email" type="email" value={form.email} onChange={update} placeholder="you@example.com" required /></label>
          <label>Mobile number<input name="phone" type="tel" value={form.phone} onChange={update} placeholder="+91 98765 43210" required /></label>
          <label>Create password<input name="password" type="password" value={form.password} onChange={update} placeholder="At least 8 characters" minLength="8" required /></label>
          <button className="cp-primary-button" type="submit">Create citizen account <ArrowUpRight size={17} /></button>
          {message && <p className="cp-success">{message}</p>}
        </form>
        <p className="cp-auth-foot">Already registered? <button onClick={() => navigate("/citizen-login")}>Sign in</button></p>
      </Panel>
    </div>
  );
}

export function Dashboard() {
  const navigate = useNavigate();
  const saved = JSON.parse(localStorage.getItem("smartland-citizen") || "{}");
  return (
    <>
      <PageHeading eyebrow="CITIZEN OVERVIEW · GOA" title={`Good day${saved.name ? `, ${saved.name.split(" ")[0]}` : ""}.`} description="Your city, your services, your impact. Here's what's happening." action={<span className="cp-date">14 NOVEMBER 2026</span>} />
      <div className="cp-stat-grid">
        <div className="cp-stat"><span>Total complaints</span><strong>12</strong><small>Across your account</small><FileText /></div>
        <div className="cp-stat"><span>In progress</span><strong>04</strong><small>Being addressed</small><Clock3 /></div>
        <div className="cp-stat"><span>Resolved</span><strong>07</strong><small>Successfully closed</small><CheckCircle2 /></div>
        <div className="cp-stat"><span>City activity</span><strong>86%</strong><small>Service response index</small><Activity /></div>
      </div>
      <div className="cp-dashboard-grid">
        <Panel>
          <div className="cp-panel-heading"><div><span className="cp-eyebrow">TAKE ACTION</span><h2>Make your city better.</h2></div></div>
          <div className="cp-action-grid">
            <button onClick={() => navigate("/citizen/report")}><span className="cp-action-icon coral"><Camera /></span><strong>Report an issue</strong><small>Snap & Speak</small><ArrowUpRight /></button>
            <button onClick={() => navigate("/citizen/complaints")}><span className="cp-action-icon teal"><ClipboardListIcon /></span><strong>Track complaints</strong><small>View your submissions</small><ArrowUpRight /></button>
            <button onClick={() => navigate("/citizen/projects")}><span className="cp-action-icon lime"><Building2 /></span><strong>Explore projects</strong><small>See Goa's progress</small><ArrowUpRight /></button>
          </div>
        </Panel>
        <Panel>
          <span className="cp-eyebrow">YOUR IMPACT</span>
          <h2>Every report counts.</h2>
          <div className="cp-impact-number">07<span> issues resolved</span></div>
          <p className="cp-muted">Your participation helps make civic services more responsive.</p>
          <div className="cp-progress"><span /></div>
          <small className="cp-muted">7 of 12 complaints resolved</small>
        </Panel>
      </div>
      <Panel>
        <div className="cp-panel-heading"><div><span className="cp-eyebrow">RECENT ACTIVITY</span><h2>Your latest complaints</h2></div><button className="cp-text-button" onClick={() => navigate("/citizen/complaints")}>View all <ArrowRight size={15} /></button></div>
        <ComplaintRows items={initialComplaints.slice(0, 2)} />
      </Panel>
    </>
  );
}

function ClipboardListIcon() {
  return <FileText />;
}

export function Report() {
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("Roads & Infrastructure");
  const [location, setLocation] = useState("");
  const [file, setFile] = useState(null);
  const [voiceMessage, setVoiceMessage] = useState("");
  const [submitted, setSubmitted] = useState(false);

  function submit(e) {
    e.preventDefault();
    const complaints = JSON.parse(localStorage.getItem("smartland-complaints") || "[]");
    complaints.unshift({
      id: `SL-${Date.now().toString().slice(-6)}`,
      title: description.slice(0, 55),
      category,
      location: location || "Location not provided",
      status: "Submitted",
      date: new Date().toLocaleDateString("en-IN"),
    });
    localStorage.setItem("smartland-complaints", JSON.stringify(complaints));
    setSubmitted(true);
  }

  return (
    <>
      <PageHeading eyebrow="SNAP & SPEAK · CIVIC REPORTING" title="See it. Report it." description="Tell us what's happening in your neighbourhood. Your report helps the right team take action." />
      {submitted ? (
        <Panel className="cp-submitted"><CheckCircle2 size={42} /><h2>Report submitted!</h2><p>Your complaint has been saved in this demo. You can track it under My Complaints.</p><button className="cp-primary-button" onClick={() => window.location.href = "/citizen/complaints"}>View my complaints <ArrowRight size={17} /></button></Panel>
      ) : (
        <Panel className="cp-report-panel">
          <form className="cp-form" onSubmit={submit}>
            <div className="cp-form-row">
              <label>Issue category<select value={category} onChange={e => setCategory(e.target.value)}><option>Roads & Infrastructure</option><option>Waste Management</option><option>Water Supply</option><option>Electricity & Streetlights</option><option>Public Safety</option><option>Drainage</option><option>Other</option></select></label>
              <label>Location<input value={location} onChange={e => setLocation(e.target.value)} placeholder="Area, street or landmark" required /></label>
            </div>
            <label>Describe the issue<textarea rows="5" value={description} onChange={e => setDescription(e.target.value)} placeholder="Explain what happened, where it happened and any details that may help..." required /></label>
            <div className="cp-upload-box">
              <Upload size={23} />
              <strong>Add a photo or video</strong>
              <span>Attach visual evidence of the issue</span>
              <input type="file" accept="image/*,video/*" onChange={e => setFile(e.target.files?.[0] || null)} />
              {file && <small className="cp-success">{file.name}</small>}
            </div>
            <div className="cp-voice-box"><Mic size={20} /><div><strong>Voice reporting</strong><span>Voice capture can be connected to speech recognition.</span></div><button type="button" onClick={() => setVoiceMessage("Voice capture UI is ready; speech recognition needs browser permission and integration.")}>Try voice</button></div>
            {voiceMessage && <p className="cp-muted">{voiceMessage}</p>}
            <button className="cp-primary-button" type="submit">Submit civic report <ArrowUpRight size={17} /></button>
          </form>
        </Panel>
      )}
    </>
  );
}

function ComplaintRows({ items }) {
  return (
    <div className="cp-complaint-list">
      {items.map(item => (
        <div className="cp-complaint-row" key={item.id}>
          <div className="cp-complaint-icon"><FileText size={18} /></div>
          <div className="cp-complaint-details"><strong>{item.title}</strong><span>{item.id} · {item.category} · {item.date}</span></div>
          <span className={`cp-status ${item.status.toLowerCase().replaceAll(" ", "-")}`}>{item.status}</span>
        </div>
      ))}
    </div>
  );
}

export function Complaints() {
  const [filter, setFilter] = useState("All");
  const own = JSON.parse(localStorage.getItem("smartland-complaints") || "[]");
  const items = [...own, ...initialComplaints].filter(x => filter === "All" || x.status === filter);
  return (
    <>
      <PageHeading eyebrow="CITIZEN RECORDS" title="My complaints." description="Follow your reports and see how civic teams are responding." />
      <div className="cp-filter-row">{["All", "Submitted", "In Progress", "Resolved"].map(x => <button key={x} className={filter === x ? "selected" : ""} onClick={() => setFilter(x)}>{x}</button>)}</div>
      <Panel><ComplaintRows items={items} />{items.length === 0 && <p className="cp-muted">No complaints in this category yet.</p>}</Panel>
    </>
  );
}

const projects = [
  { name: "Smart street lighting", area: "Margao", progress: 78, status: "In progress", tag: "INFRASTRUCTURE" },
  { name: "Public space revitalisation", area: "Panaji", progress: 52, status: "In progress", tag: "PUBLIC SPACES" },
  { name: "Water network improvement", area: "Vasco da Gama", progress: 100, status: "Completed", tag: "WATER & UTILITIES" },
  { name: "Coastal waste management", area: "Morjim", progress: 35, status: "In progress", tag: "ENVIRONMENT" },
];

export function Projects() {
  return (
    <>
      <PageHeading eyebrow="TRANSPARENT GOVERNANCE" title="Goa in progress." description="Explore civic development initiatives and follow the work happening around your communities." />
      <div className="cp-project-grid">{projects.map(p => <Panel className="cp-project" key={p.name}><span className="cp-eyebrow">{p.tag}</span><div className="cp-project-icon"><Building2 /></div><h2>{p.name}</h2><p><MapPin size={14} /> {p.area}, Goa</p><div className="cp-progress"><span style={{ width: `${p.progress}%` }} /></div><div className="cp-project-foot"><strong>{p.progress}% complete</strong><span className={`cp-status ${p.status === "Completed" ? "resolved" : "in-progress"}`}>{p.status}</span></div></Panel>)}</div>
    </>
  );
}

export function CityMap() {
  const [search, setSearch] = useState("");
  return (
    <>
      <PageHeading eyebrow="EXPLORE YOUR CITY" title="Goa, on the map." description="Find civic services, public facilities and important places around your community." />
      <Panel className="cp-map-panel">
        <div className="cp-map-search"><Search /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search an area or civic facility..." /></div>
        <div className="cp-map-visual">
          <div className="cp-map-grid" />
          <div className="cp-map-water" />
          <span className="cp-map-label label-one">PANAJI</span>
          <span className="cp-map-label label-two">VASCO</span>
          <span className="cp-map-label label-three">MARGAO</span>
          <span className="cp-map-pin pin-one"><MapPin /></span>
          <span className="cp-map-pin pin-two"><MapPin /></span>
          <span className="cp-map-pin pin-three"><MapPin /></span>
          <div className="cp-map-placeholder"><Navigation size={20} /><strong>Goa civic map</strong><span>Map provider integration can be connected here.</span></div>
        </div>
        <p className="cp-muted">This is a visual map placeholder. Live map tiles and location services need map/API configuration.</p>
      </Panel>
    </>
  );
}

export function Safety() {
  return (
    <>
      <PageHeading eyebrow="COMMUNITY WELLBEING" title="Stay safe. Stay aware." description="Important safety information and public alerts for your community." />
      <Panel className="cp-alert-banner"><AlertTriangle size={25} /><div><strong>No active emergency alerts in this demo</strong><span>Check official local advisories for verified, real-time information.</span></div></Panel>
      <div className="cp-safety-grid">
        <Panel><span className="cp-eyebrow">EMERGENCY</span><h2>Important contacts</h2><div className="cp-contact"><strong>112</strong><span>All-in-one emergency response</span></div><div className="cp-contact"><strong>101</strong><span>Fire and rescue</span></div><div className="cp-contact"><strong>108</strong><span>Ambulance service</span></div></Panel>
        <Panel><span className="cp-eyebrow">BE PREPARED</span><h2>Community safety</h2><p className="cp-muted">Keep emergency contacts accessible, follow official instructions during severe weather and report hazards through the civic reporting portal.</p><button className="cp-secondary-button" onClick={() => window.location.href = "/citizen/report"}>Report a safety issue <ArrowUpRight size={16} /></button></Panel>
      </div>
    </>
  );
}

export function SettingsPage() {
  const { theme, setTheme } = useOutletContext();
  const saved = JSON.parse(localStorage.getItem("smartland-citizen") || "{}");
  return (
    <>
      <PageHeading eyebrow="YOUR ACCOUNT" title="Settings." description="Manage your profile, preferences and Smart Land experience." />
      <div className="cp-settings-grid">
        <Panel>
          <span className="cp-eyebrow">APPEARANCE</span><h2>Display preference</h2>
          <p className="cp-muted">Choose how SMART LAND looks across the entire portal.</p>
          <div className="cp-theme-options">
            <button className={theme === "light" ? "chosen" : ""} onClick={() => setTheme("light")}><Sun /><strong>Light mode</strong><span>Bright and clear</span></button>
            <button className={theme === "dark" ? "chosen" : ""} onClick={() => setTheme("dark")}><Moon /><strong>Dark mode</strong><span>Easy on the eyes</span></button>
          </div>
          <p className="cp-success">Your preference is saved automatically.</p>
        </Panel>
        <Panel>
          <span className="cp-eyebrow">CITIZEN PROFILE</span><h2>Account details</h2>
          <div className="cp-profile-record"><UserRound /><div><span>Full name</span><strong>{saved.name || "Citizen Account"}</strong></div></div>
          <div className="cp-profile-record"><Mail /><div><span>Email address</span><strong>{saved.email || "Not added yet"}</strong></div></div>
          <div className="cp-profile-record"><Phone /><div><span>Mobile number</span><strong>{saved.phone || "Not added yet"}</strong></div></div>
          <small className="cp-muted">Profile editing and verified identity records can be connected to the backend.</small>
        </Panel>
      </div>
    </>
  );
}
