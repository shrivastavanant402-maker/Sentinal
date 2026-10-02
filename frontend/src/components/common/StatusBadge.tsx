import React from 'react';
import { AgentStatus } from '../../types';
import { CheckCircle2, PauseCircle, StopCircle, ShieldAlert } from 'lucide-react';

interface StatusBadgeProps {
  status: AgentStatus | string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const normalized = (status || 'unknown').toLowerCase();

  const configs: Record<string, { label: string; icon: React.ReactNode; className: string }> = {
    active: {
      label: 'ACTIVE',
      icon: <CheckCircle2 size={size === 'sm' ? 12 : 14} />,
      className: 'badge-active',
    },
    paused: {
      label: 'PAUSED',
      icon: <PauseCircle size={size === 'sm' ? 12 : 14} />,
      className: 'badge-paused',
    },
    halted: {
      label: 'HALTED',
      icon: <StopCircle size={size === 'sm' ? 12 : 14} />,
      className: 'badge-halted',
    },
    quarantined: {
      label: 'QUARANTINED',
      icon: <ShieldAlert size={size === 'sm' ? 12 : 14} />,
      className: 'badge-quarantined',
    },
  };

  const config = configs[normalized] || {
    label: normalized.toUpperCase(),
    icon: null,
    className: 'badge-default',
  };

  return (
    <span className={`status-badge ${config.className} ${size === 'sm' ? 'text-xs py-0.5' : ''}`}>
      {config.icon}
      <span>{config.label}</span>
    </span>
  );
};
