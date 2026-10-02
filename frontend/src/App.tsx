import { useState, useEffect, useCallback, useMemo } from 'react';
import { Agent, EventLog, Alert, LedgerReport, HealthStatus, DashboardMetrics } from './types';
import {
  fetchHealth,
  fetchAgents,
  fetchEvents,
  fetchAlerts,
  verifyLedger,
} from './services/api';
import { Header } from './components/layout/Header';
import { ErrorMessage } from './components/common/ErrorMessage';
import { Dashboard } from './pages/Dashboard';
import { Alerts } from './pages/Alerts';
import { AttackLab } from './pages/AttackLab';

export default function App() {
  const [currentTab, setCurrentTab] = useState<'dashboard' | 'alerts' | 'attack_lab'>('dashboard');
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [events, setEvents] = useState<EventLog[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [ledgerReport, setLedgerReport] = useState<LedgerReport | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Core data loader
  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [hData, aData, eData, alData, lData] = await Promise.all([
        fetchHealth().catch(err => ({ status: 'error', error: err.message })),
        fetchAgents().catch(() => []),
        fetchEvents(100).catch(() => []),
        fetchAlerts(100).catch(() => []),
        verifyLedger().catch(err => ({ ok: false, checked: 0, chain_valid: false, errors: [err.message] })),
      ]);

      setHealth(hData as HealthStatus);
      setAgents(aData);
      setEvents(eData);
      setAlerts(alData);
      setLedgerReport(lData);
      setLastUpdated(new Date());
      setErrorMsg(null);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to communicate with AegisMesh Core API');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Polling loop
  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 4000);
    return () => clearInterval(interval);
  }, [loadData]);

  // Handle manual ledger verification
  const handleVerifyLedger = async () => {
    try {
      const report = await verifyLedger();
      setLedgerReport(report);
    } catch (err: any) {
      setErrorMsg(`Ledger verification failed: ${err.message}`);
    }
  };

  // Derive metrics strictly from backend telemetry
  const metrics: DashboardMetrics = useMemo(() => {
    const activeAgents = agents.filter(a => a.status === 'active').length;
    const quarantinedAgents = agents.filter(a => a.status === 'quarantined').length;
    const criticalAlerts = alerts.filter(a => a.severity === 'critical' || a.severity === 'high').length;
    const blockedActions = events.filter(e => {
      const d = (e.decision?.decision || '').toLowerCase();
      return d.includes('block') || d.includes('denied') || e.decision?.allowed === false;
    }).length;

    return {
      totalAgents: agents.length,
      activeAgents,
      quarantinedAgents,
      totalEvents: events.length,
      totalAlerts: alerts.length,
      criticalAlerts,
      blockedActions,
    };
  }, [agents, events, alerts]);

  const handleSelectAlert = (alert: Alert | null) => {
    setSelectedAlert(alert);
  };

  return (
    <div className="app-container">
      {/* SOC Navigation & System Health Header */}
      <Header
        currentTab={currentTab}
        onTabChange={setCurrentTab}
        health={health}
        activeAgentCount={metrics.activeAgents}
        totalAgentCount={metrics.totalAgents}
        alertCount={metrics.totalAlerts}
        criticalAlertCount={metrics.criticalAlerts}
        isRefreshing={isLoading}
        onRefresh={loadData}
        lastUpdated={lastUpdated}
      />

      {/* Global Error Banner */}
      {errorMsg && (
        <ErrorMessage
          message={errorMsg}
          onRetry={loadData}
        />
      )}

      {/* Main View Router */}
      <main className="app-main-content">
        {currentTab === 'dashboard' ? (
          <Dashboard
            agents={agents}
            events={events}
            alerts={alerts}
            ledgerReport={ledgerReport}
            metrics={metrics}
            isLoading={isLoading}
            onRefresh={loadData}
            onVerifyLedger={handleVerifyLedger}
            onNavigateToAlerts={() => setCurrentTab('alerts')}
            onSelectAlert={(alert) => {
              setSelectedAlert(alert);
              setCurrentTab('alerts');
            }}
          />
        ) : currentTab === 'alerts' ? (
          <Alerts
            alerts={alerts}
            agents={agents}
            isLoading={isLoading}
            onRefresh={loadData}
            selectedAlert={selectedAlert}
            onSelectAlert={handleSelectAlert}
            onInspectEvent={(_eventId) => {
              setCurrentTab('dashboard');
              // Switch to dashboard where the event stream is visible
            }}
          />
        ) : (
          <AttackLab
            agents={agents}
            isLoading={isLoading}
          />
        )}
      </main>
    </div>
  );
}
