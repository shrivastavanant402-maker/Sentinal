import { useState } from "react";
import type { FigmaAgent as Agent, RuntimeEvent } from "../types/figma";
import type { Alert, LedgerReport } from "../types";

export function RomerDashboard({
  go,
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
  const [timeRange, setTimeRange] = useState<"1H" | "24H" | "7D">("24H");
  const activeCount = agents.filter((a) => a.status === "Active").length;
  const totalAgents = agents.length || 1;
  const highPriorityAlerts = alertsList.filter(
    (a) => a.severity === "critical" || a.severity === "high"
  ).length;

  const capacityPct = Math.min(100, Math.max(70, Math.round((activeCount / totalAgents) * 86)));
  const openApprovals = alertsList.length > 0 ? alertsList.length : 14;
  const riskIndex = highPriorityAlerts > 0 ? "ELEVATED" : "LOW";

  return (
    <>
      {/* ─── Center Workspace Column ─── */}
      <div className="romer-center-column">
        {/* Status Row */}
        <div className="romer-status-row">
          <div className="romer-live-indicator">
            <span className="romer-live-dot" />
            <span>SYSTEM LIVE</span>
          </div>
          <div className="romer-last-updated">
            LAST UPDATED: JUST NOW
          </div>
        </div>

        {/* 6 Metrics Grid (2 x 3) */}
        <div className="romer-metrics-grid">
          {/* 1. Revenue */}
          <div className="romer-white-card">
            <div className="romer-card-header">REVENUE</div>
            <div className="romer-card-number">$2.4M</div>
            <div className="romer-card-footer positive">
              <span>+12% vs last month</span>
              <div className="romer-sparkline" title="Monthly growth trend">
                <span className="romer-spark-bar" style={{ height: "4px" }} />
                <span className="romer-spark-bar" style={{ height: "6px" }} />
                <span className="romer-spark-bar" style={{ height: "8px" }} />
                <span className="romer-spark-bar" style={{ height: "7px" }} />
                <span className="romer-spark-bar tall" />
              </div>
            </div>
          </div>

          {/* 2. Open Approvals */}
          <div className="romer-white-card" style={{ cursor: "pointer" }} onClick={() => go("ledger")}>
            <div className="romer-card-header">OPEN APPROVALS</div>
            <div className="romer-card-number">{openApprovals}</div>
            <div className="romer-card-footer">
              <span>{highPriorityAlerts > 0 ? `${highPriorityAlerts} requiring attention` : "3 requiring attention"}</span>
            </div>
          </div>

          {/* 3. Risk Index */}
          <div className="romer-white-card" style={{ cursor: "pointer" }} onClick={() => go("incident")}>
            <div className="romer-card-header">RISK INDEX</div>
            <div className="romer-card-number">{riskIndex}</div>
            <div className="romer-card-footer">
              <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: riskIndex === "LOW" ? "#22c55e" : "#ef4444" }} />
                {riskIndex === "LOW" ? "All systems stable" : "Incidents active"}
              </span>
            </div>
          </div>

          {/* 4. Capacity */}
          <div className="romer-white-card">
            <div className="romer-card-header">CAPACITY</div>
            <div className="romer-card-number">{capacityPct}%</div>
            <div className="romer-card-footer">
              <span>Optimal range</span>
            </div>
          </div>

          {/* 5. Node Status */}
          <div className="romer-white-card" style={{ cursor: "pointer" }} onClick={() => go("agents")}>
            <div className="romer-card-header">NODE STATUS</div>
            <div className="romer-card-number">
              {totalAgents >= 9 ? `${activeCount}/${totalAgents}` : "9/9"}
            </div>
            <div className="romer-card-footer">
              <span style={{ color: "#FFFFFF" }}>Active regions</span>
            </div>
          </div>

          {/* 6. System Latency */}
          <div className="romer-white-card">
            <div className="romer-card-header">SYSTEM LATENCY</div>
            <div className="romer-card-number">12ms</div>
            <div className="romer-card-footer">
              <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", color: "#FFFFFF" }}>
                <span className="material-symbols-outlined" style={{ fontSize: "14px", color: "#22c55e" }}>check_circle</span>
                P99 optimal
              </span>
            </div>
          </div>
        </div>

        {/* Signal Flow Telemetry Chart Card */}
        <div className="romer-chart-card">
          <div className="romer-chart-header">
            <div className="romer-chart-title-group">
              <span className="romer-chart-title">SIGNAL FLOW</span>
              <span className="romer-chart-latency">LATENCY 12MS</span>
            </div>
            <div className="romer-chart-legend">
              <div className="romer-legend-item">
                <span className="romer-legend-dot revenue" />
                <span>REVENUE</span>
              </div>
              <div className="romer-legend-item">
                <span className="romer-legend-dot goal" />
                <span>GOAL</span>
              </div>
              <div style={{ display: "flex", gap: "4px", marginLeft: "12px" }}>
                {(["1H", "24H", "7D"] as const).map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setTimeRange(r)}
                    style={{
                      background: timeRange === r ? "#222227" : "transparent",
                      border: "1px solid",
                      borderColor: timeRange === r ? "rgba(255,255,255,0.25)" : "transparent",
                      color: timeRange === r ? "#FFFFFF" : "var(--rm-text-muted)",
                      borderRadius: "4px",
                      padding: "2px 8px",
                      fontSize: "10.5px",
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="romer-chart-canvas-area">
            <div className="romer-chart-grid-bg" />
            <svg
              className="romer-chart-svg"
              viewBox="0 0 700 220"
              preserveAspectRatio="none"
            >
              <defs>
                <linearGradient id="whiteGlow" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.12" />
                  <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0.0" />
                </linearGradient>
              </defs>
              {/* Gradient Area under curve */}
              <path
                d="M 0 170 Q 120 130, 240 145 T 480 80 T 700 95 L 700 220 L 0 220 Z"
                fill="url(#whiteGlow)"
              />
              {/* Primary White Waveform Line */}
              <path
                d="M 0 170 Q 120 130, 240 145 T 480 80 T 700 95"
                fill="none"
                stroke="#FFFFFF"
                strokeWidth="1.8"
                vectorEffect="non-scaling-stroke"
              />
              {/* Secondary Goal/Target Dashed Line */}
              <path
                d="M 0 140 Q 160 120, 320 110 T 700 65"
                fill="none"
                stroke="rgba(255, 255, 255, 0.35)"
                strokeDasharray="4 4"
                strokeWidth="1.2"
                vectorEffect="non-scaling-stroke"
              />
              {/* Data Node Markers */}
              <circle cx="240" cy="145" r="3.5" fill="#FFFFFF" />
              <circle cx="480" cy="80" r="3.5" fill="#FFFFFF" />
            </svg>
          </div>
        </div>
      </div>

      {/* ─── Column 3: ROMER INTELLIGENCE (Right Sidebar) ─── */}
      <div className="romer-intel-column">
        {/* Header */}
        <div className="romer-intel-header">
          <div className="romer-intel-header-left">
            <span className="material-symbols-outlined" style={{ fontSize: "16px", color: "#FFFFFF" }}>bolt</span>
            <span>ROMER INTELLIGENCE</span>
          </div>
          <span className="romer-intel-dot" />
        </div>

        {/* Card 1: Recommended Action */}
        <div className="romer-intel-box">
          <div className="romer-intel-label">RECOMMENDED ACTION</div>
          <div className="romer-intel-card">
            Reallocate resources to <span className="romer-intel-highlight">Project Alpha</span> to mitigate Q4 delivery risk.
          </div>
        </div>

        {/* Card 2: Signal Summary */}
        <div className="romer-intel-box">
          <div className="romer-intel-label">SIGNAL SUMMARY</div>
          <div className="romer-intel-card">
            Revenue trends <span className="romer-intel-highlight">positive (+12%)</span>, but capacity constraints emerging in engineering teams.
          </div>
        </div>

        {/* Card 3: Decision Log */}
        <div className="romer-intel-box" style={{ flex: 1, minHeight: 0 }}>
          <div className="romer-intel-label">DECISION LOG</div>
          <div className="romer-decision-list">
            {runtimeEventsList.length > 0 ? (
              runtimeEventsList.slice(0, 10).map((e) => {
                const isBlock = e.decision === "Block";
                return (
                  <div key={e.seq} className="romer-decision-item">
                    <div className="romer-decision-top">
                      <span className={`romer-decision-badge ${isBlock ? "blocked" : "approved"}`}>
                        {e.decision}
                      </span>
                      <span className="romer-decision-meta">{e.time || "Just now"}</span>
                    </div>
                    <div className="romer-decision-text">
                      <strong>{e.type}</strong> on {e.resource}
                    </div>
                    <div className="romer-decision-meta">Agent: {e.agent.substring(0, 14)}</div>
                  </div>
                );
              })
            ) : (
              <>
                <div className="romer-decision-item">
                  <div className="romer-decision-top">
                    <span className="romer-decision-badge approved">Approved</span>
                    <span className="romer-decision-meta">2m ago</span>
                  </div>
                  <div className="romer-decision-text">Policy authorization for executor-01 runtime node.</div>
                </div>
                <div className="romer-decision-item">
                  <div className="romer-decision-top">
                    <span className="romer-decision-badge approved">Approved</span>
                    <span className="romer-decision-meta">14m ago</span>
                  </div>
                  <div className="romer-decision-text">Signal sync verified across all active cluster pods.</div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
