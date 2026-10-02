import React, { useState, useEffect, useMemo } from 'react';
import { Alert, EventLog, AttackReplayResponse } from '../../types';
import { formatFullDateTimeIST } from '../../utils/time';
import { SeverityBadge } from '../common/SeverityBadge';
import { DecisionBadge } from '../common/DecisionBadge';
import { fetchAttackReplay } from '../../services/api';
import {
  X,
  Clock,
  Bot,
  AlertTriangle,
  Copy,
  Check,
  Shield,
  Layers,
  History,
  CheckCircle2,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  FileCode,
  ArrowLeft,
  Sparkles,
  Link,
  ShieldAlert,
} from 'lucide-react';

interface AlertDetailModalProps {
  alert: Alert | null;
  events?: EventLog[];
  onClose: () => void;
  onInspectEvent?: (eventId: string) => void;
}

export const AlertDetailModal: React.FC<AlertDetailModalProps> = ({
  alert,
  events = [],
  onClose,
  onInspectEvent,
}) => {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showRawDetails, setShowRawDetails] = useState<boolean>(false);

  // Asynchronous ledger evidence state
  const [ledgerLoading, setLedgerLoading] = useState<boolean>(false);
  const [replayData, setReplayData] = useState<AttackReplayResponse | null>(null);
  const [ledgerError, setLedgerError] = useState<string | null>(null);

  // Copy helper
  const copyText = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(label);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const formatTimestamp = (iso?: string) => {
    return formatFullDateTimeIST(iso);
  };

  // Fetch replay/ledger evidence whenever alert or its event_id changes
  useEffect(() => {
    if (!alert || !alert.event_id) {
      setReplayData(null);
      setLedgerLoading(false);
      setLedgerError(null);
      return;
    }

    let isMounted = true;
    setLedgerLoading(true);
    setLedgerError(null);

    fetchAttackReplay(alert.event_id)
      .then((data) => {
        if (isMounted) {
          setReplayData(data);
          setLedgerLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setLedgerError(err.message || 'Failed to load ledger evidence');
          setLedgerLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [alert?.id, alert?.event_id]);

  // Extract supporting events from details
  const supportingEventIds: string[] = useMemo(() => {
    if (!alert || !alert.details) return [];
    const list = alert.details.supporting_event_ids || alert.details.triggering_event_ids;
    if (Array.isArray(list)) {
      return list.map(String);
    }
    return [];
  }, [alert]);

  // Map supporting event IDs to supporting event metadata
  const resolvedSupportingEvents = useMemo(() => {
    if (supportingEventIds.length === 0) return [];
    const eventMap = new Map<string, EventLog>();
    events.forEach(e => eventMap.set(e.id, e));

    return supportingEventIds.map(eid => {
      const found = eventMap.get(eid);
      if (found) {
        const dec = found.decision?.status || found.decision?.decision || 'BLOCK';
        return {
          id: found.id,
          action: found.action,
          agent_id: found.agent_id,
          decision: String(dec),
          timestamp: found.created_at || new Date().toISOString(),
        };
      }
      return {
        id: eid,
        action: alert?.details?.actions?.[0] || 'evaluated_action',
        agent_id: alert?.agent_id || 'UNKNOWN',
        decision: 'BLOCK',
        timestamp: alert?.created_at || new Date().toISOString(),
      };
    });
  }, [supportingEventIds, events, alert]);

  if (!alert) return null;

  // Extract anomaly rule or attack scenario information
  const details = alert.details || {};
  const isAnomalyAlert = alert.alert_type.startsWith('REPEATED_') || alert.alert_type.includes('ANOMALY');
  const anomalyRule = details.anomaly_rule || details.rule_name;
  const attackScenario = details.scenario;
  const violationReason = details.reason || (replayData?.reason);
  const riskLevel = details.risk_level || replayData?.risk_level || alert.severity;
  const decisionOutcome = details.decision || replayData?.decision || (alert.severity === 'critical' || alert.severity === 'high' ? 'BLOCK' : 'ALLOW');

  const linkedEventId = alert.event_id || details.latest_event_id;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content modal-incident glass-card" onClick={e => e.stopPropagation()}>
        {/* Incident Header */}
        <div className="modal-header">
          <div className="modal-title-group">
            <div className="panel-icon-box bg-rose-glow">
              <ShieldAlert size={22} className="text-rose" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-white/10 text-cyan border border-cyan/30">
                  Incident Investigation
                </span>
                <span className="text-xs text-muted font-mono">
                  Alert #{alert.id.slice(0, 8)}
                </span>
              </div>
              <div className="flex items-center gap-2.5">
                <SeverityBadge severity={alert.severity} size="md" />
                <h3 className="font-mono text-base font-bold text-white tracking-wide">
                  {alert.alert_type}
                </h3>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => copyText(alert.id, 'alert_id')}
              className="btn btn-secondary btn-xs flex items-center gap-1 font-mono text-[11px]"
              title="Copy Alert ID"
            >
              {copiedId === 'alert_id' ? (
                <>
                  <Check size={12} className="text-emerald" />
                  <span>Copied</span>
                </>
              ) : (
                <>
                  <Copy size={12} />
                  <span>Copy ID</span>
                </>
              )}
            </button>

            <button onClick={onClose} className="btn-icon" title="Close Investigation Console">
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Modal Body / Investigation Layout */}
        <div className="modal-body space-y-5">
          {/* Incident Message Box */}
          <div className="detail-section">
            <div className="alert-message-box">
              <p className="text-sm text-white font-medium leading-relaxed">
                {alert.message}
              </p>
            </div>
          </div>

          {/* Core Metadata Bar */}
          <div className="modal-meta-grid">
            <div className="meta-box">
              <div className="meta-box-label flex items-center gap-1">
                <Bot size={13} className="text-cyan" />
                <span>Target / Affected Agent</span>
              </div>
              <div className="meta-box-value font-mono text-cyan font-semibold">
                {alert.agent_id || 'SYSTEM / GLOBAL'}
              </div>
            </div>

            <div className="meta-box">
              <div className="meta-box-label flex items-center gap-1">
                <Clock size={13} className="text-muted" />
                <span>Detection Timestamp</span>
              </div>
              <div className="meta-box-value font-mono text-xs">
                {formatTimestamp(alert.created_at)}
              </div>
            </div>

            <div className="meta-box">
              <div className="meta-box-label flex items-center gap-1">
                <Shield size={13} className="text-muted" />
                <span>PEP Enforcement Verdict</span>
              </div>
              <div className="meta-box-value pt-0.5">
                <DecisionBadge decision={{ status: decisionOutcome }} />
              </div>
            </div>

            <div className="meta-box">
              <div className="meta-box-label flex items-center gap-1">
                <AlertTriangle size={13} className="text-muted" />
                <span>Assessed Risk Level</span>
              </div>
              <div className="meta-box-value pt-0.5">
                <SeverityBadge severity={riskLevel} size="sm" />
              </div>
            </div>
          </div>

          {/* Section 1: Detection Explanation & Rule Criteria */}
          <div className="incident-evidence-card space-y-2.5">
            <div className="flex items-center justify-between border-b border-white/5 pb-2">
              <span className="detail-label mb-0 flex items-center gap-1.5 text-white">
                <Sparkles size={13} className="text-cyan" />
                Detection Explanation & Security Rule
              </span>
              <span className="text-[11px] font-mono text-muted">
                {isAnomalyAlert ? 'Behavioral Anomaly Rule' : 'Policy Enforcement Rule'}
              </span>
            </div>

            {isAnomalyAlert ? (
              <div className="space-y-2 text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-muted font-mono">Triggered Rule:</span>
                  <span className="font-mono font-semibold text-cyan">
                    {anomalyRule || 'Deterministic Anomaly Detector'}
                  </span>
                </div>
                {details.event_count && (
                  <div className="flex items-center gap-2 text-[11px] text-muted font-mono">
                    <span>Evidence Threshold:</span>
                    <span className="text-white">
                      {details.event_count} participating events
                      {details.time_span_seconds !== undefined && ` within ${Math.round(details.time_span_seconds)}s window`}
                    </span>
                  </div>
                )}
                {details.explanation && (
                  <p className="text-[11px] text-muted pt-1">
                    <span className="text-cyan font-mono">Rule Criteria: </span>
                    {details.explanation}
                  </p>
                )}
              </div>
            ) : attackScenario ? (
              <div className="space-y-1.5 text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-muted font-mono">Attack Scenario:</span>
                  <span className="font-mono font-semibold text-rose uppercase">
                    {attackScenario}
                  </span>
                </div>
                {violationReason && (
                  <div className="flex items-center gap-2">
                    <span className="text-muted font-mono">Policy Reason:</span>
                    <span className="font-mono text-white bg-white/5 px-2 py-0.5 rounded border border-white/10">
                      {violationReason}
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-muted font-mono">
                Direct security alert.
              </p>
            )}
          </div>

          {/* Section 2: Primary Event & Cryptographic Ledger Evidence */}
          <div className="incident-evidence-card space-y-3">
            <div className="flex items-center justify-between border-b border-white/5 pb-2">
              <span className="detail-label mb-0 flex items-center gap-1.5 text-white">
                <Layers size={13} className="text-cyan" />
                Primary Event & Cryptographic Ledger Proof
              </span>
              {linkedEventId && onInspectEvent && (
                <button
                  onClick={() => onInspectEvent(linkedEventId)}
                  className="btn btn-secondary btn-xs flex items-center gap-1 font-mono text-[11px] text-cyan hover:text-white"
                  title="Inspect this event in Attack Replay"
                >
                  <History size={12} />
                  <span>View Evidence in Replay</span>
                </button>
              )}
            </div>

            {linkedEventId ? (
              <div className="space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="p-2.5 rounded bg-black/40 border border-white/5 space-y-1">
                    <span className="text-[10px] uppercase font-mono text-muted block">Linked Event ID</span>
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-mono text-xs text-cyan truncate">{linkedEventId}</span>
                      <button
                        onClick={() => copyText(linkedEventId, 'event_id')}
                        className="btn-icon btn-icon-xs text-muted hover:text-white"
                        title="Copy Event ID"
                      >
                        {copiedId === 'event_id' ? <Check size={11} className="text-emerald" /> : <Copy size={11} />}
                      </button>
                    </div>
                  </div>

                  <div className="p-2.5 rounded bg-black/40 border border-white/5 space-y-1">
                    <span className="text-[10px] uppercase font-mono text-muted block">Attempted Action / Tool</span>
                    <span className="font-mono text-xs text-white">
                      {details.actions?.[0] || replayData?.action || 'enforcement_action'}
                    </span>
                  </div>
                </div>

                {/* Ledger Proof Data */}
                {ledgerLoading ? (
                  <div className="p-4 text-center text-xs font-mono text-muted flex items-center justify-center gap-2">
                    <span className="animate-spin text-cyan">⌛</span>
                    <span>Auditing cryptographic ledger proof...</span>
                  </div>
                ) : replayData?.ledger ? (
                  <div className="p-3 rounded bg-black/40 border border-cyan/20 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-mono text-cyan font-semibold">Ledger Sequence: #{replayData.ledger.seq}</span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald/15 text-emerald border border-emerald/30 flex items-center gap-1">
                          <CheckCircle2 size={11} />
                          <span>VALID HASH-CHAIN</span>
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-muted">SHA-256 Merkle Proof</span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono">
                      <div className="p-1.5 rounded bg-black/50 border border-white/5 flex items-center justify-between">
                        <span className="text-muted">Event Hash:</span>
                        <span className="text-white truncate ml-2 max-w-[200px]" title={replayData.ledger.event_hash}>
                          {replayData.ledger.event_hash.slice(0, 16)}...
                        </span>
                      </div>
                      <div className="p-1.5 rounded bg-black/50 border border-white/5 flex items-center justify-between">
                        <span className="text-muted">Content Hash:</span>
                        <span className="text-white truncate ml-2 max-w-[200px]" title={replayData.ledger.content_hash}>
                          {replayData.ledger.content_hash.slice(0, 16)}...
                        </span>
                      </div>
                      <div className="p-1.5 rounded bg-black/50 border border-white/5 flex items-center justify-between sm:col-span-2">
                        <span className="text-muted">Previous Hash:</span>
                        <span className="text-white truncate ml-2 max-w-[400px]" title={replayData.ledger.previous_hash}>
                          {replayData.ledger.previous_hash.slice(0, 24)}...
                        </span>
                      </div>
                    </div>
                  </div>
                ) : ledgerError ? (
                  <p className="text-xs text-muted font-mono p-2">
                    Ledger evidence unavailable.
                  </p>
                ) : (
                  <p className="text-xs text-muted font-mono p-2">
                    Ledger evidence unavailable.
                  </p>
                )}
              </div>
            ) : (
              <p className="text-xs text-muted font-mono p-2">
                Event evidence unavailable.
              </p>
            )}
          </div>

          {/* Section 3: Supporting Events List */}
          <div className="incident-evidence-card space-y-3">
            <div className="flex items-center justify-between border-b border-white/5 pb-2">
              <span className="detail-label mb-0 flex items-center gap-1.5 text-white">
                <Link size={13} className="text-cyan" />
                Supporting Events Evidence ({supportingEventIds.length})
              </span>
              <span className="text-[11px] font-mono text-muted">
                {supportingEventIds.length > 0 ? 'Click Inspect to launch Attack Replay' : ''}
              </span>
            </div>

            {supportingEventIds.length > 0 ? (
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {resolvedSupportingEvents.map((ev, i) => (
                  <div
                    key={`${ev.id}-${i}`}
                    className="p-2.5 rounded bg-black/40 border border-white/5 hover:border-cyan/30 flex items-center justify-between gap-3 text-xs font-mono transition-colors"
                  >
                    <div className="flex items-center gap-3 overflow-hidden">
                      <span className="text-muted text-[11px]">#{i + 1}</span>
                      <span className="text-cyan truncate max-w-[120px]" title={ev.id}>
                        {ev.id.slice(0, 8)}...
                      </span>
                      <span className="text-white px-2 py-0.5 rounded bg-white/5 border border-white/10 text-[11px]">
                        {ev.action}
                      </span>
                      <span className="text-muted text-[11px] hidden sm:inline">
                        {ev.agent_id}
                      </span>
                      <DecisionBadge decision={{ status: ev.decision }} />
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-[11px] text-muted hidden md:inline">
                        {formatTimestamp(ev.timestamp)}
                      </span>
                      {onInspectEvent && (
                        <button
                          onClick={() => onInspectEvent(ev.id)}
                          className="btn btn-secondary btn-xs flex items-center gap-1 text-cyan hover:text-white"
                          title="Inspect event in Attack Replay"
                        >
                          <span>Inspect</span>
                          <ExternalLink size={11} />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted font-mono p-2">
                No additional supporting events.
              </p>
            )}
          </div>

          {/* Section 4: Collapsible Diagnostic Context */}
          {details && Object.keys(details).length > 0 && (
            <div className="incident-evidence-card">
              <button
                onClick={() => setShowRawDetails(!showRawDetails)}
                className="w-full flex items-center justify-between text-left text-xs font-mono text-muted hover:text-white py-1"
              >
                <span className="flex items-center gap-1.5">
                  <FileCode size={13} className="text-cyan" />
                  <span>Raw Diagnostic Telemetry & Payload Context</span>
                </span>
                <span className="flex items-center gap-1">
                  <span>{showRawDetails ? 'Hide' : 'Expand'}</span>
                  {showRawDetails ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </span>
              </button>

              {showRawDetails && (
                <div className="pt-2 border-t border-white/5 mt-2">
                  <pre className="code-block text-xs font-mono max-h-56 overflow-auto">
                    {JSON.stringify(details, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer / Navigation Actions */}
        <div className="modal-footer">
          <span className="font-mono text-xs text-muted flex items-center gap-1.5">
            <Shield size={12} className="text-emerald" />
            <span>Evidence persisted to immutable audit ledger</span>
          </span>

          <div className="flex items-center gap-2">
            <button onClick={onClose} className="btn btn-secondary btn-sm flex items-center gap-1">
              <ArrowLeft size={13} />
              <span>Back to Alerts Console</span>
            </button>

            {linkedEventId && onInspectEvent && (
              <button
                onClick={() => onInspectEvent(linkedEventId)}
                className="btn btn-primary btn-sm flex items-center gap-1.5 font-mono text-xs"
              >
                <History size={13} />
                <span>Open Attack Replay</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
