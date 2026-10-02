import {
  Agent,
  AgentStatus,
  EventLog,
  Alert,
  LedgerReport,
  HealthStatus,
  AttackSimulateRequest,
  AttackSimulateResponse,
} from '../types';

const API_BASE = '';

async function handleResponse<T>(res: Response, fallbackError: string): Promise<T> {
  if (!res.ok) {
    let errorDetail = fallbackError;
    try {
      const errorJson = await res.json();
      errorDetail = errorJson.detail || errorJson.message || fallbackError;
    } catch {
      errorDetail = `${fallbackError} (${res.status} ${res.statusText})`;
    }
    throw new Error(errorDetail);
  }
  return await res.json();
}

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`);
  return handleResponse<HealthStatus>(res, 'Health check failed');
}

export async function fetchAgents(): Promise<Agent[]> {
  const res = await fetch(`${API_BASE}/agents`);
  return handleResponse<Agent[]>(res, 'Failed to fetch agents');
}

export async function fetchAgent(agentId: string): Promise<Agent> {
  const res = await fetch(`${API_BASE}/agents/${encodeURIComponent(agentId)}`);
  return handleResponse<Agent>(res, `Failed to fetch agent ${agentId}`);
}

export async function updateAgentStatus(agentId: string, status: AgentStatus): Promise<Agent> {
  const res = await fetch(`${API_BASE}/agents/${encodeURIComponent(agentId)}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
  return handleResponse<Agent>(res, `Failed to update status for agent ${agentId}`);
}

export async function fetchEvents(limit = 100, offset = 0): Promise<EventLog[]> {
  const res = await fetch(`${API_BASE}/events?limit=${limit}&offset=${offset}`);
  return handleResponse<EventLog[]>(res, 'Failed to fetch events');
}

export async function fetchEvent(eventId: string): Promise<EventLog> {
  const res = await fetch(`${API_BASE}/events/${encodeURIComponent(eventId)}`);
  return handleResponse<EventLog>(res, `Failed to fetch event ${eventId}`);
}

export async function emitEvent(eventData: Partial<EventLog>): Promise<EventLog> {
  const res = await fetch(`${API_BASE}/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(eventData),
  });
  return handleResponse<EventLog>(res, 'Failed to emit event');
}

export async function fetchAlerts(limit = 100): Promise<Alert[]> {
  const res = await fetch(`${API_BASE}/alerts?limit=${limit}`);
  return handleResponse<Alert[]>(res, 'Failed to fetch alerts');
}

export async function createAlert(alertData: Partial<Alert>): Promise<Alert> {
  const res = await fetch(`${API_BASE}/alerts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(alertData),
  });
  return handleResponse<Alert>(res, 'Failed to create alert');
}

export async function verifyLedger(): Promise<LedgerReport> {
  const res = await fetch(`${API_BASE}/ledger/verify`);
  return handleResponse<LedgerReport>(res, 'Ledger verification failed');
}

export async function simulateAttack(request: AttackSimulateRequest): Promise<AttackSimulateResponse> {
  const res = await fetch(`${API_BASE}/attacks/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  return handleResponse<AttackSimulateResponse>(res, 'Attack simulation failed');
}

