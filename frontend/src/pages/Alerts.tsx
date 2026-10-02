import React, { useState, useMemo } from 'react';
import { Alert, Agent } from '../types';
import { AlertFilters } from '../components/alerts/AlertFilters';
import { AlertList } from '../components/alerts/AlertList';
import { AlertDetailModal } from '../components/alerts/AlertDetailModal';
import { detectAnomalies } from '../services/api';
import { ShieldAlert, RefreshCw, Radar, CheckCircle2 } from 'lucide-react';

interface AlertsPageProps {
  alerts: Alert[];
  agents: Agent[];
  isLoading: boolean;
  onRefresh: () => void;
  selectedAlert: Alert | null;
  onSelectAlert: (alert: Alert | null) => void;
  onInspectEvent?: (eventId: string) => void;
}

export const Alerts: React.FC<AlertsPageProps> = ({
  alerts,
  agents,
  isLoading,
  onRefresh,
  selectedAlert,
  onSelectAlert,
  onInspectEvent,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSeverity, setSelectedSeverity] = useState('ALL');
  const [selectedAgent, setSelectedAgent] = useState('ALL');
  const [isScanning, setIsScanning] = useState(false);
  const [scanResult, setScanResult] = useState<{ message: string; count: number } | null>(null);

  const handleRunAnomalyScan = async () => {
    setIsScanning(true);
    setScanResult(null);
    try {
      const resp = await detectAnomalies();
      setScanResult({
        message: `Anomaly detection complete: analyzed ${resp.total_events_analyzed} events, detected ${resp.anomalies_detected} anomalies (${resp.new_alerts_created} new alerts created).`,
        count: resp.new_alerts_created,
      });
      if (resp.new_alerts_created > 0) {
        onRefresh();
      }
    } catch (err: any) {
      setScanResult({
        message: `Anomaly scan failed: ${err.message}`,
        count: 0,
      });
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
            onClick={handleRunAnomalyScan}
            disabled={isLoading || isScanning}
            className="btn btn-primary btn-sm flex items-center gap-1.5 font-mono text-xs"
            title="Scan runtime event stream for suspicious behavioral anomalies"
          >
            <Radar size={13} className={isScanning ? 'animate-spin' : ''} />
            <span>{isScanning ? 'Scanning...' : 'Detect Anomalies'}</span>
          </button>

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

      {/* Anomaly Scan Result Notification */}
      {scanResult && (
        <div className="p-3 rounded-lg border border-cyan/30 bg-cyan/10 text-xs font-mono text-cyan flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <CheckCircle2 size={14} className="text-cyan" />
            {scanResult.message}
          </span>
          <button
            onClick={() => setScanResult(null)}
            className="text-muted hover:text-white text-xs ml-3"
          >
            Dismiss
          </button>
        </div>
      )}

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

      {/* Alert Detail Modal */}
      <AlertDetailModal
        alert={selectedAlert}
        onClose={() => onSelectAlert(null)}
        onInspectEvent={onInspectEvent}
      />
    </div>
  );
};
