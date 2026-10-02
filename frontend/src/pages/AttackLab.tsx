import React, { useState } from 'react';
import { Agent, AttackScenarioType, AttackStatus, AttackResult } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { EmptyState } from '../components/common/EmptyState';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import {
  FlaskConical,
  Play,
  Terminal,
  ShieldAlert,
  Flame,
  KeyRound,
  UserX,
  Clock,
  Info,
  Layers,
  ArrowRight,
} from 'lucide-react';

interface AttackLabProps {
  agents: Agent[];
  isLoading?: boolean;
}

interface ScenarioConfig {
  id: AttackScenarioType;
  title: string;
  tagline: string;
  description: string;
  icon: React.ReactNode;
  targetRoleHint: string;
  threatLevel: 'HIGH' | 'CRITICAL';
}

const ATTACK_SCENARIOS: ScenarioConfig[] = [
  {
    id: 'prompt_injection',
    title: 'Prompt Injection',
    tagline: 'Adversarial instruction override via untrusted retrieval content',
    description:
      'Injects adversarial system instructions into retrieved web documents or tools to attempt hijacking the agent objective.',
    icon: <Flame size={18} className="text-amber" />,
    targetRoleHint: 'Recommended for Researcher or Planner',
    threatLevel: 'HIGH',
  },
  {
    id: 'secret_exfiltration',
    title: 'Secret Exfiltration',
    tagline: 'Unauthorized credential harvesting & egress transfer',
    description:
      'Simulates an agent attempting to read environment secrets, API tokens, or credentials and transmit them to an external endpoint.',
    icon: <KeyRound size={18} className="text-rose" />,
    targetRoleHint: 'Recommended for Executor or Researcher',
    threatLevel: 'CRITICAL',
  },
  {
    id: 'rogue_agent',
    title: 'Rogue Agent',
    tagline: 'Capability contract violation & unauthorized tool execution',
    description:
      'Forces an agent to execute raw system commands or socket connections outside its registered mission contract capabilities.',
    icon: <UserX size={18} className="text-rose" />,
    targetRoleHint: 'Recommended for any agent',
    threatLevel: 'CRITICAL',
  },
];

export const AttackLab: React.FC<AttackLabProps> = ({
  agents,
  isLoading = false,
}) => {
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const [selectedScenario, setSelectedScenario] = useState<AttackScenarioType | ''>('');
  const [attackStatus, setAttackStatus] = useState<AttackStatus>('ready');
  const [attackResult, setAttackResult] = useState<AttackResult | null>(null);

  const selectedAgent = agents.find(a => a.id === selectedAgentId);
  const isLaunchReady = selectedAgentId !== '' && selectedScenario !== '' && attackStatus !== 'running';

  const handleLaunchAttack = () => {
    if (!isLaunchReady || !selectedScenario) return;

    // Operator triggers assessment setup.
    // In this foundation phase, we transition status to 'ready' and initialize the result structure.
    // Real backend attack trigger will connect to the backend pipeline in the next step.
    setAttackStatus('ready');
    setAttackResult({
      scenario: selectedScenario,
      target_agent_id: selectedAgentId,
      status: 'ready',
      message: `Attack scenario prepared for ${selectedAgentId}. Backend execution pipeline will execute this test vector.`,
      timestamp: new Date().toISOString(),
    });
  };

  const getStatusBadgeClass = (status: AttackStatus) => {
    switch (status) {
      case 'running':
        return 'status-badge-running';
      case 'completed':
        return 'status-badge-completed';
      case 'failed':
        return 'status-badge-failed';
      case 'ready':
      default:
        return 'status-badge-ready';
    }
  };

  return (
    <div className="attack-lab-flow">
      {/* Header bar */}
      <div className="page-header glass-card">
        <div className="page-title-group">
          <div className="panel-icon-box bg-rose-glow">
            <FlaskConical size={22} className="text-rose" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="page-title">Attack Lab</h2>
              <span className="soc-badge font-mono text-xs">ADVERSARIAL SIMULATOR</span>
            </div>
            <p className="page-subtitle">
              Verify runtime security defenses, policy enforcement points, and quarantine mechanisms under active compromise
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-muted font-mono">STATUS:</span>
          <span className={`status-badge ${getStatusBadgeClass(attackStatus)} font-mono text-xs uppercase`}>
            {attackStatus}
          </span>
        </div>
      </div>

      {/* Main configuration grid */}
      <div className="attack-lab-grid">
        {/* Left Column: Target Agent & Attack Scenario Selection */}
        <div className="attack-config-panel glass-card">
          <div className="panel-header">
            <div className="panel-title-group">
              <Terminal size={17} className="text-indigo" />
              <div>
                <h3 className="panel-title text-sm">Simulation Configuration</h3>
                <p className="panel-subtitle">Select the target autonomous agent and attack vector</p>
              </div>
            </div>
          </div>

          <div className="panel-body flex flex-col gap-5">
            {/* 1. Target Agent Selector */}
            <div className="config-section">
              <label className="config-label flex items-center justify-between">
                <span>1. Target Agent</span>
                <span className="text-xs text-muted font-mono">
                  {agents.length} Monitored Agents
                </span>
              </label>

              {isLoading && agents.length === 0 ? (
                <LoadingSpinner label="Loading active agents from registry..." inline />
              ) : agents.length === 0 ? (
                <div className="p-3 border border-border-color rounded bg-bg-secondary text-xs text-muted">
                  No agents available. Ensure the backend runtime is active.
                </div>
              ) : (
                <div className="flex flex-col gap-2">
                  <select
                    value={selectedAgentId}
                    onChange={e => setSelectedAgentId(e.target.value)}
                    className="agent-select-input font-mono text-sm"
                  >
                    <option value="">-- Choose Target Agent --</option>
                    {agents.map(ag => (
                      <option key={ag.id} value={ag.id}>
                        {ag.name} ({ag.id} • {ag.role.toUpperCase()} • Trust: {ag.trust_score.toFixed(0)})
                      </option>
                    ))}
                  </select>

                  {selectedAgent && (
                    <div className="agent-selection-summary">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-semibold text-white">
                          {selectedAgent.name}
                        </span>
                        <StatusBadge status={selectedAgent.status} size="sm" />
                      </div>
                      <div className="flex items-center gap-3 text-xs text-secondary mt-1 font-mono">
                        <span>Role: <strong className="text-cyan">{selectedAgent.role}</strong></span>
                        <span>Trust: <strong className="text-emerald">{selectedAgent.trust_score.toFixed(1)}/100</strong></span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* 2. Attack Scenario Selector */}
            <div className="config-section">
              <label className="config-label">
                <span>2. Attack Scenario</span>
              </label>

              <div className="scenario-radio-group">
                {ATTACK_SCENARIOS.map(scenario => {
                  const isSelected = selectedScenario === scenario.id;

                  return (
                    <div
                      key={scenario.id}
                      onClick={() => setSelectedScenario(scenario.id)}
                      className={`scenario-card cursor-pointer ${isSelected ? 'scenario-card-active' : ''}`}
                    >
                      <div className="scenario-header">
                        <div className="flex items-center gap-2">
                          <input
                            type="radio"
                            name="attack_scenario"
                            checked={isSelected}
                            onChange={() => setSelectedScenario(scenario.id)}
                            className="scenario-radio"
                          />
                          <span className="scenario-title font-semibold text-sm text-white">
                            {scenario.title}
                          </span>
                        </div>
                        <span className={`threat-badge threat-${scenario.threatLevel.toLowerCase()} font-mono text-xs`}>
                          {scenario.threatLevel}
                        </span>
                      </div>

                      <p className="scenario-tagline text-xs text-secondary mt-1">
                        {scenario.tagline}
                      </p>

                      <div className="scenario-footer mt-2 flex items-center justify-between text-xs text-muted">
                        <span className="font-mono">{scenario.targetRoleHint}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 3. Launch Action */}
            <div className="config-section pt-2">
              <button
                onClick={handleLaunchAttack}
                disabled={!isLaunchReady}
                className={`btn btn-launch-attack w-full ${isLaunchReady ? 'btn-launch-ready' : 'btn-launch-disabled'}`}
              >
                <Play size={16} className={isLaunchReady ? 'text-white' : 'text-muted'} />
                <span>LAUNCH ATTACK</span>
                <ArrowRight size={14} className="ml-1" />
              </button>

              {!isLaunchReady && (
                <p className="text-xs text-muted text-center mt-2 font-mono">
                  Select both an agent and an attack scenario to enable launch
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Attack Status & Attack Result Panel */}
        <div className="attack-results-panel glass-card">
          <div className="panel-header">
            <div className="panel-title-group">
              <Layers size={17} className="text-cyan" />
              <div>
                <h3 className="panel-title text-sm">Attack Result & Telemetry</h3>
                <p className="panel-subtitle">Observability output, PEP decisions, and enforcement verification</p>
              </div>
            </div>

            <span className="font-mono text-xs text-muted">
              AUDIT TRAIL
            </span>
          </div>

          <div className="panel-body">
            {attackStatus === 'running' ? (
              <div className="p-8">
                <LoadingSpinner label="Executing attack scenario through security pipeline..." />
              </div>
            ) : !attackResult ? (
              <EmptyState
                icon={FlaskConical}
                title="No Attack Executed"
                description="Select a target agent and attack vector from the configuration panel, then click Launch Attack. Real backend events, PEP decisions, alerts, trust updates, and enforcement outcomes will appear here."
              />
            ) : (
              <div className="attack-result-content">
                {/* Result Status Banner */}
                <div className="result-status-banner">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Clock size={14} className="text-cyan" />
                      <span className="font-mono text-xs font-semibold text-white">
                        SCENARIO: {attackResult.scenario.toUpperCase()}
                      </span>
                    </div>
                    <span className="font-mono text-xs text-muted">
                      Target: <strong className="text-white">{attackResult.target_agent_id}</strong>
                    </span>
                  </div>

                  <p className="text-xs text-secondary mt-2">
                    {attackResult.message}
                  </p>
                </div>

                {/* Prepared Outcome Fields */}
                <div className="result-sections-grid mt-4">
                  {/* Event & Decision Box */}
                  <div className="result-box">
                    <span className="result-box-title">
                      <Terminal size={12} className="inline mr-1 text-cyan" />
                      Ledger Event & PEP Decision
                    </span>
                    {attackResult.decision ? (
                      <div className="font-mono text-xs text-secondary">
                        Decision: {JSON.stringify(attackResult.decision)}
                      </div>
                    ) : (
                      <div className="text-xs text-muted italic font-mono">
                        Awaiting backend PEP evaluation...
                      </div>
                    )}
                  </div>

                  {/* Security Alert Box */}
                  <div className="result-box">
                    <span className="result-box-title">
                      <ShieldAlert size={12} className="inline mr-1 text-amber" />
                      Triggered Alerts
                    </span>
                    {attackResult.alert ? (
                      <div className="font-mono text-xs text-secondary">
                        Alert: {attackResult.alert.message}
                      </div>
                    ) : (
                      <div className="text-xs text-muted italic font-mono">
                        No alert emitted yet
                      </div>
                    )}
                  </div>

                  {/* Trust Score Delta Box */}
                  <div className="result-box">
                    <span className="result-box-title">
                      <Info size={12} className="inline mr-1 text-indigo" />
                      Trust Score Delta
                    </span>
                    {attackResult.trust_change ? (
                      <div className="font-mono text-xs text-secondary">
                        {attackResult.trust_change.previous_score} → {attackResult.trust_change.new_score}
                      </div>
                    ) : (
                      <div className="text-xs text-muted italic font-mono">
                        Baseline trust score maintained
                      </div>
                    )}
                  </div>

                  {/* Enforcement Outcome Box */}
                  <div className="result-box">
                    <span className="result-box-title">
                      <ShieldAlert size={12} className="inline mr-1 text-rose" />
                      Enforcement Controller Action
                    </span>
                    {attackResult.enforcement ? (
                      <div className="font-mono text-xs text-secondary">
                        Action: {attackResult.enforcement.action} ({attackResult.enforcement.decision})
                      </div>
                    ) : (
                      <div className="text-xs text-muted italic font-mono">
                        Zero enforcement action pending
                      </div>
                    )}
                  </div>
                </div>

                <div className="attack-result-footer mt-4 pt-3 border-t border-border-color flex items-center justify-between text-xs text-muted font-mono">
                  <span>Timestamp: {attackResult.timestamp ? new Date(attackResult.timestamp).toLocaleTimeString() : '—'}</span>
                  <span>IMMUTABLE EVIDENCE LOGGED</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
