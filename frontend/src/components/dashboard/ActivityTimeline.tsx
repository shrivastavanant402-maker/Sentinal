import React from 'react';
import { EventLog, Alert } from '../../types';
import { Clock, ShieldAlert, Cpu, FileText, UserPlus, AlertOctagon } from 'lucide-react';
import { EmptyState } from '../common/EmptyState';

interface ActivityTimelineProps {
  events: EventLog[];
  alerts: Alert[];
  isLoading?: boolean;
}

interface TimelineItem {
  id: string;
  type: 'event' | 'alert';
  timestamp: string;
  agentId: string;
  title: string;
  subtitle: string;
  badge?: string;
  isWarning?: boolean;
  isCritical?: boolean;
}

export const ActivityTimeline: React.FC<ActivityTimelineProps> = ({
  events,
  alerts,
}) => {
  // Combine recent events and alerts into a unified sorted timeline
  const timelineItems: TimelineItem[] = React.useMemo(() => {
    const items: TimelineItem[] = [];

    // Add recent events (up to 15)
    events.slice(0, 15).forEach(e => {
      const isBlocked = e.decision?.decision?.toLowerCase()?.includes('block') || e.decision?.allowed === false;
      const isQuarantine = e.decision?.decision?.toLowerCase()?.includes('quarantine');

      items.push({
        id: `event-${e.id}`,
        type: 'event',
        timestamp: e.timestamp,
        agentId: e.agent_id,
        title: `${e.agent_id} → ${e.action}`,
        subtitle: `Event #${e.seq} (${e.event_type})`,
        badge: isQuarantine ? 'QUARANTINED' : isBlocked ? 'BLOCKED' : 'EXECUTED',
        isCritical: isQuarantine,
        isWarning: isBlocked,
      });
    });

    // Add recent alerts (up to 10)
    alerts.slice(0, 10).forEach(a => {
      const isCritical = a.severity === 'critical' || a.severity === 'high';
      items.push({
        id: `alert-${a.id}`,
        type: 'alert',
        timestamp: a.created_at,
        agentId: a.agent_id || 'SYSTEM',
        title: `ALERT: ${a.alert_type}`,
        subtitle: a.message,
        badge: a.severity.toUpperCase(),
        isCritical: isCritical,
        isWarning: !isCritical,
      });
    });

    // Sort descending by timestamp
    return items.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()).slice(0, 12);
  }, [events, alerts]);

  const formatTime = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return iso;
    }
  };

  const getItemIcon = (item: TimelineItem) => {
    if (item.type === 'alert') {
      return item.isCritical ? (
        <AlertOctagon size={14} className="text-rose" />
      ) : (
        <ShieldAlert size={14} className="text-amber" />
      );
    }
    if (item.badge === 'BLOCKED') {
      return <ShieldAlert size={14} className="text-rose" />;
    }
    if (item.title.includes('plan')) {
      return <FileText size={14} className="text-cyan" />;
    }
    if (item.title.includes('register')) {
      return <UserPlus size={14} className="text-indigo" />;
    }
    return <Cpu size={14} className="text-emerald" />;
  };

  return (
    <div className="dashboard-panel glass-card">
      <div className="panel-header">
        <div className="panel-title-group">
          <div className="panel-icon-box bg-indigo-glow">
            <Clock size={18} className="text-indigo" />
          </div>
          <div>
            <h2 className="panel-title">Audit Trail & Activity Timeline</h2>
            <p className="panel-subtitle">Chronological sequence of agent operations, decisions, and alerts</p>
          </div>
        </div>
      </div>

      <div className="panel-body">
        {timelineItems.length === 0 ? (
          <EmptyState
            icon={Clock}
            title="No Activity Logged"
            description="Timeline will populate as agents perform tasks and interceptor events are recorded."
            compact
          />
        ) : (
          <div className="timeline-container">
            {timelineItems.map((item, index) => (
              <div
                key={item.id}
                className={`timeline-item ${item.isCritical ? 'timeline-item-critical' : item.isWarning ? 'timeline-item-warning' : ''}`}
              >
                <div className="timeline-connector">
                  <div className={`timeline-dot ${item.isCritical ? 'dot-critical' : item.isWarning ? 'dot-warning' : 'dot-normal'}`}>
                    {getItemIcon(item)}
                  </div>
                  {index < timelineItems.length - 1 && <div className="timeline-line" />}
                </div>

                <div className="timeline-content">
                  <div className="timeline-meta-row">
                    <span className="timeline-time font-mono text-xs text-muted">
                      {formatTime(item.timestamp)}
                    </span>
                    <span className="timeline-agent font-mono text-xs">
                      {item.agentId}
                    </span>
                    {item.badge && (
                      <span className={`timeline-badge font-mono text-xs ${item.isCritical ? 'badge-quarantined' : item.isWarning ? 'badge-halted' : 'badge-active'}`}>
                        {item.badge}
                      </span>
                    )}
                  </div>

                  <div className="timeline-title font-mono text-sm text-white">
                    {item.title}
                  </div>
                  <div className="timeline-subtitle text-xs text-secondary line-clamp-1">
                    {item.subtitle}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
