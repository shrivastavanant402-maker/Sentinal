import { type ReactNode, useState } from "react";
import type { View } from "../types/figma";
import { simulateAttack } from "../services/api";

/* ───────── Sidebar items inside the dashboard frame ───────── */
const navItems: { id: View; label: string; icon: string }[] = [
  { id: "operations", label: "Overview", icon: "grid_view" },
  { id: "incident",   label: "Signals", icon: "sensors" },
  { id: "ledger",     label: "Approvals", icon: "check_circle" },
  { id: "live_map",   label: "Metrics", icon: "bar_chart" },
  { id: "attack_lab", label: "Risks", icon: "warning" },
  { id: "agents",     label: "Teams", icon: "group" },
  { id: "replay",     label: "Reports", icon: "description" },
  { id: "ide",        label: "IDE / MCP", icon: "terminal" },
];

export function RomerAppShell({
  view,
  setView,
  health,
  alertCount,
  isRefreshing,
  onRefresh,
  onNavClick,
  children,
}: {
  view: View;
  setView: (v: View) => void;
  health: { status?: string } | null;
  alertCount: number;
  isRefreshing: boolean;
  onRefresh: () => void;
  onNavClick?: (v: View) => void;
  children: ReactNode;
}) {
  const [activeTopTab, setActiveTopTab] = useState<string>("Platform");
  const [isQuickStartOpen, setIsQuickStartOpen] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [quickStartMsg, setQuickStartMsg] = useState<string | null>(null);
  const isHealthy = health?.status === "healthy" || health?.status === "ok";

  const handleNav = (v: View) => {
    setView(v);
    if (onNavClick) onNavClick(v);
  };

  const handleGetStarted = () => {
    setIsQuickStartOpen(true);
    const el = document.getElementById("romer-command-center");
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const handleQuickAttack = async () => {
    setIsSimulating(true);
    setQuickStartMsg(null);
    try {
      const res = await simulateAttack({
        scenario: "secret_exfiltration",
        agent_id: "researcher-01",
      });
      setQuickStartMsg(`⚡ PEP Intercepted: Blocked action '${res.action || "database.export"}'. Tamper-proof block logged.`);
      onRefresh();
    } catch (err: any) {
      setQuickStartMsg(`Simulation error: ${err.message || "Failed"}`);
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <div className="romer-root">
      {/* ─── Top Navigation Bar ─── */}
      <header className="romer-topbar">
        {/* Brand */}
        <div className="romer-topbar-left" style={{ cursor: "pointer" }} onClick={() => handleNav("operations")}>
          <div className="romer-brand-badge">R</div>
          <span className="romer-brand-name">Romer</span>
          <div style={{ display: "inline-flex", alignItems: "center", gap: "5px", marginLeft: "10px", fontSize: "11px", color: "var(--rm-text-muted)" }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: isHealthy ? "#22c55e" : "#ef4444" }} />
            <span>{isHealthy ? "ONLINE" : "OFFLINE"}</span>
          </div>
        </div>

        {/* Nav Links */}
        <nav className="romer-topbar-nav">
          {[
            { label: "Platform", view: "operations" as View },
            { label: "Dashboards", view: "operations" as View },
            { label: "Customers", view: "agents" as View },
            { label: "Pricing", view: "ledger" as View },
            { label: "Resources", view: "replay" as View },
            { label: "Contact", view: "ide" as View },
          ].map((item) => (
            <button
              key={item.label}
              type="button"
              className={`romer-topbar-link${activeTopTab === item.label ? " active" : ""}`}
              onClick={() => {
                setActiveTopTab(item.label);
                handleNav(item.view);
              }}
            >
              {item.label}
            </button>
          ))}
        </nav>

        {/* Actions */}
        <div className="romer-topbar-actions">
          <button
            type="button"
            className="romer-btn-ghost"
            onClick={onRefresh}
            title={isRefreshing ? "Refreshing..." : "Refresh data"}
          >
            {isRefreshing ? "Syncing…" : "Log in"}
          </button>
          <button
            type="button"
            className="romer-btn-white"
            onClick={handleGetStarted}
          >
            Start free
          </button>
        </div>
      </header>

      {/* ─── Main Container ─── */}
      <div className="romer-container">
        {/* Hero Section — shown ONLY on landing/overview page */}
        {view === "operations" && (
          <section className="romer-hero">
            <h1 className="romer-hero-title">
              The command dashboard<br />for focused teams
            </h1>
            <p className="romer-hero-subtitle">
              Romer turns scattered signals, approvals, and operating data into one calm dashboard for leadership teams.
            </p>

            <div className="romer-hero-row">
              <div className="romer-hero-ctas">
                <button
                  type="button"
                  className="romer-btn-white"
                  onClick={handleGetStarted}
                >
                  Get started
                </button>
                <button
                  type="button"
                  className="romer-btn-dark"
                  onClick={() => handleNav("live_map")}
                >
                  Book a demo
                </button>
              </div>

              <button
                type="button"
                className="romer-hero-link"
                onClick={onRefresh}
                style={{ background: "none", border: "none", cursor: "pointer" }}
              >
                Live operating layer romer.app/overview &rarr;
              </button>
            </div>
          </section>
        )}

        {/* Framed Executive Command Center Window */}
        <div id="romer-command-center" className={`romer-window-frame${view !== "operations" ? " is-subview" : ""}`}>
          <div className="romer-dashboard-layout">
            {/* Column 1: Navigation Sidebar inside frame */}
            <aside className="romer-window-nav">
              <div className="romer-nav-heading">NAVIGATION</div>
              {navItems.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`romer-nav-pill${view === item.id ? " active" : ""}`}
                  onClick={() => handleNav(item.id)}
                >
                  <span className="material-symbols-outlined">{item.icon}</span>
                  <span>{item.label}</span>
                  {item.id === "incident" && alertCount > 0 && (
                    <span className="romer-nav-pill-badge">{alertCount}</span>
                  )}
                </button>
              ))}
            </aside>

            {/* If Operations view, RomerDashboard provides Center + Intel columns */}
            {view === "operations" ? (
              children
            ) : (
              <div className="romer-subview-content" style={{ gridColumn: "span 2" }}>
                {children}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ─── Interactive Quick Start Modal ─── */}
      {isQuickStartOpen && (
        <div className="romer-modal-overlay" onClick={() => setIsQuickStartOpen(false)}>
          <div className="romer-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="romer-modal-header">
              <div>
                <h2 className="romer-modal-title">Get Started with Sentinel Mesh</h2>
                <p className="romer-modal-desc">
                  Select an operational action to test autonomous runtime security and policy enforcement live.
                </p>
              </div>
              <button
                type="button"
                className="romer-modal-close"
                onClick={() => setIsQuickStartOpen(false)}
                title="Close"
              >
                <span className="material-symbols-outlined" style={{ fontSize: "20px" }}>close</span>
              </button>
            </div>

            <div className="romer-modal-body">
              {quickStartMsg && (
                <div style={{
                  padding: "12px 14px",
                  borderRadius: "6px",
                  background: "#18181f",
                  border: "1px solid #383842",
                  fontSize: "12px",
                  color: "#FFFFFF",
                  fontFamily: "var(--font-mono, monospace)",
                  lineHeight: "1.4"
                }}>
                  {quickStartMsg}
                </div>
              )}

              <div className="romer-quickstart-grid">
                {/* Action 1: Attack simulation */}
                <div className="romer-quickstart-card">
                  <div>
                    <div className="romer-quickstart-card-title">
                      <span className="material-symbols-outlined" style={{ fontSize: "18px", color: "#FFFFFF" }}>bolt</span>
                      <span>Simulate Data Leak</span>
                    </div>
                    <p className="romer-quickstart-card-desc" style={{ marginTop: "6px" }}>
                      Trigger secret exfiltration attempt against researcher-01 and verify instant PEP isolation.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="romer-btn-white"
                    style={{ width: "100%", justifyContent: "center" }}
                    onClick={handleQuickAttack}
                    disabled={isSimulating}
                  >
                    {isSimulating ? "Simulating..." : "Run Test Simulation"}
                  </button>
                </div>

                {/* Action 2: Live Map */}
                <div className="romer-quickstart-card">
                  <div>
                    <div className="romer-quickstart-card-title">
                      <span className="material-symbols-outlined" style={{ fontSize: "18px", color: "#FFFFFF" }}>hub</span>
                      <span>Explore Live Mesh</span>
                    </div>
                    <p className="romer-quickstart-card-desc" style={{ marginTop: "6px" }}>
                      Inspect the force-directed topology of active agents, communication channels, and the central PEP Hub.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="romer-btn-dark"
                    style={{ width: "100%", justifyContent: "center" }}
                    onClick={() => {
                      setIsQuickStartOpen(false);
                      handleNav("live_map");
                    }}
                  >
                    Open Live Map &rarr;
                  </button>
                </div>

                {/* Action 3: Threat Signals */}
                <div className="romer-quickstart-card">
                  <div>
                    <div className="romer-quickstart-card-title">
                      <span className="material-symbols-outlined" style={{ fontSize: "18px", color: "#FFFFFF" }}>sensors</span>
                      <span>Active Signals & Alerts</span>
                    </div>
                    <p className="romer-quickstart-card-desc" style={{ marginTop: "6px" }}>
                      Review intercepted policy violations, containment histories, and forensic telemetry logs.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="romer-btn-dark"
                    style={{ width: "100%", justifyContent: "center" }}
                    onClick={() => {
                      setIsQuickStartOpen(false);
                      handleNav("incident");
                    }}
                  >
                    View Signals &rarr;
                  </button>
                </div>

                {/* Action 4: Merkle Ledger */}
                <div className="romer-quickstart-card">
                  <div>
                    <div className="romer-quickstart-card-title">
                      <span className="material-symbols-outlined" style={{ fontSize: "18px", color: "#FFFFFF" }}>verified_user</span>
                      <span>Audit Merkle Ledger</span>
                    </div>
                    <p className="romer-quickstart-card-desc" style={{ marginTop: "6px" }}>
                      Validate the cryptographic SHA-256 hash continuity against genesis root block.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="romer-btn-dark"
                    style={{ width: "100%", justifyContent: "center" }}
                    onClick={() => {
                      setIsQuickStartOpen(false);
                      handleNav("ledger");
                    }}
                  >
                    Audit Ledger &rarr;
                  </button>
                </div>
              </div>
            </div>

            <div className="romer-modal-footer">
              <span style={{ fontSize: "12px", color: "var(--rm-text-muted)" }}>
                Press ESC or click outside to dismiss
              </span>
              <button
                type="button"
                className="romer-btn-white"
                onClick={() => {
                  setIsQuickStartOpen(false);
                  const el = document.getElementById("romer-command-center");
                  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
                }}
              >
                Explore Command Dashboard &rarr;
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
