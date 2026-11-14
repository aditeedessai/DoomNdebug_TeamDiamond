import { useState, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  ArrowUpRight, ArrowRight, UserRound, Landmark,
  ShieldCheck, MapPin, Activity, Eye, EyeOff,
  Mail, Lock, Sun, Moon
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import "./Login.css";

function PortalCard({ type, flipped, onFlip, onEnter }) {
  const citizen = type === "citizen";

  return (
    <div
      className={`id-card ${citizen ? "citizen-id" : "official-id"} ${flipped ? "is-flipped" : ""}`}
      onClick={onFlip}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onFlip();
        }
      }}
      role="button"
      tabIndex={0}
      aria-label={`Flip ${citizen ? "Citizen" : "Official"} ID card`}
    >
      <div className="id-card-inner">
        <div className="id-card-face id-card-front">
          <div className="id-card-top">
            <span className="id-card-brand">
              <span className="id-mini-mark">S</span>
              SMART LAND
            </span>
            <span className="id-card-number">{citizen ? "01" : "02"} / GOA</span>
          </div>

          <div className="id-card-main">
            <div className="id-avatar">
              {citizen ? <UserRound size={32} /> : <Landmark size={32} />}
            </div>
            <span className="id-card-overline">
              {citizen ? "PUBLIC ACCESS" : "AUTHORIZED ACCESS"}
            </span>
            <h2>{citizen ? "CITIZEN" : "OFFICIAL"}<br /><span>IDENTITY</span></h2>
            <p>
              {citizen
                ? "Your voice. Your city. Your impact."
                : "Authority. Action. Accountability."}
            </p>
          </div>

          <div className="id-card-bottom">
            <span>{citizen ? "CITIZEN PORTAL" : "GOVERNMENT PORTAL"}</span>
            <span className="id-tap">TAP TO FLIP <ArrowUpRight size={16} /></span>
          </div>
          <div className="id-card-watermark">{citizen ? "C" : "G"}</div>
        </div>

        <div className="id-card-face id-card-back">
          <div className="id-back-top">
            <span>{citizen ? "CITIZEN ACCESS" : "OFFICIAL ACCESS"}</span>
            <ShieldCheck size={22} />
          </div>

          <div className="id-back-content">
            <span className="id-card-overline">WELCOME TO SMART LAND</span>
            <h3>{citizen ? "Your city, in your hands." : "Manage a smarter Goa."}</h3>
            <p>
              {citizen
                ? "Report civic issues, track complaints and participate in city development."
                : "Review complaints, coordinate civic services and monitor city progress."}
            </p>
          </div>

          <button
            className="id-enter-button"
            onClick={(e) => {
              e.stopPropagation();
              onEnter();
            }}
          >
            Enter {citizen ? "Citizen" : "Official"} Portal
            <ArrowUpRight size={18} />
          </button>
          <span className="id-flip-hint">TAP CARD TO FLIP BACK</span>
        </div>
      </div>
    </div>
  );
}

export default function Login() {
  const location = useLocation();
  const navigate = useNavigate();
  const { login, logout, user, isAuthenticated } = useAuth();

  const isCitizenLogin = location.pathname === "/citizen-login";
  const isOfficialLogin = location.pathname === "/official-login";
  const isLoginForm = isCitizenLogin || isOfficialLogin;

  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("smartland-theme") || "dark";
  });

  useEffect(() => {
    localStorage.setItem("smartland-theme", theme);
  }, [theme]);

  // If already authenticated and visiting login, redirect to active portal
  useEffect(() => {
    if (isAuthenticated && user) {
      if (user.role === "citizen") {
        navigate("/citizen/dashboard", { replace: true });
      } else if (user.role === "official" || user.role === "worker") {
        navigate("/official/dashboard", { replace: true });
      }
    }
  }, [isAuthenticated, user, navigate]);

  const [citizenFlipped, setCitizenFlipped] = useState(false);
  const [officialFlipped, setOfficialFlipped] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [isError, setIsError] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const portalName = isCitizenLogin ? "Citizen" : "Official";

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setMessage("Please enter both email address and password.");
      setIsError(true);
      return;
    }

    setIsSubmitting(true);
    setMessage("");
    setIsError(false);

    try {
      const data = await login(email.trim(), password);
      const userProfile = data.profile || user;

      if (!userProfile) {
        throw new Error("Unable to retrieve user profile after login.");
      }

      // Role discrimination: citizen portal requires citizen role
      if (isCitizenLogin && userProfile.role !== "citizen") {
        logout();
        setMessage("This account is registered as an Official / Worker. Please use the Official Portal.");
        setIsError(true);
        setIsSubmitting(false);
        return;
      }

      // Role discrimination: official portal requires official or worker role
      if (isOfficialLogin && userProfile.role === "citizen") {
        logout();
        setMessage("This account is registered as a Citizen. Please use the Citizen Portal.");
        setIsError(true);
        setIsSubmitting(false);
        return;
      }

      // Navigate to destination from state or default dashboard
      const destination = location.state?.from?.pathname || (userProfile.role === "citizen" ? "/citizen/dashboard" : "/official/dashboard");
      navigate(destination, { replace: true });
    } catch (err) {
      const errorMsg = err.userMessage || "Authentication failed. Please verify your email and password.";
      setMessage(errorMsg);
      setIsError(true);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoginForm) {
    return (
      <main className={`smart-login auth-screen ${theme}-theme`}>
        <div className="login-glow" />
        <header className="sl-header">
          <Link to="/" className="sl-logo">
            <span className="sl-logo-mark">S</span>
            <span>SMART LAND<span className="sl-period">.</span></span>
          </Link>
          <div className="sl-header-actions">
            <button className="theme-toggle" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
              {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
              {theme === "dark" ? "LIGHT MODE" : "DARK MODE"}
            </button>
            <Link to="/login" className="auth-back">
              <ArrowRight size={15} /> All portals
            </Link>
          </div>
        </header>

        <section className="auth-layout">
          <div className="auth-intro">
            <span className="sl-kicker"><i /> {portalName.toUpperCase()} ACCESS</span>
            <h1>
              {isCitizenLogin ? "Your city." : "Your responsibility."}
              <br />
              <span>{isCitizenLogin ? "Your voice." : "Your impact."}</span>
            </h1>
            <p>
              {isCitizenLogin
                ? "Sign in to report civic issues, follow your complaints and take part in building a better Goa."
                : "Sign in to manage civic complaints, coordinate services and support smarter city operations."}
            </p>
          </div>

          <div className="auth-card">
            <span className="auth-eyebrow">{portalName.toUpperCase()} PORTAL</span>
            <h2>Welcome back.</h2>
            <p>Enter your credentials to continue.</p>

            <form onSubmit={handleSubmit}>
              <label htmlFor="portal-email">Email address</label>
              <div className="auth-input">
                <Mail size={17} />
                <input
                  id="portal-email"
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isSubmitting}
                  required
                />
              </div>

              <label htmlFor="portal-password">Password</label>
              <div className="auth-input">
                <Lock size={17} />
                <input
                  id="portal-password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isSubmitting}
                  required
                />
                <button type="button" className="auth-eye" onClick={() => setShowPassword(!showPassword)}>
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>

              <button type="submit" className="auth-submit" disabled={isSubmitting}>
                {isSubmitting ? "Authenticating..." : `Sign in to ${portalName} Portal`} <ArrowUpRight size={18} />
              </button>
              {message && (
                <p className="auth-message" style={{ color: isError ? "#f87171" : "var(--sl-teal)" }}>
                  {message}
                </p>
              )}
            </form>

            {isCitizenLogin && (
              <p className="auth-register">
                New to Smart Land? <button type="button" onClick={() => navigate("/register")}>Create an account</button>
              </p>
            )}
            <div className="auth-security"><ShieldCheck size={16} /> Secure Smart Land access</div>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className={`smart-login ${theme}-theme`}>
      <div className="login-glow" />

      <header className="sl-header">
        <Link to="/" className="sl-logo">
          <span className="sl-logo-mark">S</span>
          <span>SMART LAND<span className="sl-period">.</span></span>
        </Link>

        <div className="sl-header-actions">
          <div className="sl-header-right">
            <span>GOA'S DIGITAL CITY PLATFORM</span>
            <span>INNOVATION<br />FOR EVERY CITIZEN</span>
          </div>
          <button
            className="theme-toggle"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
            {theme === "dark" ? "LIGHT MODE" : "DARK MODE"}
          </button>
        </div>
      </header>

      <section className="sl-hero">
        <div className="sl-heading">
          <span className="sl-kicker"><i /> NOW IN GOA</span>
          <h1>
            A smarter city.
            <br />
            <span className="sl-lime">A stronger</span>
            <br />
            <span className="sl-coral">community.</span>
          </h1>
          <p>Your connection to a better Goa starts here. Report, participate and help shape the future of your city.</p>
          <div className="sl-scroll">
            <span>CHOOSE YOUR PORTAL</span>
            <span className="sl-down-arrow">↓</span>
          </div>
        </div>

        <div className="sl-decoration">
          <div className="sl-orbit orbit-one" />
          <div className="sl-orbit orbit-two" />
          <div className="sl-decoration-label">GOA · INDIA</div>
        </div>
      </section>

      <section className="sl-floating-area">
        <div className="sl-floating-note">
          <Activity size={15} /> CONNECTED. TRANSPARENT. SMARTER.
        </div>

        <PortalCard type="citizen" flipped={citizenFlipped} onFlip={() => setCitizenFlipped(!citizenFlipped)} onEnter={() => navigate("/citizen-login")} />
        <PortalCard type="official" flipped={officialFlipped} onFlip={() => setOfficialFlipped(!officialFlipped)} onEnter={() => navigate("/official-login")} />

        <div className="sl-stat-card">
          <span className="sl-stat-label">ONE CONNECTED GOA</span>
          <div className="sl-stat-visual"><span /><span /><span /><span /><span /></div>
          <div className="sl-stat-footer"><span>PEOPLE</span><span>PROGRESS</span><span>IMPACT</span></div>
        </div>

        <div className="sl-security-card">
          <ShieldCheck size={22} />
          <div><strong>Secure access</strong><span>One platform. Separate portals.</span></div>
        </div>
      </section>

      <footer className="sl-footer">
        <span>© 2026 SMART LAND</span>
        <span>MADE FOR GOA <MapPin size={12} /></span>
        <Link to="/" className="sl-home-link">BACK TO HOME <ArrowRight size={14} /></Link>
      </footer>
    </main>
  );
}
