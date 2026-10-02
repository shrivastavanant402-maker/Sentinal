import React, { useState } from 'react';
import { Alert } from '../../types';
import { SeverityBadge } from '../common/SeverityBadge';
import { X, Clock, Bot, Hash, AlertTriangle, Copy, Check, Shield } from 'lucide-react';

interface AlertDetailModalProps {
  alert: Alert | null;
  onClose: () => void;
  onInspectEvent?: (eventId: string) => void;
}

export const AlertDetailModal: React.FC<AlertDetailModalProps> = ({
  alert,
  onClose,
  onInspectEvent,
}) => {
  const [copied, setCopied] = useState(false);

  if (!alert) return null;

  const copyId = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatTimestamp = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleString([], {
        year: 'numeric',
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

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content glass-card" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-group">
            <div className="panel-icon-box bg-rose-glow">
              <AlertTriangle size={20} className="text-rose" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <SeverityBadge severity={alert.severity} size="md" />
                <span className="font-mono text-sm font-semibold text-white">
                  {alert.alert_type}
                </span>
              </div>
              <span className="text-xs text-muted font-mono">ID: {alert.id}</span>
            </div>
          </div>

          <button onClick={onClose} className="btn-icon" title="Close modal">
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          {/* Reason / Message Box */}
          <div className="detail-section">
            <label className="detail-label">Incident Reason / Policy Violation</label>
            <div className="alert-message-box">
              <p className="text-sm text-white font-medium leading-relaxed">
                {alert.message}
              </p>
            </div>
          </div>

          {/* Metadata Grid */}
          <div className="modal-meta-grid">
            <div className="meta-box">
              <div className="meta-box-label">
                <Bot size={13} className="text-muted mr-1 inline" />
                Associated Agent
              </div>
              <div className="meta-box-value font-mono">
                {alert.agent_id || 'SYSTEM / GLOBAL'}
              </div>
            </div>

            <div className="meta-box">
              <div className="meta-box-label">
                <Clock size={13} className="text-muted mr-1 inline" />
                Timestamp
              </div>
              <div className="meta-box-value font-mono text-xs">
                {formatTimestamp(alert.created_at)}
              </div>
            </div>

            <div className="meta-box">
              <div className="meta-box-label">
                <Shield size={13} className="text-muted mr-1 inline" />
                Enforcement Status
              </div>
              <div className="meta-box-value">
                <span className="status-pill status-pill-active text-xs">
                  TRIGGERED / RECORDED
                </span>
              </div>
            </div>

            <div className="meta-box">
              <div className="meta-box-label">
                <Hash size={13} className="text-muted mr-1 inline" />
                Related Event ID
              </div>
              <div className="meta-box-value font-mono text-xs flex items-center justify-between">
                {alert.event_id ? (
                  <>
                    <span className="text-cyan truncate">{alert.event_id}</span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => copyId(alert.event_id!)}
                        className="btn-icon btn-icon-xs"
                        title="Copy Event ID"
                      >
                        {copied ? <Check size={12} className="text-emerald" /> : <Copy size={12} />}
                      </button>
                      {onInspectEvent && (
                        <button
                          onClick={() => onInspectEvent(alert.event_id!)}
                          className="btn-xs btn-outline-cyan"
                          title="View event in stream"
                        >
                          View
                        </button>
                      )}
                    </div>
                  </>
                ) : (
                  <span className="text-muted">None (Direct Sensor Alert)</span>
                )}
              </div>
            </div>
          </div>

          {/* Diagnostic Details */}
          {alert.details && Object.keys(alert.details).length > 0 && (
            <div className="detail-section mt-4">
              <label className="detail-label">Diagnostic Context & Telemetry Payload</label>
              <pre className="code-block text-xs font-mono max-h-56 overflow-auto">
                {JSON.stringify(alert.details, null, 2)}
              </pre>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <span className="font-mono text-xs text-muted">
            Evidence persisted to immutable audit ledger
          </span>
          <button onClick={onClose} className="btn btn-secondary">
            Close Console
          </button>
        </div>
      </div>
    </div>
  );
};
