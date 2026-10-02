export type AgentStatus = 'active' | 'paused' | 'halted' | 'quarantined';

export interface Agent {
  id: string;
  name: string;
  role: string;
  status: AgentStatus;
  trust_score: number;
  public_key?: string | null;
  capabilities: string[];
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export type EventType =
  | 'agent_registered'
  | 'plan_declared'
  | 'tool_call_request'
  | 'tool_call_response'
  | 'status_changed'
  | 'alert_triggered'
  | string;

export interface EventDecision {
  decision?: string;
  allowed?: boolean;
  action?: string;
  risk_level?: 'low' | 'medium' | 'high' | 'critical' | string;
  risk_score?: number;
  reason?: string;
  evaluated_by?: string;
  [key: string]: any;
}

export interface EventLog {
  id: string;
  seq: number;
  timestamp: string;
  agent_id: string;
  session_id?: string | null;
  event_type: EventType;
  action: string;
  payload: Record<string, any>;
  decision: EventDecision;
  previous_hash: string;
  content_hash: string;
  event_hash: string;
  agent_signature?: string | null;
  core_signature?: string | null;
  created_at: string;
}

export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';

export interface Alert {
  id: string;
  agent_id?: string | null;
  event_id?: string | null;
  severity: AlertSeverity;
  alert_type: string;
  message: string;
  details: Record<string, any>;
  created_at: string;
}

export interface LedgerReport {
  ok: boolean;
  checked: number;
  chain_valid: boolean;
  errors: string[];
}

export interface HealthStatus {
  status: string;
  timestamp?: string;
  version?: string;
  database?: string;
  [key: string]: any;
}

export interface DashboardMetrics {
  totalAgents: number;
  activeAgents: number;
  quarantinedAgents: number;
  totalEvents: number;
  totalAlerts: number;
  criticalAlerts: number;
  blockedActions: number;
}

export type AttackScenarioType = 'prompt_injection' | 'secret_exfiltration' | 'rogue_agent';

export type AttackStatus = 'ready' | 'running' | 'completed' | 'failed';

export interface AttackSimulateRequest {
  agent_id: string;
  scenario: AttackScenarioType;
}

export interface AttackSimulateResponse {
  scenario: AttackScenarioType;
  agent_id: string;
  target_agent_id?: string | null;
  status: string;
  decision: string;
  allowed: boolean;
  reason: string;
  risk_level: AlertSeverity;
  enforcement_outcome: string;
  action: string;
  event_id?: string | null;
  alert?: Alert | null;
  details?: Record<string, any>;
  trust_delta?: number | null;
  message: string;
  timestamp: string;
}

export interface AttackResult extends AttackSimulateResponse {
  error?: string | null;
}

export interface AttackReplayLedgerInfo {
  seq: number;
  previous_hash: string;
  content_hash: string;
  event_hash: string;
  chain_valid?: boolean | null;
}

export interface AttackReplayResponse {
  event_id: string;
  agent_id: string;
  event_type: string;
  action: string;
  decision?: string | null;
  allowed?: boolean | null;
  reason?: string | null;
  risk_level?: AlertSeverity | string | null;
  enforcement_outcome?: string | null;
  resulting_agent_status?: string | null;
  timestamp: string;
  payload: Record<string, any>;
  details: Record<string, any>;
  alert?: Alert | null;
  ledger: AttackReplayLedgerInfo;
}


