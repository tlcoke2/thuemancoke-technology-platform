import { useMemo, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  CircleCheckBig,
  Globe2,
  Mail,
  MapPin,
  Menu,
  ServerCog,
  Sparkles,
  X,
} from "lucide-react";
import { sectors, services, solutionMap } from "./data";

const API_URL = (import.meta.env.VITE_API_URL || "https://api.thuemancokelimited.com").replace(/\/$/, "");

function Navbar() {
  const [open, setOpen] = useState(false);
  const links = [
    ["Services", "#services"],
    ["Expertise", "#expertise"],
    ["About", "#about"],
    ["Approach", "#approach"],
    ["Contact", "#contact"],
  ];

  return (
    <header className="nav-shell">
      <nav className="nav container" aria-label="Main navigation">
        <a className="brand" href="#top" aria-label="Thueman Coke Limited home">
          <img src="./images/thueman-coke-logo.png" alt="" />
          <span><strong>Thueman Coke</strong><small>Limited</small></span>
        </a>

        <button className="mobile-menu" onClick={() => setOpen(!open)} aria-label="Open menu">
          {open ? <X /> : <Menu />}
        </button>

        <div className={`nav-links ${open ? "open" : ""}`}>
          {links.map(([label, href]) => (
            <a key={href} href={href} onClick={() => setOpen(false)}>{label}</a>
          ))}
          <a className="btn btn-small" href="#contact" onClick={() => setOpen(false)}>Start a project</a>
        </div>
      </nav>
    </header>
  );
}

function Hero() {
  return (
    <section className="hero" id="top">
      <div className="hero-grid container">
        <div className="hero-copy">
          <div className="eyebrow"><Sparkles size={16} /> Technology engineered around your business</div>
          <h1>Build smarter.<span> Operate stronger.</span><br />Scale with confidence.</h1>
          <p className="hero-lead">
            AI, digital platforms, data, infrastructure and healthcare technology delivered with more than
            35 years of international IT experience across the UK, Europe, USA and Caribbean.
          </p>
          <div className="hero-actions">
            <a className="btn" href="#contact">Discuss your project <ArrowRight size={18} /></a>
            <a className="btn btn-ghost" href="#services">Explore solutions</a>
          </div>
          <div className="proof-row">
            <div><strong>35+</strong><span>Years global IT experience</span></div>
            <div><strong>4</strong><span>International regions</span></div>
            <div><strong>AI-first</strong><span>Modern technology delivery</span></div>
          </div>
        </div>

        <div className="hero-visual" aria-label="Technology architecture illustration">
          <div className="grid-orb orb-1"></div>
          <div className="grid-orb orb-2"></div>
          <div className="tech-card">
            <div className="tech-card-heading"><ServerCog size={22} /><span>Enterprise Technology Fabric</span></div>
            <div className="architecture">
              <span>AI</span><i></i><span>Applications</span><i></i><span>Data</span>
              <span>Security</span><i></i><span>Cloud</span><i></i><span>Networks</span>
            </div>
            <div className="live-line"><span></span> Designed for secure, scalable operations</div>
          </div>
          <div className="float-card float-one"><span>AI + Automation</span><strong>Business intelligence in action</strong></div>
          <div className="float-card float-two"><span>Global delivery</span><strong>UK · Europe · USA · Caribbean</strong></div>
        </div>
      </div>
    </section>
  );
}

function Credibility() {
  return (
    <section className="credibility">
      <div className="container">
        <p>Experience spanning complex technology environments including</p>
        <div className="credibility-grid">
          <span>NHS</span><span>AstraZeneca</span><span>Leica Biosystems</span>
          <span>New York University in London</span><span>Hotels</span><span>Charities & Schools</span>
        </div>
        <small>Organisation names describe prior professional experience and do not imply current endorsement or partnership.</small>
      </div>
    </section>
  );
}

function Services() {
  return (
    <section className="section" id="services">
      <div className="container">
        <div className="section-heading">
          <div><span className="kicker">Technology solutions</span><h2>One technology partner. End-to-end capability.</h2></div>
          <p>We bridge strategy, engineering, infrastructure and operations so technology becomes a business advantage rather than a collection of disconnected systems.</p>
        </div>
        <div className="service-grid">
          {services.map(({ icon: Icon, title, text, tags }) => (
            <article className="service-card" key={title}>
              <div className="service-icon"><Icon /></div>
              <h3>{title}</h3>
              <p>{text}</p>
              <div className="tags">{tags.map((tag) => <span key={tag}>{tag}</span>)}</div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function Expertise() {
  const [challenge, setChallenge] = useState("Modernise operations");
  const recommendations = useMemo(() => solutionMap[challenge], [challenge]);

  return (
    <section className="section section-dark" id="expertise">
      <div className="container expertise-grid">
        <div>
          <span className="kicker">Solution finder</span>
          <h2>Start with the business problem, not the product.</h2>
          <p className="large-copy">Select the outcome you need and see the technology capabilities we would normally combine.</p>
          <div className="challenge-buttons">
            {Object.keys(solutionMap).map((item) => (
              <button key={item} className={challenge === item ? "active" : ""} onClick={() => setChallenge(item)}>
                {item}<ChevronRight size={17} />
              </button>
            ))}
          </div>
        </div>

        <div className="recommendation-card">
          <span className="mini-label">Recommended capability mix</span>
          <h3>{challenge}</h3>
          <div className="recommendations">
            {recommendations.map((item) => (
              <div key={item}><CircleCheckBig size={20} /><span>{item}</span></div>
            ))}
          </div>
          <p>Every engagement is scoped around risk, budget, existing systems, internal capability and measurable outcomes.</p>
          <a href="#contact">Request a technology assessment <ArrowRight size={18} /></a>
        </div>
      </div>
    </section>
  );
}

function About() {
  return (
    <section className="section" id="about">
      <div className="container about-grid">
        <div className="about-photo">
          <div className="photo-overlay">
            <img src="./images/thueman-coke-logo.png" alt="Thueman Coke Limited technology identity" />
          </div>
        </div>
        <div className="about-copy">
          <span className="kicker">Founder-led expertise</span>
          <h2>More than technology implementation.</h2>
          <p className="large-copy">
            Thueman Coke Limited was established in 2023, backed by more than 35 years of technology,
            management and international business experience.
          </p>
          <p>
            The founder’s experience spans platform and data design, websites, networks, server environments,
            data centres, healthcare technology, operational leadership and the application of AI to modern
            business systems.
          </p>
          <p>
            That background includes work associated with complex organisations and sectors across the UK,
            Europe, USA and Caribbean, alongside leadership and technology-partner roles supporting private
            businesses, healthcare services and charitable programmes.
          </p>
          <div className="bullet-grid">
            <span><CheckCircle2 /> Enterprise architecture</span>
            <span><CheckCircle2 /> AI-enabled applications</span>
            <span><CheckCircle2 /> Healthcare technology</span>
            <span><CheckCircle2 /> Business leadership</span>
            <span><CheckCircle2 /> Infrastructure engineering</span>
            <span><CheckCircle2 /> International delivery</span>
          </div>
        </div>
      </div>
    </section>
  );
}

function Sectors() {
  return (
    <section className="section sectors-section">
      <div className="container">
        <span className="kicker">Sector reach</span>
        <h2>Technology that adapts to the organisation.</h2>
        <div className="sector-grid">
          {sectors.map((sector, i) => (
            <div className="sector" key={sector}>
              <span>{String(i + 1).padStart(2, "0")}</span>
              <strong>{sector}</strong>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Approach() {
  const steps = [
    ["01", "Discover", "Understand objectives, users, operations, technology estate, constraints and risk."],
    ["02", "Architect", "Design the right solution, data model, security controls and delivery roadmap."],
    ["03", "Build & integrate", "Develop, configure, migrate and connect systems with clear testing gates."],
    ["04", "Launch & support", "Deploy safely, document the platform, train users and improve continuously."],
  ];

  return (
    <section className="section approach" id="approach">
      <div className="container">
        <div className="section-heading">
          <div><span className="kicker">Delivery approach</span><h2>From idea to dependable operation.</h2></div>
          <p>Our delivery model keeps business value, security, maintainability and adoption visible throughout the project.</p>
        </div>
        <div className="steps">
          {steps.map(([n, title, text]) => (
            <article key={n}><span>{n}</span><h3>{title}</h3><p>{text}</p></article>
          ))}
        </div>
      </div>
    </section>
  );
}

function Contact() {
  const [state, setState] = useState({ status: "idle", message: "" });

  async function submit(e) {
    e.preventDefault();
    setState({ status: "loading", message: "Sending…" });
    const payload = Object.fromEntries(new FormData(e.currentTarget).entries());

    try {
      const response = await fetch(`${API_URL}/api/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || "Unable to submit your enquiry.");
      e.currentTarget.reset();
      setState({ status: "success", message: "Thank you. Your enquiry has been received." });
    } catch (error) {
      setState({ status: "error", message: error.message || "Something went wrong. Please try again." });
    }
  }

  return (
    <section className="section contact-section" id="contact">
      <div className="container contact-grid">
        <div>
          <span className="kicker">Start a conversation</span>
          <h2>What should technology do better for your organisation?</h2>
          <p className="large-copy">Tell us what you are trying to achieve. We will use the first discussion to identify the most practical next step.</p>
          <div className="contact-points">
            <span><Globe2 /> UK · Europe · USA · Caribbean</span>
            <span><Mail /> Business and project enquiries</span>
            <span><MapPin /> Remote and on-site delivery by arrangement</span>
          </div>
        </div>

        <form className="contact-form" onSubmit={submit}>
          <div className="field-row">
            <label>Full name<input required name="name" autoComplete="name" /></label>
            <label>Business email<input required type="email" name="email" autoComplete="email" /></label>
          </div>
          <label>Organisation<input name="organisation" autoComplete="organization" /></label>
          <label>
            Area of interest
            <select name="service" defaultValue="">
              <option value="" disabled>Select an area</option>
              {services.map((s) => <option key={s.title}>{s.title}</option>)}
              <option>Technology strategy / other</option>
            </select>
          </label>
          <label>What would you like to achieve?<textarea required name="message" rows="5" /></label>
          <label className="consent">
            <input required type="checkbox" name="consent" value="true" />
            <span>I consent to being contacted about this enquiry.</span>
          </label>
          <button className="btn" disabled={state.status === "loading"}>
            {state.status === "loading" ? "Sending…" : "Send enquiry"} <ArrowRight size={18} />
          </button>
          {state.message && <p className={`form-status ${state.status}`}>{state.message}</p>}
        </form>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer>
      <div className="container footer-grid">
        <div className="footer-brand">
          <img src="./images/thueman-coke-logo.png" alt="" />
          <div><strong>Thueman Coke Limited</strong><span>Technology solutions for a smarter tomorrow.</span></div>
        </div>
        <div>
          <strong>Capabilities</strong>
          <a href="#services">AI & applications</a>
          <a href="#services">Data & cloud</a>
          <a href="#services">Infrastructure & security</a>
          <a href="#services">Healthcare technology</a>
        </div>
        <div>
          <strong>Company</strong>
          <a href="#about">About</a>
          <a href="#approach">Approach</a>
          <a href="#contact">Contact</a>
        </div>
      </div>
      <div className="container footer-bottom">
        <span>© {new Date().getFullYear()} Thueman Coke Limited. All rights reserved.</span>
        <span>People · Technology · Innovation · Global Impact</span>
      </div>
    </footer>
  );
}

export default function App() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <Credibility />
        <Services />
        <Expertise />
        <About />
        <Sectors />
        <Approach />
        <Contact />
      </main>
      <Footer />
    </>
  );
}
