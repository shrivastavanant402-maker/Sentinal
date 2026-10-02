import React, { useState } from 'react';
import { Agent, AttackScenarioType, AttackStatus, AttackResult } from '../types';
import { formatFullDateTimeIST } from '../utils/time';
import { simulateAttack } from '../services/api';
import { StatusBadge } from '../components/common/StatusBadge';
import { DecisionBadge } from '../components/common/DecisionBadge';
import { SeverityBadge } from '../components/common/SeverityBadge';
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
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileCheck,
  Shield,
  Activity,
  X,
} from 'lucide-react';

interface AttackLabProps {
  agents: Agent[];
  isLoading?: boolean;
  onRefresh?: () => void;
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
  onRefresh,
}) => {
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const [selectedScenario, setSelectedScenario] = useState<AttackScenarioType | ''>('');
  const [attackStatus, setAttackStatus] = useState<AttackStatus>('ready');
  const [attackResult, setAttackResult] = useState<AttackResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const selectedAgent = agents.find(a => a.id === selectedAgentId);
  const isLaunchReady =
    selectedAgentId !== '' &&
    selectedScenario !== '' &&
    attackStatus !== 'running';

  const handleLaunchAttack = async () => {
    if (!isLaunchReady || !selectedScenario || !selectedAgentId) return;

    // Transition to running state, clear previous results & errors
    setAttackStatus('running');
    setAttackResult(null);
    setErrorMessage(null);

    try {
      // Execute attack simulation via real backend security pipeline
      const response = await simulateAttack({
        agent_id: selectedAgentId,
        scenario: selectedScenario,
      });

      setAttackResult(response);
      setAttackStatus('completed');

      // Refresh SOC telemetry (events, alerts, agents)
      if (onRefresh) {
        onRefresh();
      }
    } catch (err: any) {
      setAttackStatus('failed');
      setErrorMessage(
        err.message || 'Attack simulation request failed. Please check backend connectivity.'
      );
      setAttackResult(null);
    }
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

      {/* Operator error banner */}
      {errorMessage && (
        <div className="p-3 rounded border border-rose-glow bg-rose-subtle text-rose flex items-center justify-between text-xs mb-4">
          <div className="flex items-center gap-2">
            <AlertTriangle size={16} />
            <span>
              <strong>Simulation Error:</strong> {errorMessage}
            </span>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-muted hover:text-white transition-colors"
            title="Dismiss error"
          >
            <X size={15} />
          </button>
        </div>
      )}

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
                    disabled={attackStatus === 'running'}
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
                      onClick={() => {
                        if (attackStatus !== 'running') {
                          setSelectedScenario(scenario.id);
                        }
                      }}
                      className={`scenario-card cursor-pointer ${isSelected ? 'scenario-card-active' : ''} ${attackStatus === 'running' ? 'opacity-60 cursor-not-allowed' : ''}`}
                    >
                      <div className="scenario-header">
                        <div className="flex items-center gap-2">
                          <input
                            type="radio"
                            name="attack_scenario"
                            checked={isSelected}
                            disabled={attackStatus === 'running'}
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
                {attackStatus === 'running' ? (
                  <>
                    <LoadingSpinner inline />
                    <span>EXECUTING ATTACK PIPELINE...</span>
                  </>
                ) : (
                  <>
                    <Play size={16} className={isLaunchReady ? 'text-white' : 'text-muted'} />
                    <span>LAUNCH ATTACK</span>
                    <ArrowRight size={14} className="ml-1" />
                  </>
                )}
              </button>

              {!isLaunchReady && attackStatus !== 'running' && (
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
                <LoadingSpinner label="Submitting attack vector to Policy Enforcement Point..." />
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
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div className="flex items-center gap-2">
                      <Clock size={14} className="text-cyan" />
                      <span className="font-mono text-xs font-semibold text-white">
                        SCENARIO: {attackResult.scenario.toUpperCase().replace('_', ' ')}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-muted">
                        Target: <strong className="text-white">{attackResult.target_agent_id || attackResult.agent_id}</strong>
                      </span>
                      <span className={`status-badge ${getStatusBadgeClass(attackStatus)} font-mono text-xs uppercase ml-2`}>
                        {attackStatus}
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-secondary mt-2">
                    {attackResult.message}
                  </p>
                </div>

                {/* Core Telemetry Grid */}
                <div className="result-sections-grid mt-4">
                  {/* 1. PEP Decision Box */}
                  <div className="result-box">
                    <span className="result-box-title">
                      <Shield size={12} className="inline mr-1 text-cyan" />
                      PEP Security Decision
                    </span>
                    <div className="flex items-center gap-3 mt-1">
                      <DecisionBadge
                        decision={{
                          decision: attackResult.decision,
                          allowed: attackResult.allowed,
                          status: attackResult.decision,
                        }}
                        size="md"
                      />
                      <div className="flex flex-col text-xs font-mono">
                        <span className="text-muted">Allowed:</span>
                        {attackResult.allowed ? (
                          <span className="flex items-center gap-1 text-emerald font-semibold">
                            <CheckCircle2 size={12} /> YES (Permitted)
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-rose font-semibold">
                            <XCircle size={12} /> NO (Blocked)
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* 2. Risk & Enforcement Outcome Box */}
                  <div className="result-box">
                    <span className="result-box-title">
                      <Activity size={12} className="inline mr-1 text-amber" />
                      Risk & Enforcement Outcome
                    </span>
                    <div className="flex items-center justify-between mt-1">
                      <div className="flex flex-col text-xs font-mono">
                        <span className="text-muted">Risk Level:</span>
                        <SeverityBadge severity={attackResult.risk_level} size="sm" />
                      </div>
                      <div className="flex flex-col text-xs font-mono text-right">
                        <span className="text-muted">Action/Tool:</span>
                        <span className="text-cyan font-semibold">{attackResult.action}</span>
                      </div>
                    </div>
                    <div className="text-xs font-mono text-secondary mt-2 pt-1 border-t border-white/5">
                      <span className="text-muted">Outcome: </span>
                      <span className="text-white font-semibold">{attackResult.enforcement_outcome}</span>
                    </div>
                  </div>

                  {/* 3. Decision Rationale Box */}
                  <div className="result-box col-span-2">
                    <span className="result-box-title">
                      <Terminal size={12} className="inline mr-1 text-indigo" />
                      Policy Rationale & Rule Assessment
                    </span>
                    <div className="font-mono text-xs text-secondary mt-1">
                      <span className="text-muted">Reason: </span>
                      <span className="soc-badge font-mono text-xs ml-1 text-white">
                        {attackResult.reason}
                      </span>
                    </div>
                    {attackResult.details && Object.keys(attackResult.details).length > 0 && (
                      <div className="text-xs text-muted font-mono mt-2 p-2 rounded bg-black/30 border border-white/5 overflow-x-auto">
                        <pre className="text-muted text-xs leading-relaxed whitespace-pre-wrap">
                          {JSON.stringify(attackResult.details, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>

                  {/* 4. Triggered Alert Box */}
                  <div className="result-box col-span-2">
                    <span className="result-box-title">
                      <ShieldAlert size={12} className="inline mr-1 text-rose" />
                      Generated Security Alert
                    </span>
                    {attackResult.alert ? (
                      <div className="alert-result-card p-3 rounded border border-rose/30 bg-rose-subtle mt-1 flex flex-col gap-1">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <span className="font-mono text-xs font-semibold text-white">
                            {attackResult.alert.alert_type}
                          </span>
                          <SeverityBadge severity={attackResult.alert.severity} size="sm" />
                        </div>
                        <p className="text-xs text-white/90 mt-1">
                          {attackResult.alert.message}
                        </p>
                        <div className="flex items-center justify-between text-xs text-muted font-mono mt-2 pt-2 border-t border-white/5">
                          <span>Alert ID: {attackResult.alert.id}</span>
                          <span>Linked Event: {attackResult.alert.event_id || '—'}</span>
                        </div>
                      </div>
                    ) : (
                      <div className="p-3 rounded border border-border-color bg-bg-secondary/40 text-xs text-muted font-mono flex items-center gap-2 mt-1">
                        <Info size={14} className="text-muted" />
                        <span>No alert generated</span>
                      </div>
                    )}
                  </div>

                  {/* 5. Trust Score Delta Box */}
                  <div className="result-box">
                    <span className="result-box-title">
                      <Info size={12} className="inline mr-1 text-emerald" />
                      Trust Score Telemetry
                    </span>
                    <div className="font-mono text-xs text-secondary mt-1">
                      {attackResult.trust_delta !== null && attackResult.trust_delta !== undefined ? (
                        <span>
                          Trust change: {attackResult.trust_delta > 0 ? `+${attackResult.trust_delta}` : attackResult.trust_delta}
                        </span>
                      ) : (
                        <span className="text-muted italic">
                          Trust change: Not reported by backend
                        </span>
                      )}
                    </div>
                  </div>

                  {/* 6. Cryptographic Evidence Ledger Box */}
                  <div className="result-box">
                    <span className="result-box-title">
                      <FileCheck size={12} className="inline mr-1 text-emerald" />
                      Ledger Event Reference
                    </span>
                    <div className="font-mono text-xs text-secondary mt-1 flex flex-col gap-1">
                      <div>
                        <span className="text-muted">Event ID: </span>
                        {attackResult.event_id ? (
                          <span className="text-emerald font-semibold break-all">
                            {attackResult.event_id}
                          </span>
                        ) : (
                          <span className="text-muted italic">Not recorded</span>
                        )}
                      </div>
                      <div className="text-xs text-muted">
                        Evidence logged with SHA-256 hash chaining
                      </div>
                    </div>
                  </div>
                </div>

                {/* Footer bar */}
                <div className="attack-result-footer mt-4 pt-3 border-t border-border-color flex items-center justify-between text-xs text-muted font-mono">
                  <span>Timestamp: {attackResult.timestamp ? formatFullDateTimeIST(attackResult.timestamp) : '—'}</span>
                  <span className="text-emerald flex items-center gap-1">
                    <FileCheck size={13} /> IMMUTABLE EVIDENCE RECORDED
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
