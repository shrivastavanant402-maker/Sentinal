-- AegisMesh Initial Foundation Migration: Agents, Events, Alerts
-- Target: Supabase / PostgreSQL

-- 1. Agents Table
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active', -- active, paused, halted, quarantined
    trust_score DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    public_key TEXT,
    capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Events Table (Append-Only Evidence Ledger)
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    seq BIGSERIAL,
    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    session_id TEXT,
    event_type TEXT NOT NULL,
    action TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    decision JSONB DEFAULT '{}'::jsonb,
    previous_hash TEXT,
    content_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL,
    agent_signature TEXT,
    core_signature TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Required Indexes for Events
CREATE INDEX IF NOT EXISTS idx_events_agent_id ON events(agent_id);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_event_hash ON events(event_hash);
CREATE INDEX IF NOT EXISTS idx_events_seq ON events(seq);

-- 3. Alerts Table
CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    agent_id TEXT REFERENCES agents(id) ON DELETE SET NULL,
    event_id TEXT REFERENCES events(id) ON DELETE SET NULL,
    severity TEXT NOT NULL, -- low, medium, high, critical
    alert_type TEXT NOT NULL,
    message TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Required Indexes for Alerts
CREATE INDEX IF NOT EXISTS idx_alerts_agent_id ON alerts(agent_id);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at);

-- Prevent UPDATE/DELETE on events table to guarantee tamper-resistance
-- (Note: Can be enforced via Postgres Rule or Trigger)
CREATE OR REPLACE RULE no_update_events AS ON UPDATE TO events DO INSTEAD NOTHING;
CREATE OR REPLACE RULE no_delete_events AS ON DELETE TO events DO INSTEAD NOTHING;
