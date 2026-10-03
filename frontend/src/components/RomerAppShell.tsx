import { type ReactNode, useState } from "react";
import type { View } from "../types/figma";

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
  const isHealthy = health?.status === "healthy" || health?.status === "ok";

  const handleNav = (v: View) => {
    setView(v);
    if (onNavClick) onNavClick(v);
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
            onClick={() => setView("operations")}
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
                  onClick={() => handleNav("operations")}
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
        <div className={`romer-window-frame${view !== "operations" ? " is-subview" : ""}`}>
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
    </div>
  );
}
