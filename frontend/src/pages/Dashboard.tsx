import React from 'react';
import { Agent, EventLog, Alert, LedgerReport, DashboardMetrics } from '../types';
import { SummaryCards } from '../components/dashboard/SummaryCards';
import { AgentStatus } from '../components/dashboard/AgentStatus';
import { EventStream } from '../components/dashboard/EventStream';
import { AlertPanel } from '../components/dashboard/AlertPanel';
import { ActivityTimeline } from '../components/dashboard/ActivityTimeline';
import { LedgerStatus } from '../components/dashboard/LedgerStatus';

interface DashboardPageProps {
  agents: Agent[];
  events: EventLog[];
  alerts: Alert[];
  ledgerReport: LedgerReport | null;
  metrics: DashboardMetrics;
  isLoading: boolean;
  onRefresh: () => void;
  onVerifyLedger: () => Promise<void>;
  onNavigateToAlerts: () => void;
  onSelectAlert: (alert: Alert) => void;
}

export const Dashboard: React.FC<DashboardPageProps> = ({
  agents,
  events,
  alerts,
  ledgerReport,
  metrics,
  isLoading,
  onRefresh,
  onVerifyLedger,
  onNavigateToAlerts,
  onSelectAlert,
}) => {
  return (
    <div className="dashboard-content-flow">
      {/* 1. Cryptographic Ledger Proof Banner */}
      <LedgerStatus
        ledgerReport={ledgerReport}
        onVerifyLedger={onVerifyLedger}
      />

      {/* 2. Top Summary Metric Cards */}
      <SummaryCards
        metrics={metrics}
        ledgerReport={ledgerReport}
        onNavigateToAlerts={onNavigateToAlerts}
      />

      {/* 3. Primary Operations Grid: Monitored Agents & Live Alerts */}
      <div className="dashboard-grid-split">
        <div className="grid-col-agents">
          <AgentStatus
            agents={agents}
            isLoading={isLoading}
            onRefresh={onRefresh}
          />
        </div>

        <div className="grid-col-alerts">
          <AlertPanel
            alerts={alerts}
            isLoading={isLoading}
            onNavigateToAlerts={onNavigateToAlerts}
            onSelectAlert={onSelectAlert}
          />
        </div>
      </div>

      {/* 4. Live Event Interception Stream */}
      <div className="dashboard-stream-row">
        <EventStream
          events={events}
          isLoading={isLoading}
          onRefresh={onRefresh}
        />
      </div>

      {/* 5. Chronological Audit Trail & Activity Timeline */}
      <div className="dashboard-timeline-row">
        <ActivityTimeline
          events={events}
          alerts={alerts}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
};
