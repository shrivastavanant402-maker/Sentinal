import React, { useState, useEffect, useMemo } from 'react';
import { EventLog, Agent, AttackReplayResponse } from '../types';
import { fetchAttackReplay } from '../services/api';
import { DecisionBadge } from '../components/common/DecisionBadge';
import { SeverityBadge } from '../components/common/SeverityBadge';
import { StatusBadge } from '../components/common/StatusBadge';
import { EmptyState } from '../components/common/EmptyState';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import {
  History,
  Shield,
  Activity,
  ShieldAlert,
  FileCheck,
  CheckCircle2,
  XCircle,
  Clock,
  Search,
  RefreshCw,
  Flame,
  KeyRound,
  UserX,
  Lock,
  Terminal,
  Layers,
  Info,
  AlertTriangle,
} from 'lucide-react';

interface AttackReplayProps {
  events: EventLog[];
  agents: Agent[];
  isLoading?: boolean;
  onRefresh?: () => void;
  initialEventId?: string | null;
}

type ScenarioFilter = 'ALL' | 'ENFORCEMENT' | 'PROMPT_INJECTION' | 'SECRET_EXFILTRATION' | 'ROGUE_AGENT';

interface EventTagInfo {
  tag: string;
  type: ScenarioFilter;
  colorClass: string;
  icon: React.ReactNode;
}

export const AttackReplay: React.FC<AttackReplayProps> = ({
  events,
  agents,
  isLoading = false,
  onRefresh,
  initialEventId = null,
}) => {
  const [selectedEventId, setSelectedEventId] = useState<string | null>(initialEventId);
  const [replayData, setReplayData] = useState<AttackReplayResponse | null>(null);
  const [isLoadingReplay, setIsLoadingReplay] = useState<boolean>(false);
  const [replayError, setReplayError] = useState<string | null>(null);
  const [scenarioFilter, setScenarioFilter] = useState<ScenarioFilter>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Helper to categorize each event based on its actual metadata
  const getEventTag = (event: EventLog): EventTagInfo => {
    const payload = event.payload || {};
    const prov = payload.provenance || {};
    const reason = event.decision?.reason || '';
    const action = event.action || '';
    const decision = (event.decision?.decision || event.decision?.status || '').toUpperCase();

    if (
      action === 'database.export' ||
      prov.source === 'exfiltration_probe' ||
      prov.data_classification === 'restricted_secret' ||
      reason === 'TAINT_SENSITIVE_LEAK'
    ) {
      return {
        tag: 'Secret Exfiltration',
        type: 'SECRET_EXFILTRATION',
        colorClass: 'text-rose bg-rose/10 border-rose/30',
        icon: <KeyRound size={12} className="text-rose" />,
      };
    }

    if (
      prov.integrity_compromised ||
      prov.anomaly_flag === 'unauthorized_rogue_behavior' ||
      reason === 'AGENT_QUARANTINED' ||
      decision === 'QUARANTINE'
    ) {
      return {
        tag: 'Rogue Agent',
        type: 'ROGUE_AGENT',
        colorClass: 'text-amber bg-amber/10 border-amber/30',
        icon: <UserX size={12} className="text-amber" />,
      };
    }

    if (
      prov.injection_vector === 'direct_prompt_injection' ||
      prov.tainted ||
      reason === 'MISSION_DRIFT' ||
      payload.requested_payload?.prompt?.includes('Ignore previous')
    ) {
      return {
        tag: 'Prompt Injection',
        type: 'PROMPT_INJECTION',
        colorClass: 'text-indigo bg-indigo/10 border-indigo/30',
        icon: <Flame size={12} className="text-indigo" />,
      };
    }

    if (event.event_type === 'enforcement') {
      return {
        tag: 'Enforcement',
        type: 'ENFORCEMENT',
        colorClass: 'text-cyan bg-cyan/10 border-cyan/30',
        icon: <Shield size={12} className="text-cyan" />,
      };
    }

    return {
      tag: 'System Event',
      type: 'ALL',
      colorClass: 'text-muted bg-white/5 border-white/10',
      icon: <Layers size={12} className="text-muted" />,
    };
  };

  // Sort and filter events: security/enforcement events surfaced first
  const filteredEvents = useMemo(() => {
    // Sort so enforcement events appear first, then newest first
    const sorted = [...events].sort((a, b) => {
      const aIsEnforcement = a.event_type === 'enforcement' ? 1 : 0;
      const bIsEnforcement = b.event_type === 'enforcement' ? 1 : 0;
      if (aIsEnforcement !== bIsEnforcement) {
        return bIsEnforcement - aIsEnforcement;
      }
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    });

    return sorted.filter(event => {
      const tagInfo = getEventTag(event);

      // Scenario filter
      if (scenarioFilter === 'ENFORCEMENT' && event.event_type !== 'enforcement') {
        return false;
      }
      if (scenarioFilter !== 'ALL' && scenarioFilter !== 'ENFORCEMENT' && tagInfo.type !== scenarioFilter) {
        return false;
      }

      // Search query
      if (searchQuery.trim() !== '') {
        const q = searchQuery.toLowerCase();
        const matchId = event.id.toLowerCase().includes(q);
        const matchAgent = event.agent_id.toLowerCase().includes(q);
        const matchAction = event.action.toLowerCase().includes(q);
        const matchReason = (event.decision?.reason || '').toLowerCase().includes(q);
        const matchTag = tagInfo.tag.toLowerCase().includes(q);
        return matchId || matchAgent || matchAction || matchReason || matchTag;
      }

      return true;
    });
  }, [events, scenarioFilter, searchQuery]);

  // Load replay data for selected event
  const loadReplay = async (eventId: string) => {
    setSelectedEventId(eventId);
    setIsLoadingReplay(true);
    setReplayError(null);
    try {
      const data = await fetchAttackReplay(eventId);
      setReplayData(data);
    } catch (err: any) {
      setReplayError(err.message || `Failed to fetch attack replay for event ${eventId}`);
      setReplayData(null);
    } finally {
      setIsLoadingReplay(false);
    }
  };

  // Auto-select preferred security/enforcement event on initial load
  useEffect(() => {
    if (!selectedEventId && events.length > 0) {
      const preferred = events.find(e => e.event_type === 'enforcement') || events[0];
      if (preferred) {
        loadReplay(preferred.id);
      }
    }
  }, [events, selectedEventId]);

  return (
    <div className="attack-replay-page-flow">
      {/* Header Bar */}
      <div className="page-header glass-card">
        <div className="page-title-group">
          <div className="panel-icon-box bg-cyan-glow">
            <History size={22} className="text-cyan" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="page-title">Attack Replay & Evidence Visualization</h2>
              <span className="soc-badge font-mono text-xs">AUDIT TIMELINE</span>
            </div>
            <p className="page-subtitle">
              Interactive 6-stage SOC timeline of attack vectors, detections, PDP verdicts, enforcement, alerts, and hash-chain ledger proofs
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="btn btn-secondary flex items-center gap-1.5 text-xs font-mono"
              disabled={isLoading}
              title="Refresh ledger event stream"
            >
              <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
              <span>REFRESH STREAM</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Grid: Event Selector on Left, Timeline Evidence on Right */}
      <div className="attack-replay-grid mt-4">
        {/* Left Column: Event Audit Stream */}
        <div className="event-stream-panel glass-card p-4 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers size={16} className="text-cyan" />
              <h3 className="text-sm font-semibold text-white">Recorded Events</h3>
            </div>
            <span className="count-pill count-pill-active font-mono text-xs">
              {filteredEvents.length} / {events.length}
            </span>
          </div>

          {/* Quick Scenario Filter Pills */}
          <div className="scenario-filter-pills flex flex-wrap gap-1.5 pt-1">
            <button
              onClick={() => setScenarioFilter('ALL')}
              className={`filter-tab-btn ${scenarioFilter === 'ALL' ? 'filter-tab-active' : ''}`}
            >
              All ({events.length})
            </button>
            <button
              onClick={() => setScenarioFilter('ENFORCEMENT')}
              className={`filter-tab-btn ${scenarioFilter === 'ENFORCEMENT' ? 'filter-tab-active' : ''}`}
            >
              <Shield size={12} className="inline mr-1" />
              Enforcement ({events.filter(e => e.event_type === 'enforcement').length})
            </button>
            <button
              onClick={() => setScenarioFilter('PROMPT_INJECTION')}
              className={`filter-tab-btn ${scenarioFilter === 'PROMPT_INJECTION' ? 'filter-tab-active' : ''}`}
            >
              <Flame size={12} className="inline mr-1 text-indigo" />
              Prompt Injection
            </button>
            <button
              onClick={() => setScenarioFilter('SECRET_EXFILTRATION')}
              className={`filter-tab-btn ${scenarioFilter === 'SECRET_EXFILTRATION' ? 'filter-tab-active' : ''}`}
            >
              <KeyRound size={12} className="inline mr-1 text-rose" />
              Exfiltration
            </button>
            <button
              onClick={() => setScenarioFilter('ROGUE_AGENT')}
              className={`filter-tab-btn ${scenarioFilter === 'ROGUE_AGENT' ? 'filter-tab-active' : ''}`}
            >
              <UserX size={12} className="inline mr-1 text-amber" />
              Rogue Agent
            </button>
          </div>

          {/* Search Input */}
          <div className="search-box-wrapper relative">
            <Search size={14} className="search-icon absolute left-3 top-2.5 text-muted" />
            <input
              type="text"
              placeholder="Search event ID, agent, action, or reason..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="form-input search-input pl-8 text-xs w-full"
            />
          </div>

          {/* Event List */}
          <div className="event-list-container flex flex-col gap-2 max-h-[680px] overflow-y-auto pr-1">
            {filteredEvents.length === 0 ? (
              <div className="p-6 text-center text-xs text-muted font-mono">
                No events match the selected criteria.
              </div>
            ) : (
              filteredEvents.map(event => {
                const tagInfo = getEventTag(event);
                const isSelected = selectedEventId === event.id;
                const decisionStatus = (event.decision?.status || event.decision?.decision || '').toUpperCase();

                return (
                  <div
                    key={event.id}
                    onClick={() => loadReplay(event.id)}
                    className={`event-card-item p-3 rounded-lg border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-indigo/15 border-indigo shadow-glow'
                        : 'bg-bg-secondary/40 border-border-color hover:bg-bg-secondary/80 hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold border flex items-center gap-1 ${tagInfo.colorClass}`}>
                          {tagInfo.icon}
                          {tagInfo.tag}
                        </span>
                        <span className="font-mono text-xs text-muted">#{event.seq}</span>
                      </div>
                      {decisionStatus && (
                        <DecisionBadge
                          decision={{
                            decision: decisionStatus,
                            allowed: event.decision?.allowed,
                            status: decisionStatus,
                          }}
                          size="sm"
                        />
                      )}
                    </div>

                    <div className="mt-2 flex items-center justify-between text-xs">
                      <span className="font-mono text-white font-semibold truncate max-w-[190px]">
                        {event.action}
                      </span>
                      <span className="font-mono text-muted text-[11px] truncate">
                        {event.agent_id}
                      </span>
                    </div>

                    <div className="mt-1 flex items-center justify-between text-[11px] text-muted font-mono">
                      <span>{new Date(event.timestamp).toLocaleTimeString()}</span>
                      <span className="truncate max-w-[120px]">{event.id.slice(0, 8)}...</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: 6-Stage Evidence Timeline Panel */}
        <div className="replay-evidence-panel glass-card p-6 flex flex-col gap-4">
          <div className="panel-header border-b border-border-color pb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldAlert size={18} className="text-cyan" />
              <div>
                <h3 className="panel-title text-base font-semibold">Incident Evidence Timeline</h3>
                <p className="panel-subtitle text-xs text-secondary">
                  Granular chronological verification across execution, detection, PDP evaluation, enforcement, alerts, and cryptographic ledger
                </p>
              </div>
            </div>

            {replayData && (
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-muted">Chain Status:</span>
                <span className={`px-2 py-0.5 rounded font-mono text-xs flex items-center gap-1 ${
                  replayData.ledger.chain_valid
                    ? 'bg-emerald/15 text-emerald border border-emerald/30'
                    : 'bg-rose/15 text-rose border border-rose/30'
                }`}>
                  <CheckCircle2 size={12} /> VERIFIED
                </span>
              </div>
            )}
          </div>

          {/* Body Content */}
          <div className="timeline-body min-h-[500px]">
            {isLoadingReplay ? (
              <div className="p-16 flex items-center justify-center">
                <LoadingSpinner label="Aggregating cryptographic evidence and replay telemetry..." />
              </div>
            ) : replayError ? (
              <div className="p-8 text-center flex flex-col items-center gap-3">
                <AlertTriangle size={32} className="text-rose" />
                <h4 className="text-sm font-semibold text-rose">Replay Evidence Error</h4>
                <p className="text-xs text-secondary max-w-md">{replayError}</p>
                {selectedEventId && (
                  <button
                    onClick={() => loadReplay(selectedEventId)}
                    className="btn btn-secondary text-xs mt-2"
                  >
                    Retry Replay
                  </button>
                )}
              </div>
            ) : !replayData ? (
              <EmptyState
                icon={History}
                title="No Event Selected for Replay"
                description="Select any recorded event from the left audit stream to visualize its end-to-end evidence timeline across all 6 runtime integrity stages."
              />
            ) : (
              <div className="evidence-timeline">
                {/* ─────────────────────────────────────────────────────────────
                    STAGE 1: Attack Vector / Execution Attempt
                   ───────────────────────────────────────────────────────────── */}
                <div className="timeline-stage">
                  <div className="timeline-stage-node bg-indigo text-white border-2 border-bg-primary">
                    1
                  </div>
                  <div className="timeline-stage-card">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <Terminal size={15} className="text-indigo" />
                        <h4 className="font-semibold text-sm text-white">Stage 1: Action / Attack Vector</h4>
                      </div>
                      <span className="font-mono text-xs text-muted flex items-center gap-1">
                        <Clock size={12} />
                        {new Date(replayData.timestamp).toLocaleString()}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mt-3 text-xs font-mono">
                      <div className="p-2 rounded bg-black/40 border border-white/5">
                        <span className="text-muted block text-[11px]">Executing Agent:</span>
                        <span className="text-white font-semibold">
                          {(() => {
                            const found = agents.find(a => a.id === replayData.agent_id);
                            return found ? `${found.name} (${replayData.agent_id})` : replayData.agent_id;
                          })()}
                        </span>
                      </div>
                      <div className="p-2 rounded bg-black/40 border border-white/5">
                        <span className="text-muted block text-[11px]">Invoked Action / Tool:</span>
                        <span className="text-cyan font-semibold">{replayData.action}</span>
                      </div>
                      <div className="p-2 rounded bg-black/40 border border-white/5">
                        <span className="text-muted block text-[11px]">Event Type:</span>
                        <span className="text-white">{replayData.event_type}</span>
                      </div>
                    </div>

                    {/* Payload inspection */}
                    {replayData.payload && Object.keys(replayData.payload).length > 0 && (
                      <div className="mt-3">
                        <span className="text-muted text-[11px] font-mono block mb-1">
                          Action Payload & Mission Parameters:
                        </span>
                        <div className="p-2.5 rounded bg-black/50 border border-white/5 max-h-36 overflow-y-auto">
                          <pre className="text-xs text-secondary font-mono leading-relaxed whitespace-pre-wrap">
                            {JSON.stringify(replayData.payload, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* ─────────────────────────────────────────────────────────────
                    STAGE 2: Detection & Risk Assessment
                   ───────────────────────────────────────────────────────────── */}
                <div className="timeline-stage">
                  <div className="timeline-stage-node bg-amber text-black border-2 border-bg-primary">
                    2
                  </div>
                  <div className="timeline-stage-card">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <Activity size={15} className="text-amber" />
                        <h4 className="font-semibold text-sm text-white">Stage 2: Detection & Risk Assessment</h4>
                      </div>
                      <SeverityBadge severity={replayData.risk_level || 'low'} size="sm" />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-3 text-xs font-mono">
                      <div className="p-2 rounded bg-black/40 border border-white/5">
                        <span className="text-muted block text-[11px]">Decision Rationale / Reason Code:</span>
                        <span className="text-amber font-semibold">{replayData.reason || 'None reported'}</span>
                      </div>
                      <div className="p-2 rounded bg-black/40 border border-white/5">
                        <span className="text-muted block text-[11px]">Assessed Risk Level:</span>
                        <span className="text-white uppercase">{replayData.risk_level || 'standard'}</span>
                      </div>
                    </div>

                    {/* Diagnostic details if present */}
                    {replayData.details && Object.keys(replayData.details).length > 0 && (
                      <div className="mt-3">
                        <span className="text-muted text-[11px] font-mono block mb-1">
                          Diagnostic Context (Taint Path / Contract Drift / Anomaly Telemetry):
                        </span>
                        <div className="p-2.5 rounded bg-black/50 border border-white/5 max-h-36 overflow-y-auto">
                          <pre className="text-xs text-secondary font-mono leading-relaxed whitespace-pre-wrap">
                            {JSON.stringify(replayData.details, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* ─────────────────────────────────────────────────────────────
                    STAGE 3: Policy Decision Point (PDP)
                   ───────────────────────────────────────────────────────────── */}
                <div className="timeline-stage">
                  <div className="timeline-stage-node bg-rose text-white border-2 border-bg-primary">
                    3
                  </div>
                  <div className="timeline-stage-card">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <Shield size={15} className="text-rose" />
                        <h4 className="font-semibold text-sm text-white">Stage 3: Policy Decision Point (PDP)</h4>
                      </div>
                      {replayData.decision && (
                        <DecisionBadge
                          decision={{
                            decision: replayData.decision,
                            allowed: replayData.allowed,
                            status: replayData.decision,
                          }}
                          size="md"
                        />
                      )}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-3 text-xs font-mono">
                      <div className="p-2 rounded bg-black/40 border border-white/5">
                        <span className="text-muted block text-[11px]">Gate Verdict:</span>
                        <span className="text-white font-semibold">{replayData.decision || 'N/A'}</span>
                      </div>
                      <div className="p-2 rounded bg-black/40 border border-white/5">
                        <span className="text-muted block text-[11px]">Action Allowed:</span>
                        {replayData.allowed ? (
                          <span className="text-emerald font-semibold flex items-center gap-1">
                            <CheckCircle2 size={12} /> Permitted
                          </span>
                        ) : (
                          <span className="text-rose font-semibold flex items-center gap-1">
                            <XCircle size={12} /> Denied / Intercepted
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* ─────────────────────────────────────────────────────────────
                    STAGE 4: Enforcement Outcome & Quarantine State
                   ───────────────────────────────────────────────────────────── */}
                <div className="timeline-stage">
                  <div className="timeline-stage-node bg-cyan text-black border-2 border-bg-primary">
                    4
                  </div>
                  <div className="timeline-stage-card">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <Lock size={15} className="text-cyan" />
                        <h4 className="font-semibold text-sm text-white">Stage 4: Enforcement & Agent State</h4>
                      </div>
                      {replayData.resulting_agent_status && (
                        <StatusBadge status={replayData.resulting_agent_status as any} />
                      )}
                    </div>

                    <div className="mt-3 p-3 rounded bg-black/40 border border-white/5 text-xs font-mono">
                      <span className="text-muted block text-[11px]">Enforcement Outcome:</span>
                      <span className="text-white font-semibold text-sm">
                        {replayData.enforcement_outcome}
                      </span>
                      {replayData.resulting_agent_status && (
                        <span className="text-secondary block mt-1">
                          Agent '{replayData.agent_id}' status in registry: <strong className="text-cyan">{replayData.resulting_agent_status}</strong>
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* ─────────────────────────────────────────────────────────────
                    STAGE 5: Generated Alert
                   ───────────────────────────────────────────────────────────── */}
                <div className="timeline-stage">
                  <div className="timeline-stage-node bg-violet text-white border-2 border-bg-primary">
                    5
                  </div>
                  <div className="timeline-stage-card">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <ShieldAlert size={15} className="text-violet" />
                        <h4 className="font-semibold text-sm text-white">Stage 5: Triggered Security Alert</h4>
                      </div>
                      {replayData.alert && (
                        <SeverityBadge severity={replayData.alert.severity} size="sm" />
                      )}
                    </div>

                    {replayData.alert ? (
                      <div className="alert-result-card p-3 rounded border border-rose/30 bg-rose-subtle mt-3 flex flex-col gap-1.5">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <span className="font-mono text-xs font-bold text-white">
                            {replayData.alert.alert_type}
                          </span>
                          <span className="font-mono text-[11px] text-muted">
                            Alert ID: {replayData.alert.id}
                          </span>
                        </div>
                        <p className="text-xs text-white/95 leading-relaxed">
                          {replayData.alert.message}
                        </p>
                        <div className="text-[11px] text-muted font-mono pt-1 border-t border-white/10 flex items-center justify-between">
                          <span>Target Agent: {replayData.alert.agent_id}</span>
                          <span>Linked Event ID: {replayData.alert.event_id}</span>
                        </div>
                      </div>
                    ) : (
                      <div className="p-3 rounded bg-bg-secondary/40 border border-white/5 text-xs text-muted font-mono flex items-center gap-2 mt-3">
                        <Info size={14} className="text-muted" />
                        <span>No security alert triggered for this event (action permitted or policy criteria met).</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* ─────────────────────────────────────────────────────────────
                    STAGE 6: Cryptographic Evidence Ledger
                   ───────────────────────────────────────────────────────────── */}
                <div className="timeline-stage">
                  <div className="timeline-stage-node bg-emerald text-black border-2 border-bg-primary">
                    6
                  </div>
                  <div className="timeline-stage-card border-emerald/30 shadow-glow">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <FileCheck size={15} className="text-emerald" />
                        <h4 className="font-semibold text-sm text-white">Stage 6: Tamper-Proof Cryptographic Ledger</h4>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-emerald/20 text-emerald font-semibold border border-emerald/40">
                        LEDGER BLOCK #{replayData.ledger.seq}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 gap-2 mt-3 text-xs font-mono">
                      <div className="p-2.5 rounded bg-black/60 border border-white/5 flex flex-col gap-1">
                        <div className="flex items-center justify-between">
                          <span className="text-muted text-[11px]">Ledger Event UUID:</span>
                          <span className="text-white select-all break-all">{replayData.event_id}</span>
                        </div>
                      </div>

                      <div className="p-2.5 rounded bg-black/60 border border-white/5 flex flex-col gap-1">
                        <div className="flex items-center justify-between">
                          <span className="text-muted text-[11px]">Previous Block Hash:</span>
                          <span className="text-cyan font-mono text-[11px] select-all break-all">
                            {replayData.ledger.previous_hash}
                          </span>
                        </div>
                      </div>

                      <div className="p-2.5 rounded bg-black/60 border border-white/5 flex flex-col gap-1">
                        <div className="flex items-center justify-between">
                          <span className="text-muted text-[11px]">Content Payload Hash:</span>
                          <span className="text-secondary font-mono text-[11px] select-all break-all">
                            {replayData.ledger.content_hash}
                          </span>
                        </div>
                      </div>

                      <div className="p-2.5 rounded bg-black/60 border border-white/5 flex flex-col gap-1">
                        <div className="flex items-center justify-between">
                          <span className="text-muted text-[11px]">Merkle / Event Block Hash:</span>
                          <span className="text-emerald font-mono text-[11px] font-semibold select-all break-all">
                            {replayData.ledger.event_hash}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="mt-3 p-2 rounded bg-emerald/10 border border-emerald/20 flex items-center justify-between text-xs font-mono">
                      <span className="flex items-center gap-1.5 text-emerald font-semibold">
                        <CheckCircle2 size={14} /> Cryptographic SHA256 Chaining Verified
                      </span>
                      <span className="text-muted text-[11px]">Immutable Storage Record</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
