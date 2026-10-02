import React from 'react';
import { AlertSeverity } from '../../types';
import { AlertCircle, AlertTriangle, AlertOctagon, Info } from 'lucide-react';

interface SeverityBadgeProps {
  severity: AlertSeverity | string;
  size?: 'sm' | 'md';
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity, size = 'md' }) => {
  const normalized = (severity || 'low').toLowerCase() as AlertSeverity;

  const configs: Record<AlertSeverity, { label: string; icon: React.ReactNode; className: string }> = {
    critical: {
      label: 'CRITICAL',
      icon: <AlertOctagon size={size === 'sm' ? 12 : 14} />,
      className: 'severity-critical',
    },
    high: {
      label: 'HIGH',
      icon: <AlertTriangle size={size === 'sm' ? 12 : 14} />,
      className: 'severity-high',
    },
    medium: {
      label: 'MEDIUM',
      icon: <AlertCircle size={size === 'sm' ? 12 : 14} />,
      className: 'severity-medium',
    },
    low: {
      label: 'LOW',
      icon: <Info size={size === 'sm' ? 12 : 14} />,
      className: 'severity-low',
    },
  };

  const config = configs[normalized] || configs.low;

  return (
    <span className={`severity-badge ${config.className} ${size === 'sm' ? 'text-xs' : ''}`}>
      {config.icon}
      <span>{config.label}</span>
    </span>
  );
};
