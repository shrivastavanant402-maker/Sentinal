import type { FigmaAgent as Agent, RuntimeEvent } from "../types/figma";
import type { Alert, LedgerReport } from "../types";

export function RomerDashboard({
  agents,
  runtimeEventsList,
  alertsList,
}: {
  go: (view: any) => void;
  agents: Agent[];
  runtimeEventsList: RuntimeEvent[];
  alertsList: Alert[];
  ledgerReport: LedgerReport | null;
}) {
  const activeCount = agents.filter((a) => a.status === "Active").length;
  const totalAgents = agents.length || 1;
  const uptime = ((activeCount / totalAgents) * 100).toFixed(3);
  const highPriorityAlerts = alertsList.filter(
    (a) => a.severity === "critical" || a.severity === "high"
  ).length;

  return (
    <div className="romer-content">
      {/* ─── Page Header ─── */}
      <div className="romer-page-header">
        <h1 className="romer-page-title">Command dashboard</h1>
        <p className="romer-page-subtitle">
          Live operating layer for focused teams
        </p>
      </div>

      {/* ─── Top Metrics Row ─── */}
      <div className="romer-metrics-row">
        {/* Signal Uptime — real data from agents */}
        <div className="romer-metric-card">
          <div className="romer-metric-dot ok" />
          <div className="romer-metric-label">Signal Uptime</div>
          <div className="romer-metric-value">{uptime}%</div>
          <div className="romer-metric-detail">
            Active nodes: {activeCount}/{agents.length}
          </div>
        </div>

        {/* Approval Latency — placeholder (no backend source) */}
        <div className="romer-metric-card">
          <div className="romer-metric-dot ok" />
          <div className="romer-metric-label">Approval Latency</div>
          <div className="romer-metric-value">1.2s</div>
          <div className="romer-metric-detail">p95 avg globally</div>
        </div>

        {/* Open Incidents — real data from alerts */}
        <div className="romer-metric-card">
          <div className={`romer-metric-dot ${alertsList.length > 0 ? "error" : "ok"}`} />
          <div className="romer-metric-label">Open Incidents</div>
          <div className="romer-metric-value">{alertsList.length}</div>
          <div className={`romer-metric-detail${highPriorityAlerts > 0 ? " error-text" : ""}`}>
            {highPriorityAlerts > 0
              ? `${highPriorityAlerts} high priority`
              : "All clear"}
          </div>
        </div>
      </div>

      {/* ─── Central Grid ─── */}
      <div className="romer-central-grid">
        {/* Live Telemetry Graph */}
        <div className="romer-telemetry">
          <div className="romer-panel-header">
            <div className="romer-panel-title">
              <span className="material-symbols-outlined">monitoring</span>
              Live Telemetry
            </div>
            <div className="romer-segmented">
              <button className="romer-seg-btn">1H</button>
              <button className="romer-seg-btn active">24H</button>
              <button className="romer-seg-btn">7D</button>
            </div>
          </div>
          <div className="romer-graph-area">
            <div className="romer-graph-glow" />
            {/* Y-Axis labels */}
            <div className="romer-graph-y-axis">
              <span>100k</span>
              <span>75k</span>
              <span>50k</span>
              <span>25k</span>
              <span>0</span>
            </div>
            {/* Graph canvas */}
            <div className="romer-graph-canvas">
              {/* Cyan line */}
              <svg preserveAspectRatio="none">
                <path
                  d="M0,80 Q20,60 40,70 T80,40 T120,50 T160,20 T200,30"
                  fill="none"
                  stroke="#50d8e9"
                  strokeWidth="2"
                  vectorEffect="non-scaling-stroke"
                />
              </svg>
              {/* Violet line */}
              <svg preserveAspectRatio="none">
                <path
                  d="M0,90 Q30,80 60,85 T100,50 T140,60 T180,30 T200,40"
                  fill="none"
                  opacity="0.7"
                  stroke="#7a85ff"
                  strokeWidth="1.5"
                  vectorEffect="non-scaling-stroke"
                />
              </svg>
            </div>
            {/* X-Axis labels */}
            <div className="romer-graph-x-axis">
              <span>00:00</span>
              <span>04:00</span>
              <span>08:00</span>
              <span>12:00</span>
              <span>16:00</span>
              <span>20:00</span>
            </div>
          </div>
        </div>

        {/* Signal Status — real data from agents */}
        <div className="romer-signal-panel">
          <div className="romer-panel-header">
            <div className="romer-panel-title">
              <span className="material-symbols-outlined">list_alt</span>
              Signal Status
            </div>
          </div>
          <div className="romer-signal-list">
            {agents.map((a) => {
              const isError =
                a.status === "Quarantined" || a.status === "Degraded";
              const dotClass = a.status === "Active"
                ? "ok"
                : isError
                ? "error"
                : "muted";
              return (
                <div
                  key={a.id}
                  className={`romer-signal-item${isError ? " degraded" : ""}`}
                >
                  <div className="romer-signal-left">
                    <div className={`romer-status-dot ${dotClass}`} />
                    <div
                      className={`romer-signal-name${isError ? " error-text" : ""}`}
                    >
                      {a.name || a.id.substring(0, 12)}
                    </div>
                  </div>
                  <div
                    className={`romer-signal-status${isError ? " error-text" : ""}`}
                  >
                    {a.status}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ─── Bottom Row ─── */}
      <div className="romer-bottom-row">
        {/* Pending Approvals — static placeholder (no backend source) */}
        <div className="romer-data-panel">
          <div className="romer-panel-header">
            <div className="romer-panel-title">Pending Approvals</div>
            <button className="romer-panel-action-btn">View All</button>
          </div>
          <div style={{ flex: 1, overflowY: "auto" }}>
            <table className="romer-table">
              <thead>
                <tr>
                  <th>Req ID</th>
                  <th>Type</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="mono">REQ-992</td>
                  <td className="variant">Deploy Config</td>
                  <td>
                    <span className="romer-status-badge">Awaiting</span>
                  </td>
                </tr>
                <tr>
                  <td className="mono">REQ-991</td>
                  <td className="variant">Access Grant</td>
                  <td>
                    <span className="romer-status-badge">Awaiting</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Decision Log — real data from runtime events */}
        <div className="romer-data-panel">
          <div className="romer-panel-header">
            <div className="romer-panel-title">Decision Log</div>
          </div>
          <div className="romer-log-list">
            {runtimeEventsList.slice(0, 20).map((e) => {
              const isBlock = e.decision === "Block";
              return (
                <div key={e.seq} className="romer-log-entry">
                  <div className={`romer-log-icon${isBlock ? " error-text" : ""}`}>
                    <span className="material-symbols-outlined">
                      {isBlock ? "block" : "commit"}
                    </span>
                  </div>
                  <div>
                    <div className={`romer-log-text${isBlock ? " error-text" : ""}`}>
                      {e.decision.toUpperCase()} {e.type} on {e.resource}
                    </div>
                    <div className="romer-log-meta">
                      {e.agent.substring(0, 8)} • {e.time}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
