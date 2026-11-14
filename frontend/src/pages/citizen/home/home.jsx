
import { useState } from "react";
import {
  ArrowUpRight,
  ArrowRight,
  Search,
  UserRound,
  Menu,
  X,
  MapPin,
  ShieldAlert,
  Building2,
  MessageSquareText,
} from "lucide-react";

import "../home.css";

const updates = [
  {
    category: "INFRASTRUCTURE",
    title: "Road improvement works",
    location: "Margao · Goa",
    status: "Ongoing",
    color: "teal",
  },
  {
    category: "PUBLIC SAFETY",
    title: "Streetlight maintenance drive",
    location: "Vasco · Goa",
    status: "In progress",
    color: "lime",
  },
  {
    category: "CITY DEVELOPMENT",
    title: "Community park development",
    location: "Panaji · Goa",
    status: "Upcoming",
    color: "amber",
  },
];

const services = [
  {
    icon: MessageSquareText,
    title: "Report an Issue",
    description: "Raise civic complaints with a photo, voice or text.",
    color: "coral",
  },
  {
    icon: MapPin,
    title: "Explore City Map",
    description: "Discover public infrastructure and city updates.",
    color: "teal",
  },
  {
    icon: Building2,
    title: "City Projects",
    description: "Stay informed about development around you.",
    color: "lime",
  },
  {
    icon: ShieldAlert,
    title: "Public Safety",
    description: "Report unsafe locations and infrastructure.",
    color: "amber",
  },
];

export default function Home() {
  const [menuOpen, setMenuOpen] = useState(false);

  const scrollToServices = () => {
    document.getElementById("services")?.scrollIntoView({
      behavior: "smooth",
    });
    setMenuOpen(false);
  };

  return (
    <main className="city-home">
      <section
        className="home-hero"
        id="home"
        style={{
          "--hero-image": "linear-gradient(120deg, #173b37, #536b50)",
        }}
      >
        <div className="hero-overlay" />

        <header className="home-navbar">
          <a href="#home" className="brand">
            <span className="brand-symbol">S</span>
            <span>
              <strong>SMART LAND</strong>
              <small>SMART LAND PLATFORM</small>
            </span>
          </a>

          <nav className={`nav-links ${menuOpen ? "nav-open" : ""}`}>
            <a href="#home" onClick={() => setMenuOpen(false)}>Home</a>
            <a href="#services" onClick={() => setMenuOpen(false)}>Services</a>
            <a href="#updates" onClick={() => setMenuOpen(false)}>City Updates</a>
            <a href="#projects" onClick={() => setMenuOpen(false)}>Projects</a>
          </nav>

          <div className="nav-actions">
            <button className="nav-icon" aria-label="Search">
              <Search size={19} />
            </button>
            <a href="#citizen-access" className="citizen-button">
              <UserRound size={17} />
              <span>Citizen Access</span>
              <ArrowUpRight size={15} />
            </a>
          </div>

          <button
            className="mobile-menu"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle menu"
          >
            {menuOpen ? <X /> : <Menu />}
          </button>
        </header>

        <div className="hero-content">
          <div className="hero-copy">
            <div className="eyebrow">
              <span className="eyebrow-dot" />
              NOW IN GOA
            </div>

            <h1>
              A better city
              <br />
              <span>starts with you.</span>
            </h1>

            <p className="hero-description">
              One connected platform to report civic issues, discover city
              developments and make your voice heard.
            </p>

            <div className="hero-buttons">
              <button className="primary-cta" onClick={scrollToServices}>
                Explore Smart Land <ArrowUpRight size={18} />
              </button>
              <a href="#services" className="secondary-cta">
                Discover services <ArrowRight size={17} />
              </a>
            </div>

            <div className="hero-location">
              <MapPin size={15} />
              <span>GOA, INDIA</span>
              <span className="location-line" />
              <span>BUILT FOR CITIZENS</span>
            </div>
          </div>

          <aside className="updates-glass" id="updates">
            <div className="updates-heading">
              <div>
                <span className="panel-eyebrow">HAPPENING AROUND YOU</span>
                <h2>City Pulse<span>.</span></h2>
              </div>
              <span className="live-indicator"><i /> LIVE</span>
            </div>

            <div className="updates-list">
              {updates.map((item, index) => (
                <article className="update-card" key={item.title}>
                  <div className={`update-number ${item.color}`}>
                    0{index + 1}
                  </div>
                  <div className="update-info">
                    <span className="update-category">{item.category}</span>
                    <h3>{item.title}</h3>
                    <span className="update-location">
                      <MapPin size={12} /> {item.location}
                    </span>
                  </div>
                  <span className={`update-status ${item.color}`}>
                    {item.status}
                  </span>
                </article>
              ))}
            </div>

            <a href="#projects" className="all-updates">
              Explore city updates <ArrowUpRight size={15} />
            </a>
          </aside>
        </div>

        <div className="hero-bottom">
          <div className="hero-social">
            <span>CONNECTED</span>
            <span className="social-dot" />
            <span>TRANSPARENT</span>
            <span className="social-dot" />
            <span>SMARTER</span>
          </div>

          <a href="#services" className="scroll-indicator">
            SCROLL TO EXPLORE <span>↓</span>
          </a>
        </div>
      </section>

      <section className="services-section" id="services">
        <div className="section-heading">
          <div>
            <span className="section-eyebrow">
              YOUR CITY, AT YOUR FINGERTIPS
            </span>
            <h2>Everything starts <span>here.</span></h2>
          </div>

          <p>
            From reporting an issue to tracking city development, access the
            services that bring citizens and their city closer.
          </p>
        </div>

        <div className="services-grid">
          {services.map((service, index) => {
            const Icon = service.icon;

            return (
              <a
                href="#citizen-access"
                className="service-card"
                key={service.title}
              >
                <div className={`service-icon ${service.color}`}>
                  <Icon size={23} />
                </div>

                <span className="service-index">0{index + 1}</span>
                <h3>{service.title}</h3>
                <p>{service.description}</p>

                <span className="service-arrow">
                  <ArrowUpRight size={19} />
                </span>
              </a>
            );
          })}
        </div>
      </section>

      <section className="city-cta" id="citizen-access">
        <div>
          <span className="section-eyebrow">BE PART OF THE CHANGE</span>
          <h2>Your city. Your voice. <span>Your impact.</span></h2>
          <p>Connect with your city and help shape a better tomorrow.</p>
        </div>

        <a href="#home" className="cta-link">
          Back to top <ArrowUpRight size={18} />
        </a>
      </section>

      <footer className="home-footer">
        <a href="#home" className="footer-brand">
          SMART LAND<span>.</span>
        </a>
        <p>© 2026 SMART LAND · AI CITY MANAGEMENT PLATFORM</p>
        <span>MADE FOR GOA</span>
      </footer>
    </main>
  );
}
