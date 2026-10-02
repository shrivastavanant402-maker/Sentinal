import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
  title?: string;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({
  message,
  onRetry,
  title = 'Telemetry & API Connection Error',
}) => {
  return (
    <div className="error-alert-banner">
      <div className="error-icon-box">
        <AlertCircle size={20} className="text-rose" />
      </div>
      <div className="error-content">
        <div className="error-title">{title}</div>
        <div className="error-desc">{message}</div>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="btn btn-sm btn-outline-rose" title="Retry request">
          <RefreshCw size={14} className="mr-1" />
          Retry
        </button>
      )}
    </div>
  );
};
