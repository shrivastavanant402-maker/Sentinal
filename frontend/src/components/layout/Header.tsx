import React from 'react';
import { Shield, RefreshCw, Activity, AlertTriangle, Layers, Radio, FlaskConical, History } from 'lucide-react';
import { HealthStatus } from '../../types';
import { formatTimeIST } from '../../utils/time';

interface HeaderProps {
  currentTab: 'dashboard' | 'alerts' | 'attack_lab' | 'attack_replay';
  onTabChange: (tab: 'dashboard' | 'alerts' | 'attack_lab' | 'attack_replay') => void;
  health: HealthStatus | null;
  activeAgentCount: number;
  totalAgentCount: number;
  alertCount: number;
  criticalAlertCount: number;
  isRefreshing: boolean;
  onRefresh: () => void;
  lastUpdated: Date | null;
}

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  onTabChange,
  health,
  activeAgentCount,
  totalAgentCount,
  alertCount,
  criticalAlertCount,
  isRefreshing,
  onRefresh,
  lastUpdated,
}) => {
  const isHealthy = health && health.status === 'ok';

  return (
    <header className="app-header glass-card">
      <div className="brand-section">
        <div className="brand-logo-icon">
          <Shield size={24} className="text-white" />
        </div>
        <div>
          <div className="brand-title-row">
            <h1 className="brand-title">AegisMesh</h1>
            <span className="soc-badge">RUNTIME SOC</span>
          </div>
          <p className="brand-subtitle">Autonomous AI Agent Runtime Integrity & Mission Defense</p>
        </div>
      </div>

      <nav className="header-nav">
        <button
          onClick={() => onTabChange('dashboard')}
          className={`nav-tab ${currentTab === 'dashboard' ? 'nav-tab-active' : ''}`}
        >
          <Layers size={16} />
          <span>Dashboard & Live Ops</span>
        </button>

        <button
          onClick={() => onTabChange('alerts')}
          className={`nav-tab ${currentTab === 'alerts' ? 'nav-tab-active' : ''}`}
        >
          <AlertTriangle size={16} />
          <span>Alerts</span>
          {alertCount > 0 && (
            <span className={`nav-count-badge ${criticalAlertCount > 0 ? 'nav-count-critical' : ''}`}>
              {alertCount}
            </span>
          )}
        </button>

        <button
          onClick={() => onTabChange('attack_lab')}
          className={`nav-tab ${currentTab === 'attack_lab' ? 'nav-tab-active' : ''}`}
        >
          <FlaskConical size={16} />
          <span>Attack Lab</span>
        </button>

        <button
          onClick={() => onTabChange('attack_replay')}
          className={`nav-tab ${currentTab === 'attack_replay' ? 'nav-tab-active' : ''}`}
        >
          <History size={16} />
          <span>Attack Replay</span>
        </button>
      </nav>

      <div className="system-status-section">
        {/* Active Agents Indicator */}
        <div className="status-pill agent-count-pill" title="Active monitored agents">
          <Radio size={14} className={activeAgentCount > 0 ? 'text-emerald animate-pulse' : 'text-muted'} />
          <span className="font-mono text-sm">
            <strong className="text-white">{activeAgentCount}</strong>/{totalAgentCount} Agents Active
          </span>
        </div>

        {/* System Health Indicator */}
        <div
          className={`status-pill health-pill ${isHealthy ? 'health-ok' : 'health-down'}`}
          title={health ? `API: ${health.status} (${health.version || 'v0.1.0'})` : 'Checking system health...'}
        >
          <Activity size={14} className={isHealthy ? 'text-emerald' : 'text-rose'} />
          <span className="font-mono text-sm">
            {health ? (isHealthy ? 'CORE ONLINE' : 'CORE DEGRADED') : 'CONNECTING...'}
          </span>
        </div>

        {/* Refresh button */}
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="btn-refresh"
          title={`Click to refresh data. Last refreshed: ${lastUpdated ? formatTimeIST(lastUpdated) : 'never'}`}
        >
          <RefreshCw size={15} className={isRefreshing ? 'animate-spin text-accent' : 'text-secondary'} />
          <span className="text-xs text-muted font-mono hidden md:inline">
            {isRefreshing ? 'SYNCING' : lastUpdated ? formatTimeIST(lastUpdated) : 'REFRESH'}
          </span>
        </button>
      </div>
    </header>
  );
};
