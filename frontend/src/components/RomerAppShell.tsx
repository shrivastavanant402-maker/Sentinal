import type { ReactNode } from "react";
import type { View } from "../types/figma";

/* ───────── Nav items mapped to existing Sentinal views ───────── */
const navItems: { id: View; label: string; icon: string }[] = [
  { id: "operations", label: "Command", icon: "terminal" },
  { id: "incident",   label: "Signals", icon: "sensors" },
  { id: "ledger",     label: "Approvals", icon: "verified_user" },
  { id: "agents",     label: "Agents", icon: "group" },
  { id: "live_map",   label: "Live Map", icon: "monitoring" },
  { id: "attack_lab", label: "Attack Lab", icon: "analytics" },
  { id: "replay",     label: "Reports", icon: "description" },
  { id: "ide",        label: "IDE / MCP", icon: "code" },
];

export function RomerAppShell({
  view,
  setView,
  health,
  alertCount,
  isRefreshing,
  onRefresh,
  children,
}: {
  view: View;
  setView: (v: View) => void;
  health: { status?: string } | null;
  alertCount: number;
  isRefreshing: boolean;
  onRefresh: () => void;
  children: ReactNode;
}) {
  const isHealthy = health?.status === "healthy" || health?.status === "ok";

  return (
    <div className="romer-root">
      {/* ─── Desktop sidebar ─── */}
      <nav className="romer-sidebar">
        {/* Brand */}
        <div className="romer-sidebar-brand">
          <span className="material-symbols-outlined">terminal</span>
          <div>
            <h1>OPERATIONS</h1>
            <p>v2.4.0-stable</p>
          </div>
        </div>

        {/* Navigation */}
        <div className="romer-nav">
          {navItems.map((item) => (
            <button
              key={item.id}
              className={`romer-nav-item${view === item.id ? " active" : ""}`}
              onClick={() => setView(item.id)}
            >
              <span className="material-symbols-outlined">{item.icon}</span>
              {item.label}
              {item.id === "incident" && alertCount > 0 && (
                <span className="romer-nav-badge">{alertCount}</span>
              )}
            </button>
          ))}
        </div>

        {/* Footer */}
        <div className="romer-sidebar-footer">
          <button
            className="romer-btn-primary"
            onClick={onRefresh}
            disabled={isRefreshing}
          >
            {isRefreshing ? "Syncing…" : "Launch Terminal"}
          </button>

          <div className="romer-sidebar-links">
            <a href="#">
              <span className="material-symbols-outlined">help</span> Docs
            </a>
            <a href="#">
              <span className="material-symbols-outlined">contact_support</span> Support
            </a>
          </div>

          <div className="romer-sidebar-user">
            <div className="romer-avatar">
              {isHealthy ? (
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#50d8e9", display: "block" }} />
              ) : (
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#ffb4ab", display: "block" }} />
              )}
            </div>
            <span className="romer-sidebar-user-info">System Admin</span>
          </div>
        </div>
      </nav>

      {/* ─── Main area ─── */}
      <main className="romer-main">
        {/* Mobile header */}
        <header className="romer-mobile-header">
          <div className="romer-mobile-header-title">ROMER</div>
          <div className="romer-mobile-actions">
            <span className="material-symbols-outlined">notifications</span>
            <span className="material-symbols-outlined">settings</span>
            <button className="romer-mobile-ws-btn">Workspace</button>
          </div>
        </header>

        {children}
      </main>
    </div>
  );
}
