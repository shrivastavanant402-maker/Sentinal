export type View = "operations" | "agents" | "incident" | "replay" | "ledger"
export type Severity = "Critical" | "High" | "Medium" | "Low"
export type Decision = "Allow" | "Block" | "Require approval" | "Sandbox"
export type AgentStatus = "Active" | "Degraded" | "Halted" | "Quarantined" | "Offline"

export interface Agent {
  id: string
  name: string
  role: string
  status: AgentStatus
  trust: number
  tier: "Trusted" | "Watched" | "Restricted" | "Quarantined"
  mission: string
  step: string
  lastEvent: string
  contract: string
  token: string
  capabilities: string[]
  dimensions: Record<"Compliance" | "Integrity" | "Consistency" | "Claim accuracy", number>
}

export interface RuntimeEvent {
  seq: number
  time: string
  agent: string
  type: string
  resource: string
  decision: Decision
  severity: Severity
  latency: number
  reason: string
  hash: string
  previousHash: string
  signature: "Verified" | "Pending"
}

export interface ReplayEvent {
  time: string
  title: string
  description: string
  agent: string
  trustBefore: number
  trustAfter: number
  state: string
  policy: string
}
