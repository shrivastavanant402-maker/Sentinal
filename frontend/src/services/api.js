const API_BASE = '';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return await res.json();
}

export async function fetchAgents() {
  const res = await fetch(`${API_BASE}/agents`);
  if (!res.ok) throw new Error(`Failed to fetch agents: ${res.statusText}`);
  return await res.json();
}

export async function registerAgent(agentData) {
  const res = await fetch(`${API_BASE}/agents/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(agentData),
  });
  if (!res.ok) throw new Error(`Registration failed: ${res.statusText}`);
  return await res.json();
}

export async function fetchEvents(limit = 100, offset = 0) {
  const res = await fetch(`${API_BASE}/events?limit=${limit}&offset=${offset}`);
  if (!res.ok) throw new Error(`Failed to fetch events: ${res.statusText}`);
  return await res.json();
}

export async function emitEvent(eventData) {
  const res = await fetch(`${API_BASE}/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(eventData),
  });
  if (!res.ok) throw new Error(`Failed to emit event: ${res.statusText}`);
  return await res.json();
}

export async function verifyLedger() {
  const res = await fetch(`${API_BASE}/ledger/verify`);
  if (!res.ok) throw new Error(`Ledger verification failed: ${res.statusText}`);
  return await res.json();
}
