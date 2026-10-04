import {
  BrainCircuit,
  Blocks,
  Database,
  CloudCog,
  Network,
  ShieldCheck,
  HeartPulse,
  Globe2,
} from "lucide-react";

export const services = [
  {
    icon: BrainCircuit,
    title: "AI & Intelligent Automation",
    text: "AI-led workflow automation, assistants, decision support, retrieval systems and responsible enterprise AI integration.",
    tags: ["AI strategy", "Automation", "LLM platforms"],
  },
  {
    icon: Blocks,
    title: "Applications & Digital Platforms",
    text: "Custom business applications, client portals, operational platforms, APIs and secure workflow systems built around your organisation.",
    tags: ["Web apps", "APIs", "Portals"],
  },
  {
    icon: Database,
    title: "Data Architecture & Engineering",
    text: "Data models, databases, integration, reporting, migration and analytics foundations that turn information into usable business intelligence.",
    tags: ["PostgreSQL", "Data models", "BI"],
  },
  {
    icon: CloudCog,
    title: "Cloud, Server & Data Centre",
    text: "Architecture, migration, server platforms, virtualisation, cloud services, resilience, backup and infrastructure modernisation.",
    tags: ["Cloud", "Servers", "Resilience"],
  },
  {
    icon: Network,
    title: "Networks & Connectivity",
    text: "Secure LAN/WAN, Wi-Fi, VPN, multi-site connectivity, infrastructure design, monitoring and performance engineering.",
    tags: ["LAN/WAN", "Wi-Fi", "VPN"],
  },
  {
    icon: ShieldCheck,
    title: "Cybersecurity & Governance",
    text: "Security baselines, identity, hardening, risk reviews, business continuity, data protection and practical security improvement programmes.",
    tags: ["Security", "Identity", "Risk"],
  },
  {
    icon: HeartPulse,
    title: "Healthcare Technology",
    text: "Digital health platforms, clinic systems, EPR/LIMS integration, diagnostics workflows, healthcare operations and technology-enabled service design.",
    tags: ["Digital health", "EPR/LIMS", "Diagnostics"],
  },
  {
    icon: Globe2,
    title: "Websites & Digital Experience",
    text: "Modern business websites, secure hosting, online services, search optimisation, analytics and long-term digital management.",
    tags: ["Web", "SEO", "UX"],
  },
];

export const sectors = [
  "Healthcare & Life Sciences",
  "Professional Services",
  "Hotels & Hospitality",
  "Charities & NGOs",
  "Schools & Education",
  "Public Sector",
  "SMEs & Growing Businesses",
  "International Projects",
];

export const solutionMap = {
  "Modernise operations": [
    "Custom applications and workflow platforms",
    "AI automation and intelligent assistants",
    "Cloud and infrastructure modernisation",
  ],
  "Improve data": [
    "Data architecture and PostgreSQL platforms",
    "System integration and API design",
    "Analytics and decision-support foundations",
  ],
  "Strengthen security": [
    "Cybersecurity baseline and risk review",
    "Identity and access hardening",
    "Backup, resilience and business continuity",
  ],
  "Transform healthcare": [
    "Digital health platform design",
    "EPR/LIMS and diagnostics integration",
    "Clinic technology and operational workflow improvement",
  ],
};
