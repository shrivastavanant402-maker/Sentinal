import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  label?: string;
  size?: number;
  inline?: boolean;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  label = 'Loading telemetry...',
  size = 24,
  inline = false,
}) => {
  if (inline) {
    return (
      <span className="inline-flex items-center gap-2 text-muted text-sm">
        <Loader2 size={size} className="animate-spin text-accent" />
        {label && <span>{label}</span>}
      </span>
    );
  }

  return (
    <div className="loading-spinner-container">
      <Loader2 size={size} className="animate-spin text-accent mb-2" />
      <span className="text-secondary text-sm font-mono">{label}</span>
    </div>
  );
};
