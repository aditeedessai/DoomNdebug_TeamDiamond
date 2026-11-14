import { useEffect, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import {
  Clock3, CheckCircle2, AlertTriangle, Camera, Sun, Moon,
  UserRound, Mail, Phone, Building2, FileText,
  Activity, ShieldCheck, ArrowUpRight, ArrowRight, Upload,
  MapPin, MessageSquare, RefreshCw, X, ShieldAlert, Sparkles
} from "lucide-react";
import authService from "../../../services/authService";
import citizenService from "../../../services/citizenService";
import { useAuth } from "../../../context/AuthContext";
import CivicMap2D from "../../../components/CivicMap2D";
import "./CitizenPages.css";

// Standard Goa location centroid coordinates for auto-geocoding common locality names
const GOA_LOCALITIES = {
  panaji: { lat: 15.4989, lon: 73.8278 },
  margao: { lat: 15.2736, lon: 73.9581 },
  vasco: { lat: 15.3959, lon: 73.8157 },
  mapusa: { lat: 15.5937, lon: 73.8142 },
  ponda: { lat: 15.4026, lon: 74.0152 },
  verna: { lat: 15.3564, lon: 73.9318 },
  porvorim: { lat: 15.5342, lon: 73.8285 },
  calangute: { lat: 15.5439, lon: 73.7553 },
  candolim: { lat: 15.5173, lon: 73.7628 },
  bicholim: { lat: 15.5947, lon: 73.9525 },
};

function resolveGoaCoordinates(locationText) {
  if (!locationText) return { lat: 15.3500, lon: 73.8500 };
  const lower = locationText.toLowerCase();
  for (const [key, coords] of Object.entries(GOA_LOCALITIES)) {
    if (lower.includes(key)) {
      return coords;
    }
  }
  return { lat: 15.3500, lon: 73.8500 };
}

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

// ============================================================================
// 1. CITIZEN REGISTRATION
// ============================================================================
export function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", phone: "", password: "" });
  const [message, setMessage] = useState("");
  const [isError, setIsError] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function update(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function submit(e) {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim() || !form.password) {
      setMessage("Please fill in all required fields.");
      setIsError(true);
      return;
    }
    if (form.password.length < 6) {
      setMessage("Password must be at least 6 characters.");
      setIsError(true);
      return;
    }

    setIsSubmitting(true);
    setMessage("");
    setIsError(false);

    try {
      const res = await authService.register({
        email: form.email.trim(),
        password: form.password,
        full_name: form.name.trim(),
        phone: form.phone.trim() || undefined,
      });

      const hasSession = Boolean(res.session?.access_token || res.access_token);
      if (hasSession) {
        setMessage("Registration successful! Welcome to SMART LAND. Redirecting to your dashboard...");
        setIsError(false);
        setTimeout(() => {
          navigate("/citizen/dashboard");
        }, 1500);
      } else {
        setMessage(
          res.message
            ? `${res.message} Please check your email for confirmation or sign in with your credentials.`
            : "Registration successful! Please check your email for verification or sign in with your credentials."
        );
        setIsError(false);
        setTimeout(() => {
          navigate("/citizen-login");
        }, 2500);
      }
    } catch (err) {
      setMessage(err.userMessage || "Registration failed. The email may already be registered.");
      setIsError(true);
    } finally {
      setIsSubmitting(false);
    }
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
          <label>Full name<input name="name" value={form.name} onChange={update} placeholder="Your full name" required disabled={isSubmitting} /></label>
          <label>Email address<input name="email" type="email" value={form.email} onChange={update} placeholder="you@example.com" required disabled={isSubmitting} /></label>
          <label>Mobile number<input name="phone" type="tel" value={form.phone} onChange={update} placeholder="+91 98765 43210" disabled={isSubmitting} /></label>
          <label>Create password<input name="password" type="password" value={form.password} onChange={update} placeholder="At least 6 characters" minLength="6" required disabled={isSubmitting} /></label>
          <button className="cp-primary-button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Creating account..." : "Create citizen account"} <ArrowUpRight size={17} />
          </button>
          {message && (
            <p className={isError ? "cp-error" : "cp-success"} style={{ color: isError ? "#f87171" : "var(--sl-teal)", marginTop: "12px", fontSize: "13px" }}>
              {message}
            </p>
          )}
        </form>
        <p className="cp-auth-foot">Already registered? <button onClick={() => navigate("/citizen-login")}>Sign in</button></p>
      </Panel>
    </div>
  );
}

// ============================================================================
// 2. CITIZEN DASHBOARD
// ============================================================================
export function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function loadDashboard() {
    try {
      setLoading(true);
      setError(null);
      const data = await citizenService.getDashboardSummary();
      setSummary(data);
    } catch (err) {
      console.warn("Error fetching citizen dashboard summary:", err.message);
      setError(err.userMessage || "Unable to load dashboard data. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  const total = summary?.my_total || 0;
  const inProgress = summary?.my_in_progress || 0;
  const resolved = summary?.my_resolved || 0;
  const pending = summary?.my_pending || 0;
  const activeProjects = summary?.active_projects || 0;
  const trafficHotspots = summary?.traffic_hotspots || 0;
  const recent = summary?.recent_complaints || [];

  const resolutionPercent = total > 0 ? Math.round((resolved / total) * 100) : 0;
  const firstName = user?.full_name ? user.full_name.split(" ")[0] : "Citizen";

  return (
    <>
      <PageHeading
        eyebrow="CITIZEN OVERVIEW · GOA"
        title={`Good day, ${firstName}.`}
        description="Your city, your services, your impact. Here's what's happening."
        action={
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <button
              onClick={loadDashboard}
              className="cp-text-button"
              disabled={loading}
              title="Refresh dashboard metrics"
            >
              <RefreshCw size={13} className={loading ? "cp-spin" : ""} /> Refresh
            </button>
            <span className="cp-date">{new Date().toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" }).toUpperCase()}</span>
          </div>
        }
      />

      {error && (
        <div className="cp-error-banner">
          <AlertTriangle size={18} />
          <span>{error}</span>
          <button onClick={loadDashboard}>Retry</button>
        </div>
      )}

      {loading && !summary ? (
        <div className="cp-loading-state">
          <div className="cp-spinner" />
          <span>Loading municipal metrics...</span>
        </div>
      ) : (
        <>
          <div className="cp-stat-grid">
            <div className="cp-stat">
              <span>My complaints</span>
              <strong>{total}</strong>
              <small>{pending} awaiting review</small>
              <FileText />
            </div>
            <div className="cp-stat">
              <span>In progress</span>
              <strong>{inProgress}</strong>
              <small>Active municipal work</small>
              <Clock3 />
            </div>
            <div className="cp-stat">
              <span>Resolved</span>
              <strong>{resolved}</strong>
              <small>{resolutionPercent}% resolution rate</small>
              <CheckCircle2 />
            </div>
            <div className="cp-stat">
              <span>Active projects</span>
              <strong>{activeProjects}</strong>
              <small>{trafficHotspots} traffic zones</small>
              <Activity />
            </div>
          </div>

          <div className="cp-dashboard-grid">
            <Panel>
              <div className="cp-panel-heading">
                <div>
                  <span className="cp-eyebrow">TAKE ACTION</span>
                  <h2>Make your city better.</h2>
                </div>
              </div>
              <div className="cp-action-grid">
                <button onClick={() => navigate("/citizen/report")}>
                  <span className="cp-action-icon coral"><Camera /></span>
                  <strong>Report an issue</strong>
                  <small>Snap &amp; Speak reporting</small>
                  <ArrowUpRight />
                </button>
                <button onClick={() => navigate("/citizen/complaints")}>
                  <span className="cp-action-icon teal"><FileText /></span>
                  <strong>Track complaints</strong>
                  <small>View live progress</small>
                  <ArrowUpRight />
                </button>
                <button onClick={() => navigate("/citizen/projects")}>
                  <span className="cp-action-icon lime"><Building2 /></span>
                  <strong>Explore projects</strong>
                  <small>See municipal progress</small>
                  <ArrowUpRight />
                </button>
              </div>
            </Panel>

            <Panel>
              <span className="cp-eyebrow">YOUR IMPACT</span>
              <h2>Every report counts.</h2>
              <div className="cp-impact-number">
                {resolved}<span> {resolved === 1 ? "issue resolved" : "issues resolved"}</span>
              </div>
              <p className="cp-muted">Your participation helps make Goa's civic services more responsive and accountable.</p>
              <div className="cp-progress">
                <span style={{ width: `${Math.max(resolutionPercent, 4)}%` }} />
              </div>
              <small className="cp-muted">
                {total > 0 ? `${resolved} of ${total} complaints resolved` : "No complaints submitted yet"}
              </small>
            </Panel>
          </div>

          <Panel>
            <div className="cp-panel-heading">
              <div>
                <span className="cp-eyebrow">RECENT ACTIVITY</span>
                <h2>Your latest complaints</h2>
              </div>
              <button className="cp-text-button" onClick={() => navigate("/citizen/complaints")}>
                View all <ArrowRight size={15} />
              </button>
            </div>
            {recent.length > 0 ? (
              <div className="cp-complaint-list">
                {recent.map((item) => (
                  <div
                    className="cp-complaint-row"
                    key={item.id}
                    onClick={() => navigate("/citizen/complaints")}
                    style={{ cursor: "pointer" }}
                  >
                    <div className="cp-complaint-icon"><FileText size={18} /></div>
                    <div className="cp-complaint-details">
                      <strong>{item.title}</strong>
                      <span>{String(item.id).slice(0, 8)} · {item.category} · {new Date(item.created_at).toLocaleDateString("en-IN")}</span>
                    </div>
                    <span className={`cp-status ${String(item?.status || "Submitted").toLowerCase().replaceAll(" ", "-")}`}>{item?.status || "Submitted"}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="cp-empty-state">
                <p>You haven't submitted any complaints yet.</p>
                <button
                  className="cp-secondary-button"
                  onClick={() => navigate("/citizen/report")}
                  style={{ marginTop: "10px" }}
                >
                  Submit your first civic report <ArrowUpRight size={15} />
                </button>
              </div>
            )}
          </Panel>
        </>
      )}
    </>
  );
}

// ============================================================================
// 3. REPORT A COMPLAINT ("Snap & Speak")
// ============================================================================
export function Report() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("Roads & Infrastructure");
  const [location, setLocation] = useState("");
  const [file, setFile] = useState(null);
  const [voiceNotice, setVoiceNotice] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [submittedData, setSubmittedData] = useState(null);

  const categories = [
    "Roads & Infrastructure",
    "Sanitation & Waste",
    "Water & Utilities",
    "Electricity & Lighting",
    "Public Safety",
    "Other",
  ];

  function handleFileChange(e) {
    const selected = e.target.files?.[0];
    if (!selected) {
      setFile(null);
      return;
    }

    // Validate image format
    const validTypes = ["image/jpeg", "image/png", "image/webp"];
    if (!validTypes.includes(selected.type)) {
      setErrorMessage("Unsupported file format. Please upload a JPEG, PNG, or WebP photograph.");
      e.target.value = "";
      setFile(null);
      return;
    }

    // Validate size (max 5 MB)
    const maxBytes = 5 * 1024 * 1024;
    if (selected.size > maxBytes) {
      setErrorMessage("File exceeds the 5 MB limit. Please choose a smaller photograph.");
      e.target.value = "";
      setFile(null);
      return;
    }

    setErrorMessage("");
    setFile(selected);
  }

  async function submit(e) {
    e.preventDefault();
    if (description.trim().length < 5) {
      setErrorMessage("Please provide a description with at least 5 characters.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage("");

    try {
      let uploadedImagePath = null;

      // 1. Upload photograph if attached
      if (file) {
        try {
          const uploadRes = await citizenService.uploadImage(file);
          uploadedImagePath = uploadRes.image_path;
        } catch (uploadErr) {
          throw new Error(uploadErr.userMessage || "Photograph upload failed. Please verify format and size.");
        }
      }

      // 2. Resolve coordinates
      const coords = resolveGoaCoordinates(location);

      // 3. Build complaint create payload strictly matching backend schema
      const complaintTitle = title.trim() || description.trim().slice(0, 80);
      const payload = {
        title: complaintTitle.length >= 3 ? complaintTitle : `${category} issue in ${location || "Goa"}`,
        description: description.trim(),
        latitude: coords.lat,
        longitude: coords.lon,
        category: category,
        issue_type: category === "Roads & Infrastructure" ? "Road or Footpath Damage" :
                    category === "Sanitation & Waste" ? "Garbage Accumulation" :
                    category === "Water & Utilities" ? "Water Leakage or Blockage" :
                    category === "Electricity & Lighting" ? "Streetlight or Power Issue" :
                    category === "Public Safety" ? "Unsafe Civic Infrastructure" : "Civic Concern",
        image_url: uploadedImagePath || undefined,
        safety_related: category === "Public Safety",
        safety_category: category === "Public Safety" ? "Location feels unsafe" : undefined,
      };

      const result = await citizenService.createComplaint(payload);
      setSubmittedData(result);
    } catch (err) {
      setErrorMessage(err.userMessage || err.message || "Failed to submit civic report. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <>
      <PageHeading
        eyebrow="SNAP &amp; SPEAK · CIVIC REPORTING"
        title="See it. Report it."
        description="Tell us what's happening in your neighbourhood. Your report helps municipal teams take action."
      />

      {submittedData ? (
        <Panel className="cp-submitted">
          <CheckCircle2 size={46} />
          <h2>Report submitted successfully!</h2>
          <p>
            Your complaint has been assigned Reference <strong>#{submittedData.id}</strong>.
            Our AI pipeline has routed it to the <strong>{submittedData.department_name || submittedData.category}</strong> department
            with <strong>{submittedData.priority}</strong> priority.
          </p>
          <div style={{ display: "flex", gap: "12px", justifyContent: "center", marginTop: "20px" }}>
            <button className="cp-primary-button" onClick={() => navigate("/citizen/complaints")}>
              View my complaints <ArrowRight size={17} />
            </button>
            <button
              className="cp-secondary-button"
              onClick={() => {
                setSubmittedData(null);
                setTitle("");
                setDescription("");
                setLocation("");
                setFile(null);
              }}
            >
              Report another issue
            </button>
          </div>
        </Panel>
      ) : (
        <Panel className="cp-report-panel">
          {errorMessage && (
            <div className="cp-error-banner">
              <AlertTriangle size={18} />
              <span>{errorMessage}</span>
            </div>
          )}

          <form className="cp-form" onSubmit={submit}>
            <div className="cp-form-row">
              <label>
                Issue category
                <select value={category} onChange={e => setCategory(e.target.value)} disabled={isSubmitting}>
                  {categories.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </label>

              <label>
                Location / Landmark
                <input
                  value={location}
                  onChange={e => setLocation(e.target.value)}
                  placeholder="e.g. Near Bus Stand, Margao, or Panaji Market"
                  required
                  disabled={isSubmitting}
                />
              </label>
            </div>

            <label>
              Brief summary (optional)
              <input
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="Short title for your complaint (e.g. Deep pothole on main road)"
                disabled={isSubmitting}
              />
            </label>

            <label>
              Describe the issue
              <textarea
                rows="5"
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="Explain what happened, where it happened, and any details that will help civic workers locate and resolve it..."
                required
                minLength={5}
                disabled={isSubmitting}
              />
            </label>

            <div className="cp-upload-box">
              <Upload size={23} />
              <strong>Add a photograph</strong>
              <span>Attach visual evidence (JPEG, PNG, WebP up to 5 MB)</span>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleFileChange}
                disabled={isSubmitting}
              />
              {file && <small className="cp-success">Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)</small>}
            </div>

            <div className="cp-voice-box">
              <Camera size={20} />
              <div>
                <strong>AI Multimodal Analysis</strong>
                <span>Photos are automatically classified by Google Gemini AI for department routing, duplicate detection, and priority assignment.</span>
              </div>
            </div>

            <button className="cp-primary-button" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Submitting to Municipal AI..." : "Submit civic report"} <ArrowUpRight size={17} />
            </button>
          </form>
        </Panel>
      )}
    </>
  );
}

// ============================================================================
// 4. MY COMPLAINTS (LIST, FILTER, & DETAIL DRAWER)
// ============================================================================
export function Complaints() {
  const [complaints, setComplaints] = useState([]);
  const [filter, setFilter] = useState("All");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Selected complaint detail state
  const [selectedComplaint, setSelectedComplaint] = useState(null);

  async function loadComplaints() {
    try {
      setLoading(true);
      setError(null);
      const data = await citizenService.getMyComplaints();
      setComplaints(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn("Failed to load complaints:", err.message);
      setError(err.userMessage || "Failed to load complaints. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadComplaints();
  }, []);

  async function openComplaintDetail(id) {
    try {
      const detail = await citizenService.getComplaintById(id);
      setSelectedComplaint(detail);
    } catch (err) {
      console.warn("Failed to retrieve complaint detail:", err.message);
      // Fallback to local item if detail call fails
      const fallback = complaints.find(c => c.id === id);
      if (fallback) setSelectedComplaint(fallback);
    }
  }

  const statuses = [
    "All",
    "Submitted",
    "Under Review",
    "Assigned",
    "In Progress",
    "Resolved",
    "Rejected",
    "Needs More Information",
  ];
  const filtered = complaints.filter(c => filter === "All" || c.status === filter);

  return (
    <>
      <PageHeading
        eyebrow="CITIZEN RECORDS"
        title="My complaints."
        description="Follow your reports and see how civic teams are responding."
        action={
          <button onClick={loadComplaints} className="cp-text-button" disabled={loading}>
            <RefreshCw size={13} className={loading ? "cp-spin" : ""} /> Refresh
          </button>
        }
      />

      <div className="cp-filter-row">
        {statuses.map(s => (
          <button
            key={s}
            className={filter === s ? "selected" : ""}
            onClick={() => setFilter(s)}
          >
            {s}
          </button>
        ))}
      </div>

      {error && (
        <div className="cp-error-banner">
          <AlertTriangle size={18} />
          <span>{error}</span>
          <button onClick={loadComplaints}>Retry</button>
        </div>
      )}

      <Panel>
        {loading ? (
          <div className="cp-loading-state">
            <div className="cp-spinner" />
            <span>Loading your complaints...</span>
          </div>
        ) : filtered.length > 0 ? (
          <div className="cp-complaint-list">
            {filtered.map(item => (
              <div
                className="cp-complaint-row"
                key={item.id}
                onClick={() => openComplaintDetail(item.id)}
                style={{ cursor: "pointer" }}
              >
                <div className="cp-complaint-icon"><FileText size={18} /></div>
                <div className="cp-complaint-details">
                  <strong>{item.title}</strong>
                  <span>
                    #{String(item.id).slice(0, 8)} · {item.category} · {item.department_name || "General"} · {new Date(item.created_at).toLocaleDateString("en-IN")}
                  </span>
                </div>
                <span className={`cp-status ${String(item?.status || "Submitted").toLowerCase().replaceAll(" ", "-")}`}>
                  {item?.status || "Submitted"}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="cp-empty-state">
            <p>No complaints found for status "{filter}".</p>
          </div>
        )}
      </Panel>

      {/* COMPLAINT DETAIL DRAWER */}
      {selectedComplaint && (
        <div className="cp-drawer-backdrop" onClick={() => setSelectedComplaint(null)}>
          <aside className="cp-drawer" onClick={e => e.stopPropagation()}>
            <div className="cp-drawer-head">
              <div>
                <span className="cp-eyebrow">COMPLAINT DETAIL</span>
                <h2>#{String(selectedComplaint.id).slice(0, 8)}</h2>
              </div>
              <button className="cp-drawer-close" onClick={() => setSelectedComplaint(null)}>✕</button>
            </div>

            <div className="cp-detail-grid">
              <div className="cp-detail-item">
                <span>Status</span>
                <strong className={`cp-status ${String(selectedComplaint?.status || "Submitted").toLowerCase().replaceAll(" ", "-")}`}>
                  {selectedComplaint?.status || "Submitted"}
                </strong>
              </div>
              <div className="cp-detail-item">
                <span>Priority</span>
                <strong>{selectedComplaint.priority}</strong>
              </div>
              <div className="cp-detail-item">
                <span>Department</span>
                <strong>{selectedComplaint.department_name || "Triage Pending"}</strong>
              </div>
              <div className="cp-detail-item">
                <span>Category</span>
                <strong>{selectedComplaint.category}</strong>
              </div>
              <div className="cp-detail-item">
                <span>Coordinates</span>
                <strong>{selectedComplaint.latitude}, {selectedComplaint.longitude}</strong>
              </div>
              <div className="cp-detail-item">
                <span>Reported On</span>
                <strong>{new Date(selectedComplaint.created_at).toLocaleDateString("en-IN")}</strong>
              </div>
            </div>

            <div>
              <span className="cp-eyebrow">DESCRIPTION</span>
              <p style={{ fontSize: "12px", lineHeight: "1.6", marginTop: "6px" }}>
                {selectedComplaint.description}
              </p>
            </div>

            {selectedComplaint.ai_summary && (
              <div style={{ padding: "12px", borderRadius: "10px", background: "rgba(0,188,180,0.08)", border: "1px solid rgba(0,188,180,0.2)" }}>
                <span className="cp-eyebrow" style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                  <Sparkles size={12} /> AI ASSESSMENT SUMMARY
                </span>
                <p style={{ fontSize: "11px", color: "var(--text)", margin: "6px 0 0" }}>
                  {selectedComplaint.ai_summary}
                </p>
              </div>
            )}

            {selectedComplaint.image_signed_url && (
              <div>
                <span className="cp-eyebrow">ATTACHED EVIDENCE</span>
                <img
                  src={selectedComplaint.image_signed_url}
                  alt="Complaint Evidence"
                  style={{ width: "100%", maxHeight: "220px", objectFit: "cover", borderRadius: "10px", marginTop: "8px" }}
                />
              </div>
            )}

            {/* TIMELINE OF STATUS UPDATES */}
            <div>
              <span className="cp-eyebrow">STATUS UPDATE HISTORY</span>
              {selectedComplaint.updates && selectedComplaint.updates.length > 0 ? (
                <div className="cp-timeline">
                  {selectedComplaint.updates.map((upd, idx) => (
                    <div className="cp-timeline-item" key={upd.id || idx}>
                      <span className="cp-timeline-dot" />
                      <div className="cp-timeline-header">
                        <strong>{upd.status}</strong>
                        <small>{new Date(upd.created_at).toLocaleDateString("en-IN")} · {upd.actor_role || "Official"}</small>
                      </div>
                      <p>{upd.remarks || "Status transitioned."}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="cp-muted" style={{ fontSize: "11px", marginTop: "8px" }}>
                  No official remarks logged yet. Your report is queued for municipal triage.
                </p>
              )}
            </div>
          </aside>
        </div>
      )}
    </>
  );
}

// ============================================================================
// 5. PROJECTS AND PUBLIC FEEDBACK
// ============================================================================
export function Projects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Feedback form state
  const [selectedProject, setSelectedProject] = useState(null);
  const [feedbackCategory, setFeedbackCategory] = useState("Construction-related inconvenience");
  const [feedbackMessage, setFeedbackMessage] = useState("");
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackStatus, setFeedbackStatus] = useState(null);

  async function loadProjects() {
    try {
      setLoading(true);
      setError(null);
      const data = await citizenService.getProjects();
      setProjects(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn("Failed to load projects:", err.message);
      setError(err.userMessage || "Failed to load municipal projects.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProjects();
  }, []);

  async function handleFeedbackSubmit(e) {
    e.preventDefault();
    if (!selectedProject || feedbackMessage.trim().length < 3) {
      setFeedbackStatus({ error: "Please enter feedback with at least 3 characters." });
      return;
    }

    setFeedbackSubmitting(true);
    setFeedbackStatus(null);

    try {
      await citizenService.submitFeedback({
        project_id: selectedProject.id,
        category: feedbackCategory,
        message: feedbackMessage.trim(),
      });
      setFeedbackStatus({ success: "Thank you! Your feedback has been registered and forwarded to the project team." });
      setFeedbackMessage("");
    } catch (err) {
      setFeedbackStatus({ error: err.userMessage || "Failed to submit feedback. Please try again." });
    } finally {
      setFeedbackSubmitting(false);
    }
  }

  return (
    <>
      <PageHeading
        eyebrow="TRANSPARENT GOVERNANCE"
        title="Goa in progress."
        description="Explore civic development initiatives and follow public works happening across your communities."
        action={
          <button onClick={loadProjects} className="cp-text-button" disabled={loading}>
            <RefreshCw size={13} className={loading ? "cp-spin" : ""} /> Refresh
          </button>
        }
      />

      {error && (
        <div className="cp-error-banner">
          <AlertTriangle size={18} />
          <span>{error}</span>
          <button onClick={loadProjects}>Retry</button>
        </div>
      )}

      {loading ? (
        <div className="cp-loading-state">
          <div className="cp-spinner" />
          <span>Loading municipal infrastructure projects...</span>
        </div>
      ) : projects.length > 0 ? (
        <div className="cp-project-grid">
          {projects.map((p) => {
            const isCompleted = p.status === "Completed";
            const progress = isCompleted ? 100 : p.status === "Ongoing" ? 65 : 20;

            return (
              <Panel className="cp-project" key={p.id}>
                <span className="cp-eyebrow">{p.department_name ? p.department_name.toUpperCase() : "MUNICIPAL WORK"}</span>
                <div className="cp-project-icon"><Building2 /></div>
                <h2>{p.title}</h2>
                <p style={{ marginBottom: "12px" }}>{p.description}</p>
                <p><MapPin size={14} /> Coordinates: {p.latitude.toFixed(4)}, {p.longitude.toFixed(4)}</p>
                <p style={{ fontSize: "10px", color: "var(--muted)", margin: "4px 0 10px" }}>
                  Timeline: {p.start_date} to {p.expected_end_date}
                </p>
                <div className="cp-progress"><span style={{ width: `${progress}%` }} /></div>
                <div className="cp-project-foot">
                  <strong>{progress}% complete</strong>
                  <span className={`cp-status ${isCompleted ? "resolved" : "in-progress"}`}>{p.status}</span>
                </div>

                <div style={{ marginTop: "16px", paddingTop: "12px", borderTop: "1px solid var(--border)" }}>
                  <button
                    className="cp-secondary-button"
                    style={{ width: "100%", fontSize: "11px", minHeight: "38px" }}
                    onClick={() => {
                      setSelectedProject(p);
                      setFeedbackStatus(null);
                    }}
                  >
                    <MessageSquare size={14} /> Share Citizen Feedback
                  </button>
                </div>
              </Panel>
            );
          })}
        </div>
      ) : (
        <Panel>
          <div className="cp-empty-state">
            <p>No published infrastructure projects currently listed.</p>
          </div>
        </Panel>
      )}

      {/* FEEDBACK MODAL / DRAWER */}
      {selectedProject && (
        <div className="cp-drawer-backdrop" onClick={() => setSelectedProject(null)}>
          <aside className="cp-drawer" onClick={e => e.stopPropagation()}>
            <div className="cp-drawer-head">
              <div>
                <span className="cp-eyebrow">CITIZEN FEEDBACK</span>
                <h2>{selectedProject.title}</h2>
              </div>
              <button className="cp-drawer-close" onClick={() => setSelectedProject(null)}>✕</button>
            </div>

            <p style={{ fontSize: "12px", color: "var(--muted)" }}>
              Share your thoughts, suggestions, or concerns regarding this municipal infrastructure initiative.
            </p>

            {feedbackStatus?.error && (
              <div className="cp-error-banner">
                <AlertTriangle size={16} />
                <span>{feedbackStatus.error}</span>
              </div>
            )}
            {feedbackStatus?.success && (
              <p className="cp-success" style={{ padding: "10px", background: "rgba(0,188,180,0.1)", borderRadius: "8px" }}>
                {feedbackStatus.success}
              </p>
            )}

            <form className="cp-form" onSubmit={handleFeedbackSubmit}>
              <label>
                Feedback category
                <select
                  value={feedbackCategory}
                  onChange={e => setFeedbackCategory(e.target.value)}
                  disabled={feedbackSubmitting}
                >
                  <option value="Construction-related inconvenience">Construction Inconvenience</option>
                  <option value="Road closures or diversions">Road Closures &amp; Diversions</option>
                  <option value="Noise or dust">Noise &amp; Dust Pollution</option>
                  <option value="Damaged nearby infrastructure">Damaged Nearby Infrastructure</option>
                  <option value="Accessibility concerns">Accessibility Concerns</option>
                  <option value="Other project-related problems">Other / General Feedback</option>
                </select>
              </label>

              <label>
                Your comments
                <textarea
                  rows="4"
                  value={feedbackMessage}
                  onChange={e => setFeedbackMessage(e.target.value)}
                  placeholder="Share constructive feedback on this project..."
                  required
                  minLength={3}
                  maxLength={2000}
                  disabled={feedbackSubmitting}
                />
              </label>

              <button className="cp-primary-button" type="submit" disabled={feedbackSubmitting}>
                {feedbackSubmitting ? "Submitting..." : "Submit feedback"} <ArrowUpRight size={16} />
              </button>
            </form>
          </aside>
        </div>
      )}
    </>
  );
}

// ============================================================================
// 6. CITY MAP
// ============================================================================
export function CityMap() {
  return (
    <>
      <PageHeading
        eyebrow="EXPLORE YOUR CITY"
        title="Goa, on the map."
        description="Geospatial visualization of civic complaints, published public works, and traffic hotspots across Goa."
      />
      <Panel className="cp-map-panel" style={{ padding: "15px" }}>
        <CivicMap2D />
      </Panel>
    </>
  );
}

// ============================================================================
// 7. SAFETY REPORTS & UNVERIFIED LOCATIONS
// ============================================================================
export function Safety() {
  const [safetyReports, setSafetyReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Safety report submission form
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [safetyCategory, setSafetyCategory] = useState("Poor Lighting");
  const [location, setLocation] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);

  const allowedSafetyCategories = [
    "Poor Lighting",
    "Deserted Bus Stop",
    "Dark Alley",
    "Unsafe Crossing",
    "Non-functional streetlights",
    "Poorly lit pedestrian routes",
    "Damaged or obstructed footpaths",
    "Location feels unsafe",
  ];

  async function loadSafetyReports() {
    try {
      setLoading(true);
      setError(null);
      const data = await citizenService.getMySafetyReports();
      setSafetyReports(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn("Failed to load safety reports:", err.message);
      setError(err.userMessage || "Failed to load safety reports.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSafetyReports();
  }, []);

  async function handleSafetySubmit(e) {
    e.preventDefault();
    if (description.trim().length < 5) {
      setStatusMessage({ error: "Please describe the hazard with at least 5 characters." });
      return;
    }

    setIsSubmitting(true);
    setStatusMessage(null);

    try {
      const coords = resolveGoaCoordinates(location);
      const reportTitle = title.trim() || `${safetyCategory} near ${location || "Goa"}`;

      await citizenService.createSafetyReport({
        title: reportTitle.length >= 3 ? reportTitle : undefined,
        description: description.trim(),
        safety_category: safetyCategory,
        latitude: coords.lat,
        longitude: coords.lon,
      });

      setStatusMessage({ success: "Safety report submitted. It has been securely logged for inspection by municipal safety officials." });
      setTitle("");
      setDescription("");
      setLocation("");
      loadSafetyReports();
    } catch (err) {
      setStatusMessage({ error: err.userMessage || "Failed to submit safety report. Please verify details." });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <>
      <PageHeading
        eyebrow="COMMUNITY INFRASTRUCTURE SAFETY"
        title="Stay safe. Stay aware."
        description="Confidential safety hazard reporting to help municipal authorities eliminate poorly lit, isolated, or hazardous public spaces."
        action={
          <button onClick={loadSafetyReports} className="cp-text-button" disabled={loading}>
            <RefreshCw size={13} className={loading ? "cp-spin" : ""} /> Refresh
          </button>
        }
      />

      <Panel className="cp-alert-banner">
        <ShieldAlert size={28} />
        <div>
          <strong>Confidential Infrastructure Safety Channel</strong>
          <span>Safety concerns submitted here are strictly aggregated for public privacy and routed to designated Safety Officers for inspection.</span>
        </div>
      </Panel>

      {error && (
        <div className="cp-error-banner">
          <AlertTriangle size={18} />
          <span>{error}</span>
          <button onClick={loadSafetyReports}>Retry</button>
        </div>
      )}

      <div className="cp-dashboard-grid" style={{ marginBottom: "20px" }}>
        {/* SUBMIT SAFETY REPORT */}
        <Panel>
          <span className="cp-eyebrow">REPORT HAZARD</span>
          <h2>Report an unsafe infrastructure location</h2>
          <p className="cp-muted">Highlight poorly lit stretches, broken crossings, or isolated transit points.</p>

          {statusMessage?.error && (
            <div className="cp-error-banner">
              <AlertTriangle size={16} />
              <span>{statusMessage.error}</span>
            </div>
          )}
          {statusMessage?.success && (
            <p className="cp-success" style={{ padding: "10px", background: "rgba(0,188,180,0.1)", borderRadius: "8px" }}>
              {statusMessage.success}
            </p>
          )}

          <form className="cp-form" onSubmit={handleSafetySubmit} style={{ marginTop: "15px" }}>
            <label>
              Safety concern category
              <select
                value={safetyCategory}
                onChange={e => setSafetyCategory(e.target.value)}
                disabled={isSubmitting}
              >
                {allowedSafetyCategories.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </label>

            <label>
              Location / Area
              <input
                value={location}
                onChange={e => setLocation(e.target.value)}
                placeholder="e.g. Backroad between Panaji &amp; Miramar"
                required
                disabled={isSubmitting}
              />
            </label>

            <label>
              Hazard description
              <textarea
                rows="4"
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="Describe the hazard (e.g. 4 consecutive streetlights broken, complete dark zone at night)..."
                required
                minLength={5}
                disabled={isSubmitting}
              />
            </label>

            <button className="cp-primary-button" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Logging safety report..." : "Submit safety report"} <ArrowUpRight size={16} />
            </button>
          </form>
        </Panel>

        {/* EMERGENCY CONTACTS */}
        <Panel>
          <span className="cp-eyebrow">EMERGENCY SERVICES</span>
          <h2>Immediate assistance</h2>
          <div className="cp-contact"><strong>112</strong><span>All-in-one Goa Emergency Response</span></div>
          <div className="cp-contact"><strong>1091</strong><span>Women's Safety Helpline</span></div>
          <div className="cp-contact"><strong>101</strong><span>Fire and rescue</span></div>
          <div className="cp-contact"><strong>108</strong><span>Emergency Medical Ambulance</span></div>
        </Panel>
      </div>

      {/* MY SAFETY REPORTS HISTORY */}
      <Panel>
        <div className="cp-panel-heading">
          <div>
            <span className="cp-eyebrow">YOUR SUBMISSIONS</span>
            <h2>My safety reports history</h2>
          </div>
        </div>

        {loading ? (
          <div className="cp-loading-state">
            <div className="cp-spinner" />
            <span>Loading your safety records...</span>
          </div>
        ) : safetyReports.length > 0 ? (
          <div className="cp-complaint-list">
            {safetyReports.map(item => (
              <div className="cp-complaint-row" key={item.id}>
                <div className="cp-complaint-icon"><ShieldCheck size={18} /></div>
                <div className="cp-complaint-details">
                  <strong>{item.title || item.safety_category}</strong>
                  <span>#{String(item.id).slice(0, 8)} · {item.safety_category} · {new Date(item.created_at).toLocaleDateString("en-IN")}</span>
                </div>
                <span className={`cp-status ${String(item?.status || "Submitted").toLowerCase().replaceAll(" ", "-")}`}>
                  {item?.status || "Submitted"}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="cp-empty-state">
            <p>You have not logged any infrastructure safety reports yet.</p>
          </div>
        )}
      </Panel>
    </>
  );
}

// ============================================================================
// 8. CITIZEN SETTINGS & AUTHENTICATED PROFILE
// ============================================================================
export function SettingsPage() {
  const { theme, setTheme } = useOutletContext();
  const { user } = useAuth();

  return (
    <>
      <PageHeading
        eyebrow="YOUR ACCOUNT"
        title="Settings."
        description="Manage your profile, preferences and Smart Land experience."
      />
      <div className="cp-settings-grid">
        <Panel>
          <span className="cp-eyebrow">APPEARANCE</span>
          <h2>Display preference</h2>
          <p className="cp-muted">Choose how SMART LAND looks across the entire portal.</p>
          <div className="cp-theme-options">
            <button className={theme === "light" ? "chosen" : ""} onClick={() => setTheme("light")}>
              <Sun />
              <strong>Light mode</strong>
              <span>Bright and clear</span>
            </button>
            <button className={theme === "dark" ? "chosen" : ""} onClick={() => setTheme("dark")}>
              <Moon />
              <strong>Dark mode</strong>
              <span>Easy on the eyes</span>
            </button>
          </div>
          <p className="cp-success" style={{ marginTop: "14px" }}>Your display preference is saved automatically.</p>
        </Panel>

        <Panel>
          <span className="cp-eyebrow">CITIZEN PROFILE</span>
          <h2>Account details</h2>
          <div className="cp-profile-record">
            <UserRound />
            <div>
              <span>Full name</span>
              <strong>{user?.full_name || "Citizen Account"}</strong>
            </div>
          </div>
          <div className="cp-profile-record">
            <Mail />
            <div>
              <span>Account identifier</span>
              <strong>{user?.id || "Session active"}</strong>
            </div>
          </div>
          <div className="cp-profile-record">
            <Phone />
            <div>
              <span>Mobile number</span>
              <strong>{user?.phone || "Not provided on registration"}</strong>
            </div>
          </div>
          <div className="cp-profile-record">
            <ShieldCheck />
            <div>
              <span>Verified role</span>
              <strong style={{ textTransform: "uppercase" }}>{user?.role || "Citizen"}</strong>
            </div>
          </div>
          <small className="cp-muted" style={{ display: "block", marginTop: "14px" }}>
            Identity and profile updates are managed through verified municipal channels. Contact municipal administration for record amendments.
          </small>
        </Panel>
      </div>
    </>
  );
}
