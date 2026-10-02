-- AegisMesh Phase 1 Step 4 Migration: Mission Contracts
-- Target: Supabase / PostgreSQL

CREATE TABLE IF NOT EXISTS mission_contracts (
    id TEXT PRIMARY KEY,
    mission_id TEXT,
    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    allowed_tools JSONB NOT NULL DEFAULT '[]'::jsonb,
    forbidden_tools JSONB NOT NULL DEFAULT '[]'::jsonb,
    allowed_resources JSONB NOT NULL DEFAULT '[]'::jsonb,
    risk_level TEXT NOT NULL DEFAULT 'medium',
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Required Indexes for Mission Contracts
CREATE INDEX IF NOT EXISTS idx_contracts_agent_id ON mission_contracts(agent_id);
CREATE INDEX IF NOT EXISTS idx_contracts_mission_id ON mission_contracts(mission_id);
CREATE INDEX IF NOT EXISTS idx_contracts_enabled ON mission_contracts(enabled);
