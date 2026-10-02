import React from 'react';
import { LucideIcon, Inbox } from 'lucide-react';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
  compact?: boolean;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = Inbox,
  title,
  description,
  actionText,
  onAction,
  compact = false,
}) => {
  return (
    <div className={`empty-state-container ${compact ? 'empty-state-compact' : ''}`}>
      <div className="empty-state-icon-wrapper">
        <Icon size={compact ? 24 : 36} className="empty-state-icon" />
      </div>
      <h4 className="empty-state-title">{title}</h4>
      <p className="empty-state-desc">{description}</p>
      {actionText && onAction && (
        <button onClick={onAction} className="btn btn-secondary mt-3">
          {actionText}
        </button>
      )}
    </div>
  );
};
