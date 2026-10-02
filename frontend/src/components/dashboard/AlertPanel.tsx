import React from 'react';
import { Alert } from '../../types';
import { SeverityBadge } from '../common/SeverityBadge';
import { EmptyState } from '../common/EmptyState';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { AlertTriangle, ArrowRight, ShieldCheck, Clock } from 'lucide-react';

interface AlertPanelProps {
  alerts: Alert[];
  isLoading?: boolean;
  onNavigateToAlerts?: () => void;
  onSelectAlert?: (alert: Alert) => void;
}

export const AlertPanel: React.FC<AlertPanelProps> = ({
  alerts,
  isLoading = false,
  onNavigateToAlerts,
  onSelectAlert,
}) => {
  const recentAlerts = alerts.slice(0, 5);

  const formatTimestamp = (iso?: string) => {
    if (!iso) return '—';
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return iso;
    }
  };

  return (
    <div className="dashboard-panel glass-card">
      <div className="panel-header">
        <div className="panel-title-group">
          <div className="panel-icon-box bg-rose-glow">
            <AlertTriangle size={18} className="text-rose" />
          </div>
          <div>
            <h2 className="panel-title">Active Security Alerts</h2>
            <p className="panel-subtitle">Immediate policy violations, anomalies, and drift incidents</p>
          </div>
        </div>
        {onNavigateToAlerts && (
          <button
            onClick={onNavigateToAlerts}
            className="btn btn-sm btn-ghost text-xs text-accent font-medium flex items-center gap-1"
          >
            <span>View All ({alerts.length})</span>
            <ArrowRight size={13} />
          </button>
        )}
      </div>

      <div className="panel-body">
        {isLoading && alerts.length === 0 ? (
          <LoadingSpinner label="Auditing active alerts..." />
        ) : alerts.length === 0 ? (
          <EmptyState
            icon={ShieldCheck}
            title="Zero Active Security Incidents"
            description="The runtime integrity core has detected no policy violations, unauthorized tool accesses, or anomalies."
            compact
          />
        ) : (
          <div className="alerts-compact-list">
            {recentAlerts.map(alert => {
              const isCritical = alert.severity === 'critical' || alert.severity === 'high';

              return (
                <div
                  key={alert.id}
                  onClick={() => onSelectAlert && onSelectAlert(alert)}
                  className={`alert-compact-card ${isCritical ? 'alert-compact-critical' : ''} cursor-pointer hover:border-accent`}
                  title="Click to view details in alerts console"
                >
                  <div className="alert-compact-top">
                    <div className="alert-badge-group">
                      <SeverityBadge severity={alert.severity} size="sm" />
                      <span className="alert-type-text font-mono text-xs text-white">
                        {alert.alert_type}
                      </span>
                    </div>

                    <div className="alert-time-group font-mono text-xs text-muted flex items-center">
                      <Clock size={11} className="mr-1" />
                      <span>{formatTimestamp(alert.created_at)}</span>
                    </div>
                  </div>

                  <p className="alert-message-text text-sm text-secondary line-clamp-2">
                    {alert.message}
                  </p>

                  <div className="alert-compact-bottom font-mono text-xs text-muted">
                    <span>
                      Target Agent: <strong className="text-white">{alert.agent_id || 'SYSTEM'}</strong>
                    </span>
                    {alert.event_id && (
                      <span className="text-muted ml-3">
                        Event: #{alert.event_id.slice(0, 8)}
                      </span>
                    )}
                    <span className="alert-status-pill ml-auto">
                      TRIGGERED
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
