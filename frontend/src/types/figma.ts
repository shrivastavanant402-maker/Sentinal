export type View = "operations" | "agents" | "incident" | "replay" | "ledger" | "attack_lab" | "ide";
export type FigmaSeverity = "Critical" | "High" | "Medium" | "Low";
export type FigmaDecision = "Allow" | "Block" | "Require approval" | "Sandbox" | "Quarantine";
export type FigmaAgentStatus = "Active" | "Degraded" | "Halted" | "Quarantined" | "Offline";

export interface FigmaAgent {
  id: string;
  name: string;
  role: string;
  status: FigmaAgentStatus;
  trust: number;
  tier: "Trusted" | "Watched" | "Restricted" | "Quarantined";
  mission: string;
  step: string;
  lastEvent: string;
  contract: string;
  token: string;
  capabilities: string[];
  dimensions: Record<"Compliance" | "Integrity" | "Consistency" | "Claim accuracy", number>;
}

export interface RuntimeEvent {
  id?: string;
  seq: number;
  time: string;
  timestamp?: string;
  agent: string;
  type: string;
  resource: string;
  decision: FigmaDecision;
  severity: FigmaSeverity;
  latency: number;
  reason: string;
  hash: string;
  previousHash: string;
  signature: "Verified" | "Pending";
}

export interface ReplayEvent {
  time: string;
  title: string;
  description: string;
  agent: string;
  trustBefore: number;
  trustAfter: number;
  state: string;
  policy: string;
}
