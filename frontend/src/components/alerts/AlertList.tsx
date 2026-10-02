import React from 'react';
import { Alert } from '../../types';
import { SeverityBadge } from '../common/SeverityBadge';
import { EmptyState } from '../common/EmptyState';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { Clock, ShieldCheck, ChevronRight } from 'lucide-react';

interface AlertListProps {
  alerts: Alert[];
  isLoading?: boolean;
  onSelectAlert: (alert: Alert) => void;
  onRefresh?: () => void;
}

export const AlertList: React.FC<AlertListProps> = ({
  alerts,
  isLoading = false,
  onSelectAlert,
  onRefresh,
}) => {
  const formatTimestamp = (iso?: string) => {
    if (!iso) return '—';
    try {
      const d = new Date(iso);
      return d.toLocaleString([], {
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return iso;
    }
  };

  if (isLoading && alerts.length === 0) {
    return (
      <div className="glass-card p-8">
        <LoadingSpinner label="Auditing security alerts from database..." />
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <div className="glass-card p-6">
        <EmptyState
          icon={ShieldCheck}
          title="No Alerts Detected"
          description="There are currently no security violations matching your filter criteria. All agents and tool calls comply with registered mission contracts."
          actionText="Refresh Alerts"
          onAction={onRefresh}
        />
      </div>
    );
  }

  return (
    <div className="alerts-table-container glass-card">
      <table className="alerts-table">
        <thead>
          <tr>
            <th style={{ width: '120px' }}>Severity</th>
            <th style={{ width: '180px' }}>Alert Type</th>
            <th style={{ width: '140px' }}>Agent</th>
            <th>Reason / Violation Details</th>
            <th style={{ width: '180px' }}>Timestamp</th>
            <th style={{ width: '120px' }}>Status</th>
            <th style={{ width: '130px' }} className="text-right">Action</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map(alert => {
            const isCritical = alert.severity === 'critical' || alert.severity === 'high';

            return (
              <tr
                key={alert.id}
                onClick={() => onSelectAlert(alert)}
                className={`alert-row cursor-pointer ${isCritical ? 'alert-row-critical' : ''}`}
                title="Click to view complete diagnostic telemetry"
              >
                <td>
                  <SeverityBadge severity={alert.severity} size="sm" />
                </td>
                <td>
                  <span className="font-mono text-xs font-semibold text-white">
                    {alert.alert_type}
                  </span>
                </td>
                <td>
                  <span className="font-mono text-xs text-cyan">
                    {alert.agent_id || 'SYSTEM'}
                  </span>
                </td>
                <td>
                  <div className="alert-reason-cell">
                    <span className="alert-reason-text text-sm text-secondary">
                      {alert.message}
                    </span>
                    {alert.event_id && (
                      <span className="event-ref-tag font-mono text-xs text-muted">
                        Event #{alert.event_id.slice(0, 8)}
                      </span>
                    )}
                  </div>
                </td>
                <td className="whitespace-nowrap font-mono text-xs text-muted">
                  <div className="flex items-center">
                    <Clock size={12} className="mr-1 text-muted" />
                    <span>{formatTimestamp(alert.created_at)}</span>
                  </div>
                </td>
                <td>
                  <span className="status-pill text-xs status-pill-active">
                    TRIGGERED
                  </span>
                </td>
                <td className="text-right">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectAlert(alert);
                    }}
                    className="btn btn-secondary btn-xs font-mono text-[11px] text-cyan hover:text-white inline-flex items-center gap-1"
                    title="Investigate incident in SOC console"
                  >
                    <span>Investigate</span>
                    <ChevronRight size={12} />
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
