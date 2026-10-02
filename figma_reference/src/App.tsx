import { useEffect, useMemo, useState, type ReactNode } from "react"
import { agents, mission, replayEvents, runtimeEvents } from "./data"
import type { Agent, Decision, RuntimeEvent, View } from "./types"

type IconName = "activity" | "agents" | "alert" | "replay" | "ledger" | "search" | "bell" | "check" | "pause" | "play" | "filter" | "chevron" | "shield" | "copy" | "more" | "x" | "clock" | "link"

const iconPaths: Record<IconName, ReactNode> = {
  activity: (
    <>
      <path d="M3 12h4l2-7 4 14 2-7h6" />
    </>
  ),
  agents: (
    <>
      <circle cx="9" cy="7" r="4" />
      <path d="M2.5 21v-2a6.5 6.5 0 0 1 13 0v2M16 4.5a4 4 0 0 1 0 7.5M18 15a5 5 0 0 1 3.5 4.8V21" />
    </>
  ),
  alert: (
    <>
      <path d="M12 3 2.8 19a1.4 1.4 0 0 0 1.2 2h16a1.4 1.4 0 0 0 1.2-2L12 3Z" />
      <path d="M12 9v4M12 17h.01" />
    </>
  ),
  replay: (
    <>
      <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
      <path d="M3 3v5h5" />
    </>
  ),
  ledger: (
    <>
      <path d="M5 3h14v18H5zM8 7h8M8 11h8M8 15h5" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-4-4" />
    </>
  ),
  bell: (
    <>
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" />
    </>
  ),
  check: <path d="m5 12 4 4L19 6" />,
  pause: (
    <>
      <path d="M9 5v14M15 5v14" />
    </>
  ),
  play: <path d="m8 5 11 7-11 7V5Z" />,
  filter: <path d="M4 6h16M7 12h10M10 18h4" />,
  chevron: <path d="m9 18 6-6-6-6" />,
  shield: (
    <>
      <path d="M12 3 20 6v5c0 5-3.4 8.5-8 10-4.6-1.5-8-5-8-10V6l8-3Z" />
      <path d="m8.5 12 2 2 5-5" />
    </>
  ),
  copy: (
    <>
      <rect x="8" y="8" width="11" height="11" rx="2" />
      <path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3" />
    </>
  ),
  more: (
    <>
      <circle cx="5" cy="12" r="1" />
      <circle cx="12" cy="12" r="1" />
      <circle cx="19" cy="12" r="1" />
    </>
  ),
  x: (
    <>
      <path d="m6 6 12 12M18 6 6 18" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  link: (
    <>
      <path d="M10 13a5 5 0 0 0 7.5.5l2-2a5 5 0 0 0-7-7l-1.2 1.2" />
      <path d="M14 11a5 5 0 0 0-7.5-.5l-2 2a5 5 0 0 0 7 7l1.2-1.2" />
    </>
  ),
}

function Icon({ name, size = 17 }: { name: IconName size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {iconPaths[name]}
    </svg>
  )
}
function Button({
  children,
  variant = "ghost",
  className = "",
  onClick,
  title,
  disabled = false,
}: {
  children: ReactNode
  variant?: "primary" | "secondary" | "ghost" | "danger"
  className?: string
  onClick?: () => void
  title?: string
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      className={`button ${variant} ${className}`}
      onClick={onClick}
      title={title}
      disabled={disabled}
    >
      {children}
    </button>
  )
}
function Input({
  value,
  onChange,
  placeholder,
  label,
}: {
  value: string
  onChange: (value: string) => void
  placeholder: string
  label: string
}) {
  return (
    <div className="input-wrap">
      <Icon name="search" size={15} />
      <input
        aria-label={label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  )
}
function Select({
  value,
  onChange,
  label,
  children,
}: {
  value: string
  onChange: (value: string) => void
  label: string
  children: ReactNode
}) {
  return (
    <select
      aria-label={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      {children}
    </select>
  )
}
function Status({ value }: { value: string }) {
  const tone = ["Critical", "Block", "Quarantined", "Failed"].includes(value)
    ? "critical"
    : ["High", "Require approval", "Degraded", "Pending"].includes(value)
      ? "warning"
      : ["Allow", "Active", "Trusted", "Verified", "Contained"].includes(value)
        ? "success"
        : "neutral"
  return (
    <span className={`status ${tone}`}>
      <span />
      {value}
    </span>
  )
}
function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard?.writeText(value)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1200)
  }
  return (
    <Button className="copy-button" onClick={copy} title={`Copy ${value}`}>
      <Icon name={copied ? "check" : "copy"} size={13} />
      {copied ? "Copied" : "Copy"}
    </Button>
  )
}

const nav: { id: View label: string icon: IconName count?: number }[] = [
  { id: "operations", label: "Operations", icon: "activity" },
  { id: "agents", label: "Agents", icon: "agents" },
  { id: "incident", label: "Incidents", icon: "alert", count: 1 },
  { id: "replay", label: "Replay", icon: "replay" },
  { id: "ledger", label: "Audit ledger", icon: "ledger" },
]

function AppShell({
  view,
  setView,
  children,
}: {
  view: View
  setView: (view: View) => void
  children: ReactNode
}) {
  const [globalSearch, setGlobalSearch] = useState("")
  const currentNav = nav.find((item) => item.id === view) ?? nav[0]
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-symbol">
            <Icon name="shield" size={18} />
          </div>
          <span>
            AegisMesh
            <small>Control</small>
          </span>
        </div>
        <div className="nav-label">Workspace</div>
        <nav aria-label="Primary navigation">
          {nav.map((item) => (
            <Button
              key={item.id}
              className={`nav-button ${view === item.id ? "active" : ""}`}
              onClick={() => setView(item.id)}
              title={item.label}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
              {item.count && <b>{item.count}</b>}
            </Button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="connection">
            <span />
            All systems operational
          </div>
          <div className="user-row">
            <div className="avatar">AK</div>
            <div>
              <strong>Alex Kim</strong>
              <small>Security admin</small>
            </div>
            <Icon name="more" size={16} />
          </div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div className="topbar-context">
            <Icon name={currentNav.icon} size={15} />
            <span>{currentNav.label}</span>
          </div>
          <Input
            value={globalSearch}
            onChange={setGlobalSearch}
            placeholder="Search AegisMesh"
            label="Global search"
          />
          <div className="top-actions">
            <div className="environment">
              <span />
              Production
            </div>
            <Button className="icon-button" title="Notifications">
              <Icon name="bell" />
            </Button>
          </div>
        </header>
        {children}
      </main>
    </div>
  )
}

function PageHeader({
  title,
  description,
  children,
  eyebrow,
}: {
  title: string
  description: string
  children?: ReactNode
  eyebrow?: string
}) {
  return (
    <section className="page-header">
      <div>
        {eyebrow && <div className="breadcrumb">{eyebrow}</div>}
        <div className="page-title">{title}</div>
        <div className="page-description">{description}</div>
      </div>
      {children && <div className="header-actions">{children}</div>}
    </section>
  )
}

function FilterBar({
  query,
  setQuery,
  agent,
  setAgent,
  decision,
  setDecision,
  extra,
}: {
  query: string
  setQuery: (v: string) => void
  agent?: string
  setAgent?: (v: string) => void
  decision?: string
  setDecision?: (v: string) => void
  extra?: ReactNode
}) {
  return (
    <div className="filter-bar">
      <Input
        value={query}
        onChange={setQuery}
        placeholder="Filter records"
        label="Filter records"
      />
      {setAgent && (
        <Select
          value={agent || "All agents"}
          onChange={setAgent}
          label="Filter by agent"
        >
          <option>All agents</option>
          {agents.map((a) => (
            <option key={a.id}>{a.name}</option>
          ))}
        </Select>
      )}
      {setDecision && (
        <Select
          value={decision || "All decisions"}
          onChange={setDecision}
          label="Filter by decision"
        >
          <option>All decisions</option>
          <option>Allow</option>
          <option>Block</option>
          <option>Sandbox</option>
        </Select>
      )}
      <Button variant="secondary">
        <Icon name="clock" size={14} />
        Last 15 minutes
      </Button>
      {extra}
      <span className="record-count">Updated just now</span>
    </div>
  )
}

function EventTable({
  events,
  selected,
  onSelect,
}: {
  events: RuntimeEvent[]
  selected?: RuntimeEvent | null
  onSelect?: (event: RuntimeEvent) => void
}) {
  return (
    <div className="data-table event-table">
      <div className="table-head">
        <span>Time</span>
        <span>Agent</span>
        <span>Event</span>
        <span>Resource</span>
        <span>Decision</span>
        <span>Risk</span>
        <span>Latency</span>
      </div>
      {events.map((event) => (
        <Button
          key={event.seq}
          className={`table-row ${
            selected?.seq === event.seq ? "selected" : ""
          }`}
          onClick={() => onSelect?.(event)}
        >
          <code>{event.time}</code>
          <span>{event.agent}</span>
          <strong>{event.type}</strong>
          <code>{event.resource}</code>
          <Status value={event.decision} />
          <span className={`risk ${event.severity.toLowerCase()}`}>
            {event.severity}
          </span>
          <code className="right">{event.latency} ms</code>
        </Button>
      ))}
      {events.length === 0 && (
        <div className="empty-state">No events match the current filters.</div>
      )}
    </div>
  )
}

function OperationsView({ go }: { go: (view: View) => void }) {
  const [query, setQuery] = useState("")
  const [agent, setAgent] = useState("All agents")
  const [decision, setDecision] = useState("All decisions")
  const [paused, setPaused] = useState(false)
  const [selected, setSelected] = useState<RuntimeEvent | null>(
    runtimeEvents[3],
  )
  const filtered = useMemo(
    () =>
      runtimeEvents.filter(
        (event) =>
          (agent === "All agents" || event.agent === agent) &&
          (decision === "All decisions" || event.decision === decision) &&
          `${event.type} ${event.resource} ${event.agent}`
            .toLowerCase()
            .includes(query.toLowerCase()),
      ),
    [query, agent, decision],
  )
  return (
    <div className="page">
      <PageHeader
        title="Live operations"
        description="Monitor enforcement decisions, agent health, and mission continuity in real time."
      >
        <Button variant="secondary">
          <Icon name="clock" size={14} />
          Last 15 minutes
        </Button>
      </PageHeader>
      <section className="metric-strip">
        <div>
          <span>Active agents</span>
          <strong>2 of 3</strong>
          <small>1 quarantined</small>
        </div>
        <div>
          <span>Events / sec</span>
          <strong>1,284</strong>
          <small className="positive">+4.2% vs prior 15m</small>
        </div>
        <div>
          <span>Block rate</span>
          <strong>0.13%</strong>
          <small>17 of 13,114 actions</small>
        </div>
        <div>
          <span>Decision p95</span>
          <strong>42 ms</strong>
          <small className="positive">Within 100 ms SLO</small>
        </div>
        <div>
          <span>Ledger status</span>
          <strong className="verified">Verified</strong>
          <small>Through sequence #18402</small>
        </div>
      </section>
      <section className="priority-panel">
        <div className="section-heading">
          <div>
            <strong>Needs attention</strong>
            <span>1 active incident · 1 pending approval</span>
          </div>
        </div>
        <div className="priority-row critical-row">
          <Status value="Critical" />
          <div className="priority-content">
            <strong>Unauthorized data export attempt</strong>
            <span>
              Researcher-01 attempted <code>database.export("customers")</code>
            </span>
          </div>
          <div className="priority-meta">
            <span>Contained in 19 ms</span>
            <small>10:31:06 UTC</small>
          </div>
          <Button variant="primary" onClick={() => go("incident")}>
            Investigate
          </Button>
        </div>
        <div className="priority-row">
          <Status value="Require approval" />
          <div className="priority-content">
            <strong>External report delivery</strong>
            <span>
              Executor-01 requests <code>external.post</code> to
              reports.example.com
            </span>
          </div>
          <div className="priority-meta">
            <span>Expires in 42s</span>
            <small>Approval #APR-104</small>
          </div>
          <Button variant="secondary">Review</Button>
        </div>
      </section>
      <div className="operations-layout">
        <section className="activity-panel">
          <div className="section-heading">
            <div>
              <strong>Runtime activity</strong>
              <span>Signed enforcement decisions from the active session</span>
            </div>
          </div>
          <FilterBar
            query={query}
            setQuery={setQuery}
            agent={agent}
            setAgent={setAgent}
            decision={decision}
            setDecision={setDecision}
            extra={
              <Button variant="secondary" onClick={() => setPaused(!paused)}>
                <Icon name={paused ? "play" : "pause"} size={14} />
                {paused ? "Resume stream" : "Pause stream"}
              </Button>
            }
          />
          <EventTable
            events={filtered}
            selected={selected}
            onSelect={setSelected}
          />
          <div className="table-footer">
            <span>
              Showing {filtered.length} of {runtimeEvents.length} events
            </span>
            <span>{paused ? "Stream paused" : "Live stream connected"}</span>
          </div>
        </section>
        <aside className="right-column">
          {selected && (
            <section className="inspector">
              <div className="section-heading">
                <div>
                  <strong>Event details</strong>
                  <span>Sequence #{selected.seq}</span>
                </div>
                <Button title="Close details" onClick={() => setSelected(null)}>
                  <Icon name="x" size={15} />
                </Button>
              </div>
              <dl>
                <dt>Decision reason</dt>
                <dd>{selected.reason}</dd>
                <dt>Event hash</dt>
                <dd className="inline-copy">
                  <code>{selected.hash.slice(0, 15)}…</code>
                  <CopyButton value={selected.hash} />
                </dd>
                <dt>Signature</dt>
                <dd>
                  <Status value={selected.signature} />
                </dd>
                <dt>Policy latency</dt>
                <dd>{selected.latency} ms</dd>
              </dl>
              <Button
                variant="secondary"
                className="full-width"
                onClick={() => go("ledger")}
              >
                View ledger evidence
              </Button>
            </section>
          )}
          <section className="agents-panel">
            <div className="section-heading">
              <div>
                <strong>Agent posture</strong>
                <span>Current mission participants</span>
              </div>
              <Button onClick={() => go("agents")}>View all</Button>
            </div>
            {agents.map((item) => (
              <Button
                key={item.id}
                className="agent-row"
                onClick={() => go("agents")}
              >
                <div className="agent-avatar">{item.name[0]}</div>
                <div>
                  <strong>{item.name}</strong>
                  <span>{item.step}</span>
                </div>
                <Status value={item.status} />
                <code>{item.trust}</code>
              </Button>
            ))}
          </section>
          <section className="mission-panel">
            <span>Active mission · SESS-001</span>
            <strong>{mission}</strong>
            <div className="mission-progress">
              <span />
            </div>
            <small>Step 2 of 3 · Workflow continued after containment</small>
          </section>
        </aside>
      </div>
    </div>
  )
}

function AgentsView({ setDialog }: { setDialog: (value: boolean) => void }) {
  const [query, setQuery] = useState("")
  const [selected, setSelected] = useState<Agent>(agents[1])
  const filtered = agents.filter((item) =>
    `${item.name} ${item.role} ${item.status}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  )
  return (
    <div className="page">
      <PageHeader
        title="Agents"
        description="Inspect identity, permissions, mission contracts, and behavioral trust."
      />
      <div className="agent-workbench">
        <section className="registry-pane">
        <FilterBar
          query={query}
          setQuery={setQuery}
          extra={<Button variant="primary">Register agent</Button>}
        />
        <div className="data-table agent-table">
          <div className="table-head">
            <span>Agent</span>
            <span>Status</span>
            <span>Trust</span>
            <span>Current step</span>
            <span>Last event</span>
            <span>Contract</span>
          </div>
          {filtered.map((item) => (
            <Button
              key={item.id}
              className={`table-row ${
                selected.id === item.id ? "selected" : ""
              }`}
              onClick={() => setSelected(item)}
            >
              <span className="agent-cell">
                <span className="agent-avatar">{item.name[0]}</span>
                <span>
                  <strong>{item.name}</strong>
                  <small>{item.role}</small>
                </span>
              </span>
              <Status value={item.status} />
              <span className="trust-cell">
                <strong>{item.trust}</strong>
                <small>{item.tier}</small>
              </span>
              <span>{item.step}</span>
              <span>{item.lastEvent}</span>
              <code>{item.contract}</code>
            </Button>
          ))}
        </div>
      </section>
      <aside className="agent-detail">
        <div className="detail-header">
          <div className="agent-avatar large">{selected.name[0]}</div>
          <div>
            <div className="detail-title">{selected.name}</div>
            <span>
              {selected.role} · {selected.id}
            </span>
          </div>
          <div className="detail-actions">
            <Button variant="secondary">Halt agent</Button>
            {selected.status === "Quarantined" && (
              <Button variant="danger" onClick={() => setDialog(true)}>
                Release quarantine
              </Button>
            )}
          </div>
        </div>
        <div className="detail-grid">
          <div>
            <div className="subsection-title">Identity and contract</div>
            <dl className="key-values">
              <dt>Identity</dt>
              <dd>
                <Status value="Verified" />
              </dd>
              <dt>Capability token</dt>
              <dd>{selected.token}</dd>
              <dt>Contract</dt>
              <dd>
                <code>{selected.contract}</code>
              </dd>
              <dt>Mission</dt>
              <dd>{selected.mission}</dd>
            </dl>
            <div className="subsection-title">Capabilities</div>
            <div className="capabilities">
              {selected.capabilities.map((capability) => (
                <code key={capability}>{capability}</code>
              ))}
            </div>
          </div>
          <div>
            <div className="subsection-title">Trust dimensions</div>
            <div className="overall-trust">
              <strong>{selected.trust}</strong>
              <div>
                <span>Overall trust</span>
                <Status value={selected.tier} />
              </div>
            </div>
            {Object.entries(selected.dimensions).map(([label, value]) => (
              <div className="dimension" key={label}>
                <div>
                  <span>{label}</span>
                  <b>{value}</b>
                </div>
                <div>
                  <span className={`progress-${value}`} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </aside>
      </div>
    </div>
  )
}

function IncidentView({ go }: { go: (view: View) => void }) {
  const timeline = replayEvents.slice(2, 8)
  return (
    <div className="page">
      <PageHeader
        eyebrow="Incidents / INC-2025-0042"
        title="Unauthorized data export attempt"
        description="Researcher-01 deviated from its active mission after consuming untrusted content."
      >
        <Button variant="secondary">
          <Icon name="copy" size={14} />
          Export evidence
        </Button>
        <Button variant="primary" onClick={() => go("replay")}>
          Open replay
        </Button>
      </PageHeader>
      <div className="incident-layout">
        <div>
          <section className="decision-summary">
            <div className="decision-top">
              <Status value="Critical" />
              <strong>Contained</strong>
              <span>Detected 10:31:06 UTC · contained in 19 ms</span>
            </div>
            <div className="decision-grid">
              <div>
                <span>Attempted action</span>
                <code>database.export("customers")</code>
              </div>
              <div>
                <span>Decision</span>
                <strong className="critical-text">Deny + quarantine</strong>
              </div>
              <div>
                <span>Reason code</span>
                <code>MISSION_VIOLATION</code>
              </div>
              <div>
                <span>Mission alignment</span>
                <strong>0.02 / 1.00</strong>
              </div>
              <div>
                <span>Policy version</span>
                <code>mission-integrity@v1.8</code>
              </div>
              <div>
                <span>Risk score</span>
                <strong>98 / 100</strong>
              </div>
            </div>
          </section>
          <section className="incident-timeline">
            <div className="section-heading">
              <div>
                <strong>Evidence timeline</strong>
                <span>Chronological reconstruction from signed events</span>
              </div>
            </div>
            {timeline.map((item, index) => (
              <div
                className={`timeline-row ${
                  index >= 2 && index <= 4 ? "alerting" : ""
                }`}
                key={item.time}
              >
                <code>{item.time}</code>
                <span className="timeline-marker" />
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.description}</p>
                  <small>
                    {item.agent} · {item.policy}
                  </small>
                </div>
              </div>
            ))}
          </section>
          <section className="policy-panel">
            <div className="section-heading">
              <div>
                <strong>Policy evaluation</strong>
                <span>Facts evaluated at sequence #18399</span>
              </div>
            </div>
            {[
              [
                "Identity and token",
                "Passed",
                "Ed25519 signature and session token valid",
              ],
              [
                "Mission contract",
                "Violation",
                "database.export explicitly forbidden",
              ],
              [
                "Current plan",
                "Violation",
                "Step 02 permits web.search and web.read only",
              ],
              [
                "Provenance",
                "Violation",
                "Action influenced by untrusted content",
              ],
              [
                "Behavior",
                "High risk",
                "New tool and abnormal argument pattern",
              ],
              ["OPA result", "Deny", "Block, revoke token, quarantine, alert"],
            ].map(([group, result, detail]) => (
              <div className="policy-row" key={group}>
                <strong>{group}</strong>
                <Status
                  value={
                    result === "Passed"
                      ? "Verified"
                      : result === "High risk"
                        ? "High"
                        : result === "Deny"
                          ? "Block"
                          : "Critical"
                  }
                />
                <span>{detail}</span>
                <Icon name="chevron" size={14} />
              </div>
            ))}
          </section>
        </div>
        <aside>
          <section className="response-panel">
            <div className="section-heading">
              <div>
                <strong>Response status</strong>
                <span>Automated containment complete</span>
              </div>
            </div>
            <div className="containment-state">
              <Icon name="shield" size={20} />
              <div>
                <strong>Threat contained</strong>
                <span>Workflow remains operational</span>
              </div>
            </div>
            {[
              "Action blocked",
              "Capability token revoked",
              "Agent quarantined",
              "Task reassigned to Planner-01",
            ].map((item, index) => (
              <div className="response-step" key={item}>
                <Icon name="check" size={14} />
                <span>{item}</span>
                <code>
                  10:31:0{index === 3 ? "7.102" : `6.9${21 + index * 10}`}
                </code>
              </div>
            ))}
            <div className="trust-impact">
              <span>Trust impact</span>
              <div>
                <strong>94</strong>
                <Icon name="chevron" />
                <strong className="critical-text">34</strong>
              </div>
              <small>Compliance −30 · Integrity −50</small>
            </div>
          </section>
          <section className="lineage-panel">
            <div className="section-heading">
              <div>
                <strong>Taint lineage</strong>
                <span>Recorded provenance path</span>
              </div>
            </div>
            {[
              "Untrusted web page",
              "Researcher-01",
              "database.export",
              "Blocked at PEP",
            ].map((item, index) => (
              <div className={index === 2 ? "danger-node" : ""} key={item}>
                <span>{index + 1}</span>
                <strong>{item}</strong>
                {index < 3 && <Icon name="chevron" size={14} />}
              </div>
            ))}
          </section>
        </aside>
      </div>
    </div>
  )
}

function ReplayView() {
  const [selected, setSelected] = useState(5)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState("1×")
  useEffect(() => {
    if (!playing) return
    const timer = window.setInterval(
      () =>
        setSelected((value) =>
          value >= replayEvents.length - 1 ? 0 : value + 1,
        ),
      speed === "2×" ? 600 : 1200,
    )
    return () => window.clearInterval(timer)
  }, [playing, speed])
  const item = replayEvents[selected]
  return (
    <div className="page replay-page">
      <PageHeader
        eyebrow="Sessions / SESS-001 / Replay"
        title="Forensic replay"
        description="Deterministic reconstruction using recorded state and policy versions."
      >
        <Status value="Verified" />
      </PageHeader>
      <div className="replay-layout">
        <section className="replay-events">
          <div className="section-heading">
            <div>
              <strong>Session events</strong>
              <span>{replayEvents.length} recorded events</span>
            </div>
          </div>
          {replayEvents.map((event, index) => (
            <Button
              key={event.time}
              className={`replay-row ${index === selected ? "selected" : ""}`}
              onClick={() => setSelected(index)}
            >
              <code>#{18395 + index}</code>
              <span>
                <strong>{event.title}</strong>
                <small>
                  {event.time} · {event.agent}
                </small>
              </span>
              {index >= 4 && index <= 6 && <span className="event-alert" />}
            </Button>
          ))}
        </section>
        <section className="replay-canvas">
          <div className="canvas-head">
            <span>
              State at <code>{item.time}</code>
            </span>
            <small>
              Event {selected + 1} of {replayEvents.length}
            </small>
          </div>
          <div className="agent-flow">
            <div className="flow-agent">
              <span>P</span>
              <strong>Planner-01</strong>
              <Status value="Active" />
            </div>
            <Icon name="chevron" />
            <div
              className={`flow-agent ${
                item.agent === "Researcher-01" ? "focused" : ""
              }`}
            >
              <span>R</span>
              <strong>Researcher-01</strong>
              <Status value={item.state} />
            </div>
            <Icon name="chevron" />
            <div className="flow-agent">
              <span>E</span>
              <strong>Executor-01</strong>
              <Status value="Active" />
            </div>
          </div>
          <div className="selected-event">
            <span>Selected event</span>
            <strong>{item.title}</strong>
            <p>{item.description}</p>
          </div>
          <div className="scrubber">
            <div>
              {replayEvents.map((_, index) => (
                <Button
                  key={index}
                  className={`${index <= selected ? "passed" : ""} ${
                    index === selected ? "current" : ""
                  }`}
                  title={`Go to event ${index + 1}`}
                  onClick={() => setSelected(index)}
                />
              ))}
            </div>
          </div>
          <div className="playback">
            <Button
              variant="secondary"
              onClick={() => setSelected(Math.max(0, selected - 1))}
            >
              Previous
            </Button>
            <Button
              variant="primary"
              className="play-button"
              onClick={() => setPlaying(!playing)}
            >
              <Icon name={playing ? "pause" : "play"} size={15} />
              {playing ? "Pause" : "Play"}
            </Button>
            <Button
              variant="secondary"
              onClick={() =>
                setSelected(Math.min(replayEvents.length - 1, selected + 1))
              }
            >
              Next
            </Button>
            <Select value={speed} onChange={setSpeed} label="Playback speed">
              <option>1×</option>
              <option>2×</option>
            </Select>
          </div>
        </section>
        <aside className="state-inspector">
          <div className="section-heading">
            <div>
              <strong>State inspector</strong>
              <span>Before and after event</span>
            </div>
          </div>
          <dl>
            <dt>Agent</dt>
            <dd>{item.agent}</dd>
            <dt>Agent state</dt>
            <dd>
              <Status value={item.state} />
            </dd>
            <dt>Trust score</dt>
            <dd className="state-change">
              <strong>{item.trustBefore}</strong>
              <Icon name="chevron" size={14} />
              <strong
                className={
                  item.trustAfter < item.trustBefore ? "critical-text" : ""
                }
              >
                {item.trustAfter}
              </strong>
            </dd>
            <dt>Plan step</dt>
            <dd>Step 02 · Research</dd>
            <dt>Policy version</dt>
            <dd>
              <code>{item.policy}</code>
            </dd>
            <dt>Re-evaluation</dt>
            <dd>
              <Status value="Verified" /> Matches recorded decision
            </dd>
          </dl>
          <Button variant="secondary" className="full-width">
            View signed event
          </Button>
        </aside>
      </div>
    </div>
  )
}

function LedgerView() {
  const [query, setQuery] = useState("")
  const [selected, setSelected] = useState<RuntimeEvent>(runtimeEvents[0])
  const [verifyStep, setVerifyStep] = useState(-1)
  const checks = [
    "Checking event hashes",
    "Checking chain continuity",
    "Verifying signatures",
    "Verifying Merkle roots",
    "Comparing blockchain anchor",
  ]
  useEffect(() => {
    if (verifyStep < 0 || verifyStep >= checks.length) return
    const timer = window.setTimeout(
      () => setVerifyStep((value) => value + 1),
      500,
    )
    return () => window.clearTimeout(timer)
  }, [verifyStep])
  const filtered = runtimeEvents.filter((event) =>
    `${event.seq} ${event.type} ${event.agent} ${event.hash}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  )
  const verifying = verifyStep >= 0 && verifyStep < checks.length
  const complete = verifyStep >= checks.length
  return (
    <div className="page">
      <PageHeader
        title="Audit ledger"
        description="Verify hash-chain continuity, signatures, Merkle proofs, and blockchain anchors."
      >
        <Button
          variant="primary"
          disabled={verifying}
          onClick={() => setVerifyStep(0)}
        >
          <Icon name={complete ? "check" : "shield"} size={15} />
          {verifying
            ? "Verifying…"
            : complete
              ? "Verified 18,402 events"
              : "Verify ledger"}
        </Button>
      </PageHeader>
      {(verifying || complete) && (
        <section
          className={`verification-progress ${complete ? "complete" : ""}`}
          aria-live="polite"
        >
          <div>
            <Icon name={complete ? "check" : "shield"} />
            <div>
              <strong>
                {complete ? "Ledger verification complete" : checks[verifyStep]}
              </strong>
              <span>
                {complete
                  ? "18,402 events verified in 2.5 seconds · No integrity violations found"
                  : `Step ${verifyStep + 1} of ${checks.length}`}
              </span>
            </div>
          </div>
          <div className="verify-track">
            <span className={`verify-step-${complete ? 5 : verifyStep + 1}`} />
          </div>
        </section>
      )}
      <section className="ledger-summary">
        <div>
          <span>Ledger status</span>
          <strong>
            <Status value="Verified" />
          </strong>
          <small>Through sequence #18402</small>
        </div>
        <div>
          <span>Hash chain</span>
          <strong>Continuous</strong>
          <small>18,402 linked events</small>
        </div>
        <div>
          <span>Current checkpoint</span>
          <strong>#184</strong>
          <small>Sequences 18,301–18,400</small>
        </div>
        <div>
          <span>Blockchain anchor</span>
          <strong>Confirmed</strong>
          <small>Sepolia · block 7,184,221</small>
        </div>
      </section>
      <div className="ledger-layout">
        <section className="ledger-main">
          <FilterBar
            query={query}
            setQuery={setQuery}
            extra={
              <Button variant="secondary">
                <Icon name="filter" size={14} />
                More filters
              </Button>
            }
          />
          <div className="data-table ledger-table">
            <div className="table-head">
              <span>Seq</span>
              <span>Timestamp</span>
              <span>Event type</span>
              <span>Agent</span>
              <span>Event hash</span>
              <span>Proof</span>
            </div>
            {filtered.map((event) => (
              <Button
                key={event.seq}
                className={`table-row ${
                  selected.seq === event.seq ? "selected" : ""
                }`}
                onClick={() => setSelected(event)}
              >
                <code>#{event.seq}</code>
                <code>{event.time}</code>
                <strong>{event.type}</strong>
                <span>{event.agent}</span>
                <code>{event.hash.slice(0, 12)}…</code>
                <Status value={event.signature} />
              </Button>
            ))}
          </div>
          <div className="table-footer">
            <span>Showing {filtered.length} of 18,402 events</span>
            <span>Checkpoint #184</span>
          </div>
        </section>
        <aside className="evidence-inspector">
          <div className="section-heading">
            <div>
              <strong>Cryptographic evidence</strong>
              <span>Sequence #{selected.seq}</span>
            </div>
          </div>
          {[
            ["Event hash", selected.hash],
            ["Previous hash", selected.previousHash],
            ["Content hash", "bc890c831721fd05c3e8"],
            ["Agent signature", "ed25519:7a8f42cd109b"],
            ["Core signature", "ed25519:901fc83b72da"],
            ["Merkle root", "0x9f840d1243ab8c49f2"],
          ].map(([label, value]) => (
            <div className="hash-row" key={label}>
              <span>{label}</span>
              <div>
                <code>{value}</code>
                <CopyButton value={value} />
              </div>
            </div>
          ))}
          <div className="proof-summary">
            <Icon name="link" size={16} />
            <div>
              <strong>Inclusion proof valid</strong>
              <span>Checkpoint #184 · Sepolia block 7,184,221</span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}

function ConfirmDialog({ close }: { close: () => void }) {
  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={close}>
      <div
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="dialog-icon">
          <Icon name="alert" />
        </div>
        <div id="dialog-title" className="dialog-title">
          Release Researcher-01?
        </div>
        <p>
          This restores an agent that was quarantined after a critical mission
          violation. A new capability token will be issued and the action will
          be recorded in the ledger.
        </p>
        <div className="dialog-note">
          <strong>Prerequisites required</strong>
          <span>
            Review incident INC-2025-0042 and confirm the mission contract
            before release.
          </span>
        </div>
        <div className="dialog-actions">
          <Button variant="secondary" onClick={close}>
            Cancel
          </Button>
          <Button variant="danger" onClick={close}>
            Confirm release
          </Button>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const [view, setView] = useState<View>("operations")
  const [dialog, setDialog] = useState(false)
  let content: ReactNode = <OperationsView go={setView} />
  if (view === "agents") content = <AgentsView setDialog={setDialog} />
  if (view === "incident") content = <IncidentView go={setView} />
  if (view === "replay") content = <ReplayView />
  if (view === "ledger") content = <LedgerView />
  return (
    <AppShell view={view} setView={setView}>
      {content}
      {dialog && <ConfirmDialog close={() => setDialog(false)} />}
    </AppShell>
  )
}
