import React from 'react';
import { Users, Activity, AlertTriangle, ShieldX, ShieldCheck } from 'lucide-react';
import { DashboardMetrics, LedgerReport } from '../../types';

interface SummaryCardsProps {
  metrics: DashboardMetrics;
  ledgerReport: LedgerReport | null;
  onNavigateToAlerts?: () => void;
}

export const SummaryCards: React.FC<SummaryCardsProps> = ({
  metrics,
  ledgerReport,
  onNavigateToAlerts,
}) => {
  const isChainValid = ledgerReport?.chain_valid === true;

  return (
    <div className="summary-cards-grid">
      {/* 1. Active Agents */}
      <div className="metric-card glass-card">
        <div className="metric-header">
          <span className="metric-title">Active Agents</span>
          <div className="metric-icon-box bg-indigo-glow">
            <Users size={18} className="text-indigo" />
          </div>
        </div>
        <div className="metric-value-row">
          <span className="metric-main-value">{metrics.activeAgents}</span>
          <span className="metric-secondary-value">/ {metrics.totalAgents} registered</span>
        </div>
        <div className="metric-footer">
          {metrics.quarantinedAgents > 0 ? (
            <span className="text-xs text-rose font-medium">
              ⚠ {metrics.quarantinedAgents} agent(s) quarantined
            </span>
          ) : (
            <span className="text-xs text-emerald font-medium">
              ✓ All agents operational
            </span>
          )}
        </div>
      </div>

      {/* 2. Total Events */}
      <div className="metric-card glass-card">
        <div className="metric-header">
          <span className="metric-title">Events Logged</span>
          <div className="metric-icon-box bg-cyan-glow">
            <Activity size={18} className="text-cyan" />
          </div>
        </div>
        <div className="metric-value-row">
          <span className="metric-main-value">{metrics.totalEvents}</span>
          <span className="metric-secondary-value">tamper-evident</span>
        </div>
        <div className="metric-footer">
          <span className="text-xs text-secondary font-mono">
            Append-only hash chain
          </span>
        </div>
      </div>

      {/* 3. Security Alerts */}
      <div
        className={`metric-card glass-card cursor-pointer hover:border-accent ${metrics.criticalAlerts > 0 ? 'border-rose-glow' : ''}`}
        onClick={onNavigateToAlerts}
        title="Click to view full alerts page"
      >
        <div className="metric-header">
          <span className="metric-title">Security Alerts</span>
          <div className={`metric-icon-box ${metrics.criticalAlerts > 0 ? 'bg-rose-glow' : 'bg-amber-glow'}`}>
            <AlertTriangle size={18} className={metrics.criticalAlerts > 0 ? 'text-rose' : 'text-amber'} />
          </div>
        </div>
        <div className="metric-value-row">
          <span className="metric-main-value">{metrics.totalAlerts}</span>
          {metrics.criticalAlerts > 0 && (
            <span className="metric-badge-critical">
              {metrics.criticalAlerts} CRITICAL
            </span>
          )}
        </div>
        <div className="metric-footer">
          {metrics.totalAlerts === 0 ? (
            <span className="text-xs text-emerald font-medium">✓ No policy violations</span>
          ) : (
            <span className="text-xs text-amber font-medium">→ Review incident alerts</span>
          )}
        </div>
      </div>

      {/* 4. Blocked Actions */}
      <div className="metric-card glass-card">
        <div className="metric-header">
          <span className="metric-title">Blocked Actions</span>
          <div className="metric-icon-box bg-rose-glow">
            <ShieldX size={18} className="text-rose" />
          </div>
        </div>
        <div className="metric-value-row">
          <span className="metric-main-value">{metrics.blockedActions}</span>
          <span className="metric-secondary-value">enforced by PEP</span>
        </div>
        <div className="metric-footer">
          <span className="text-xs text-muted">Zero unauthorized executions</span>
        </div>
      </div>

      {/* 5. Cryptographic Ledger Status */}
      <div className="metric-card glass-card">
        <div className="metric-header">
          <span className="metric-title">Ledger Integrity</span>
          <div className={`metric-icon-box ${isChainValid ? 'bg-emerald-glow' : 'bg-rose-glow'}`}>
            <ShieldCheck size={18} className={isChainValid ? 'text-emerald' : 'text-rose'} />
          </div>
        </div>
        <div className="metric-value-row">
          <span className={`text-base font-semibold ${isChainValid ? 'text-emerald' : 'text-rose'}`}>
            {isChainValid ? 'HASH CHAIN VERIFIED' : 'TAMPER / UNVERIFIED'}
          </span>
        </div>
        <div className="metric-footer">
          <span className="text-xs text-secondary font-mono">
            {ledgerReport ? `${ledgerReport.checked} blocks audited` : 'Connecting to ledger...'}
          </span>
        </div>
      </div>
    </div>
  );
};
