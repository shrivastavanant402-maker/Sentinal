import React from 'react';
import { Check, X, ShieldAlert, Clock, AlertTriangle } from 'lucide-react';
import { EventDecision } from '../../types';

interface DecisionBadgeProps {
  decision?: EventDecision | Record<string, any>;
  size?: 'sm' | 'md';
}

export const DecisionBadge: React.FC<DecisionBadgeProps> = ({ decision, size = 'sm' }) => {
  if (!decision || Object.keys(decision).length === 0) {
    return (
      <span className="decision-badge decision-none">
        <span className="text-muted text-xs">—</span>
      </span>
    );
  }

  const rawDecision = (decision.decision || (decision.allowed === true ? 'allow' : decision.allowed === false ? 'block' : 'pending')).toString().toLowerCase();

  let label = rawDecision.toUpperCase();
  let className = 'decision-allow';
  let icon = <Check size={size === 'sm' ? 12 : 14} />;

  if (rawDecision.includes('block') || rawDecision.includes('denied') || rawDecision.includes('halt')) {
    label = 'BLOCKED';
    className = 'decision-block';
    icon = <X size={size === 'sm' ? 12 : 14} />;
  } else if (rawDecision.includes('quarantine')) {
    label = 'QUARANTINED';
    className = 'decision-quarantine';
    icon = <ShieldAlert size={size === 'sm' ? 12 : 14} />;
  } else if (rawDecision.includes('approval') || rawDecision.includes('require')) {
    label = 'APPROVAL REQ';
    className = 'decision-approval';
    icon = <Clock size={size === 'sm' ? 12 : 14} />;
  } else if (rawDecision.includes('sandbox') || rawDecision.includes('shadow')) {
    label = 'SANDBOXED';
    className = 'decision-sandbox';
    icon = <AlertTriangle size={size === 'sm' ? 12 : 14} />;
  } else if (rawDecision.includes('allow') || rawDecision.includes('permit')) {
    label = 'ALLOWED';
    className = 'decision-allow';
    icon = <Check size={size === 'sm' ? 12 : 14} />;
  }

  return (
    <span className={`decision-badge ${className}`}>
      {icon}
      <span>{label}</span>
    </span>
  );
};
