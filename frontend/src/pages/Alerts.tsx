import React, { useState, useMemo } from 'react';
import { Alert, Agent, EventLog, AnomalyDetectResponse } from '../types';
import { formatTimeIST } from '../utils/time';
import { AlertFilters } from '../components/alerts/AlertFilters';
import { AlertList } from '../components/alerts/AlertList';
import { AlertDetailModal } from '../components/alerts/AlertDetailModal';
import { detectAnomalies } from '../services/api';
import {
  ShieldAlert,
  RefreshCw,
  Radar,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  PlayCircle,
  Clock,
} from 'lucide-react';

interface AlertsPageProps {
  alerts: Alert[];
  agents: Agent[];
  events?: EventLog[];
  isLoading: boolean;
  onRefresh: () => void;
  selectedAlert: Alert | null;
  onSelectAlert: (alert: Alert | null) => void;
  onInspectEvent?: (eventId: string) => void;
}

export const Alerts: React.FC<AlertsPageProps> = ({
  alerts,
  agents,
  events = [],
  isLoading,
  onRefresh,
  selectedAlert,
  onSelectAlert,
  onInspectEvent,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSeverity, setSelectedSeverity] = useState('ALL');
  const [selectedAgent, setSelectedAgent] = useState('ALL');

  // Anomaly Detection State
  const [selectedScanAgent, setSelectedScanAgent] = useState('ALL');
  const [isScanning, setIsScanning] = useState(false);
  const [scanResponse, setScanResponse] = useState<AnomalyDetectResponse | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);

  const handleRunAnomalyScan = async () => {
    setIsScanning(true);
    setScanError(null);
    try {
      const resp = await detectAnomalies(
        selectedScanAgent === 'ALL' ? undefined : { agent_id: selectedScanAgent }
      );
      setScanResponse(resp);
      const newAlerts = resp.alerts_created ?? resp.new_alerts_created;
      if (newAlerts > 0) {
        onRefresh();
      }
    } catch (err: any) {
      setScanError(err.message || 'Anomaly detection scan failed');
    } finally {
      setIsScanning(false);
    }
  };

  // Compute severity counts for filter tabs
  const severityCounts = useMemo(() => {
    const counts: Record<string, number> = {
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
    };
    alerts.forEach(a => {
      const sev = (a.severity || 'medium').toLowerCase();
      if (counts[sev] !== undefined) {
        counts[sev]++;
      } else {
        counts[sev] = 1;
      }
    });
    return counts;
  }, [alerts]);

  // Extract unique agent IDs
  const availableAgents = useMemo(() => {
    const set = new Set<string>();
    agents.forEach(a => set.add(a.id));
    alerts.forEach(al => {
      if (al.agent_id) set.add(al.agent_id);
    });
    return Array.from(set).sort();
  }, [agents, alerts]);

  // Filter alerts
  const filteredAlerts = useMemo(() => {
    return alerts.filter(alert => {
      if (selectedSeverity !== 'ALL' && alert.severity.toLowerCase() !== selectedSeverity.toLowerCase()) {
        return false;
      }
      if (selectedAgent !== 'ALL' && alert.agent_id !== selectedAgent) {
        return false;
      }
      if (searchQuery.trim() !== '') {
        const query = searchQuery.toLowerCase();
        const matchMessage = alert.message.toLowerCase().includes(query);
        const matchType = alert.alert_type.toLowerCase().includes(query);
        const matchAgent = (alert.agent_id || '').toLowerCase().includes(query);
        return matchMessage || matchType || matchAgent;
      }
      return true;
    });
  }, [alerts, selectedSeverity, selectedAgent, searchQuery]);

  return (
    <div className="alerts-page-flow">
      {/* Header bar */}
      <div className="page-header glass-card">
        <div className="page-title-group">
          <div className="panel-icon-box bg-rose-glow">
            <ShieldAlert size={22} className="text-rose" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="page-title">Security Alerts & Incidents</h2>
              <span className="count-pill count-pill-active font-mono text-xs">
                {alerts.length} Total
              </span>
            </div>
            <p className="page-subtitle">
              Continuous runtime behavioral monitoring, mission drift, and policy violation logs
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="btn btn-secondary btn-sm"
          >
            <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* ── RUNTIME ANOMALY DETECTION SECTION ──────────────────────── */}
      <div className="glass-card p-5 border border-cyan/20 bg-slate-900/40">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-cyan/10 border border-cyan/30 text-cyan">
              <Radar size={22} className={isScanning ? 'animate-spin' : ''} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-white text-base">Runtime Anomaly Detection</h3>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-cyan/15 text-cyan border border-cyan/30">
                  Deterministic Engine
                </span>
              </div>
              <p className="text-xs text-muted mt-0.5">
                Evaluates ledger event streams against deterministic rules (Rule A: High-Risk, Rule B: Policy Violations, Rule C: Action Burst).
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs text-muted font-mono">
              <span>Target:</span>
              <select
                value={selectedScanAgent}
                onChange={(e) => setSelectedScanAgent(e.target.value)}
                className="bg-black/40 border border-white/10 rounded px-2.5 py-1 text-xs text-white font-mono focus:border-cyan outline-none"
              >
                <option value="ALL">All Agents</option>
                {availableAgents.map((aid) => (
                  <option key={aid} value={aid}>{aid}</option>
                ))}
              </select>
            </div>

            <button
              onClick={handleRunAnomalyScan}
              disabled={isScanning || isLoading}
              className="btn btn-primary btn-sm flex items-center gap-1.5 font-mono text-xs shadow-lg shadow-cyan/10"
            >
              <Radar size={13} className={isScanning ? 'animate-spin' : ''} />
              <span>{isScanning ? 'Analyzing Stream...' : 'Run Detection'}</span>
            </button>
          </div>
        </div>

        {/* Rules Summary Tags */}
        <div className="flex flex-wrap gap-2 py-3 border-b border-white/5 text-[11px] font-mono text-muted">
          <span className="text-muted/60">Active Rules:</span>
          <span className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-cyan-200">
            Rule A: Repeated High-Risk (&ge;3 high/crit in 5m)
          </span>
          <span className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-cyan-200">
            Rule B: Repeated Policy Violations (&ge;3 violations in 5m)
          </span>
          <span className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-cyan-200">
            Rule C: Action Burst (&ge;10 actions in 1m)
          </span>
        </div>

        {/* Scan Status / Results */}
        {scanError && (
          <div className="mt-4 p-3 rounded-lg border border-rose/30 bg-rose/10 text-xs font-mono text-rose flex items-center justify-between">
            <span className="flex items-center gap-2">
              <AlertTriangle size={14} className="text-rose" />
              Scan Error: {scanError}
            </span>
            <button
              onClick={handleRunAnomalyScan}
              className="text-xs underline hover:text-white"
            >
              Retry
            </button>
          </div>
        )}

        {isScanning && (
          <div className="mt-4 p-6 rounded-lg border border-cyan/20 bg-cyan/5 text-center flex flex-col items-center justify-center gap-2">
            <Radar size={28} className="text-cyan animate-spin" />
            <p className="text-xs font-mono text-cyan">Scanning runtime event stream and evaluating sliding time windows...</p>
          </div>
        )}

        {!isScanning && scanResponse && (
          <div className="mt-4 space-y-4">
            {/* Metrics Row */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <div className="p-3 rounded-lg bg-black/30 border border-white/5">
                <span className="text-[10px] uppercase font-mono text-muted block">Agents Scanned</span>
                <span className="text-sm font-mono font-semibold text-white">{scanResponse.scanned_agents.length}</span>
              </div>
              <div className="p-3 rounded-lg bg-black/30 border border-white/5">
                <span className="text-[10px] uppercase font-mono text-muted block">Events Analyzed</span>
                <span className="text-sm font-mono font-semibold text-cyan">{scanResponse.total_events_analyzed}</span>
              </div>
              <div className="p-3 rounded-lg bg-black/30 border border-white/5">
                <span className="text-[10px] uppercase font-mono text-muted block">Rules Evaluated</span>
                <span className="text-sm font-mono font-semibold text-white">{scanResponse.rules_evaluated?.length || 3}</span>
              </div>
              <div className="p-3 rounded-lg bg-black/30 border border-white/5">
                <span className="text-[10px] uppercase font-mono text-muted block">Anomalies Found</span>
                <span className={`text-sm font-mono font-semibold ${scanResponse.anomalies_detected > 0 ? 'text-amber' : 'text-emerald'}`}>
                  {scanResponse.anomalies_detected}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-black/30 border border-white/5">
                <span className="text-[10px] uppercase font-mono text-muted block">New Alerts</span>
                <span className="text-sm font-mono font-semibold text-rose">
                  {scanResponse.alerts_created ?? scanResponse.new_alerts_created}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-black/30 border border-white/5">
                <span className="text-[10px] uppercase font-mono text-muted block">Deduplicated</span>
                <span className="text-sm font-mono font-semibold text-muted">
                  {scanResponse.alerts_deduplicated ?? 0}
                </span>
              </div>
            </div>

            {/* Zero Anomalies State */}
            {scanResponse.anomalies.length === 0 ? (
              <div className="p-4 rounded-lg bg-emerald/10 border border-emerald/20 flex items-center gap-3">
                <CheckCircle2 size={18} className="text-emerald shrink-0" />
                <div>
                  <p className="text-xs font-mono text-emerald font-semibold">Zero Anomalies Detected</p>
                  <p className="text-[11px] text-muted">
                    No suspicious patterns found across evaluated agents ({scanResponse.scanned_agents.join(', ')}). All actions fall within nominal rate and risk limits.
                  </p>
                </div>
              </div>
            ) : (
              /* Detected Anomalies List */
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs text-muted font-mono">
                  <span>Detected Patterns ({scanResponse.anomalies.length}):</span>
                  <span>Click an event ID to inspect in Attack Replay</span>
                </div>
                {scanResponse.anomalies.map((anomaly, idx) => (
                  <div
                    key={`${anomaly.agent_id}-${anomaly.anomaly_type}-${idx}`}
                    className="p-4 rounded-lg bg-black/40 border border-amber/30 hover:border-amber/50 transition-colors space-y-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold ${
                          anomaly.severity === 'critical' ? 'bg-rose/20 text-rose border border-rose/40' :
                          anomaly.severity === 'high' ? 'bg-orange/20 text-orange border border-orange/40' :
                          'bg-amber/20 text-amber border border-amber/40'
                        }`}>
                          {anomaly.severity}
                        </span>
                        <span className="text-xs font-mono font-semibold text-white">
                          {anomaly.anomaly_type}
                        </span>
                        <span className="px-2 py-0.5 rounded bg-white/5 text-muted text-[11px] font-mono border border-white/10">
                          {anomaly.agent_id}
                        </span>
                        {anomaly.created_alert ? (
                          <span className="text-[10px] font-mono text-rose bg-rose/10 px-2 py-0.5 rounded border border-rose/30">
                            New Alert Created
                          </span>
                        ) : (
                          <span className="text-[10px] font-mono text-muted bg-white/5 px-2 py-0.5 rounded border border-white/10">
                            Alert Deduplicated (Reused)
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-[11px] text-muted font-mono">
                        <Clock size={12} />
                        <span>{formatTimeIST(anomaly.timestamp)}</span>
                        {anomaly.alert_id && (
                          <button
                            onClick={() => {
                              const found = alerts.find(a => a.id === anomaly.alert_id);
                              if (found) onSelectAlert(found);
                            }}
                            className="text-cyan hover:underline cursor-pointer flex items-center gap-1 font-mono text-[11px]"
                            title="Open Incident Investigation for this alert"
                          >
                            <span>Alert #{anomaly.alert_id.slice(0, 8)}...</span>
                          </button>
                        )}
                      </div>
                    </div>

                    <p className="text-xs text-white/90 font-mono">
                      {anomaly.message}
                    </p>

                    {anomaly.explanation && (
                      <p className="text-[11px] text-muted">
                        <span className="text-cyan font-mono">Rule Criteria: </span>
                        {anomaly.explanation}
                      </p>
                    )}

                    {/* Supporting Events with Replay Link */}
                    <div className="pt-2 border-t border-white/5 flex flex-wrap items-center justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-[11px] font-mono text-muted mr-1">
                          Supporting Events ({anomaly.event_count}):
                        </span>
                        {(anomaly.supporting_event_ids || anomaly.triggering_event_ids).map((eid) => (
                          <button
                            key={eid}
                            onClick={() => onInspectEvent?.(eid)}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-cyan/10 hover:bg-cyan/20 border border-cyan/30 text-cyan text-[11px] font-mono transition-colors"
                            title={`Inspect event ${eid} in Attack Replay`}
                          >
                            <span>{eid.slice(0, 8)}...</span>
                            <ExternalLink size={10} />
                          </button>
                        ))}
                      </div>

                      <div className="flex items-center gap-2">
                        {anomaly.alert_id && (
                          <button
                            onClick={() => {
                              const found = alerts.find(a => a.id === anomaly.alert_id);
                              if (found) onSelectAlert(found);
                            }}
                            className="btn btn-primary btn-xs flex items-center gap-1 font-mono text-[11px]"
                            title="Investigate incident in SOC console"
                          >
                            <ShieldAlert size={12} />
                            <span>Investigate Incident</span>
                          </button>
                        )}

                        <button
                          onClick={() => onInspectEvent?.(anomaly.latest_event_id)}
                          className="btn btn-secondary btn-xs flex items-center gap-1 font-mono text-[11px] text-cyan hover:text-white"
                          title="Replay latest triggering event in Attack Replay"
                        >
                          <PlayCircle size={12} className="text-cyan" />
                          <span>Replay Latest Event</span>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Filter and search bar */}
      <AlertFilters
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        selectedSeverity={selectedSeverity}
        onSeverityChange={setSelectedSeverity}
        selectedAgent={selectedAgent}
        onAgentChange={setSelectedAgent}
        availableAgents={availableAgents}
        severityCounts={severityCounts}
      />

      {/* Alerts list table */}
      <AlertList
        alerts={filteredAlerts}
        isLoading={isLoading}
        onSelectAlert={onSelectAlert}
        onRefresh={onRefresh}
      />

      {/* Incident Investigation Modal */}
      <AlertDetailModal
        alert={selectedAlert}
        events={events}
        onClose={() => onSelectAlert(null)}
        onInspectEvent={onInspectEvent}
      />
    </div>
  );
};
