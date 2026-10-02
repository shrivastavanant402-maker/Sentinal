import React from 'react';
import { Search, Filter, AlertTriangle, AlertOctagon, AlertCircle, Info } from 'lucide-react';

interface AlertFiltersProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  selectedSeverity: string;
  onSeverityChange: (s: string) => void;
  selectedAgent: string;
  onAgentChange: (a: string) => void;
  availableAgents: string[];
  severityCounts: Record<string, number>;
}

export const AlertFilters: React.FC<AlertFiltersProps> = ({
  searchQuery,
  onSearchChange,
  selectedSeverity,
  onSeverityChange,
  selectedAgent,
  onAgentChange,
  availableAgents,
  severityCounts,
}) => {
  const severities: { id: string; label: string; icon: React.ReactNode; colorClass: string }[] = [
    { id: 'ALL', label: 'All Severities', icon: null, colorClass: '' },
    { id: 'critical', label: 'Critical', icon: <AlertOctagon size={13} className="text-rose" />, colorClass: 'border-rose' },
    { id: 'high', label: 'High', icon: <AlertTriangle size={13} className="text-amber" />, colorClass: 'border-amber' },
    { id: 'medium', label: 'Medium', icon: <AlertCircle size={13} className="text-amber" />, colorClass: 'border-yellow' },
    { id: 'low', label: 'Low', icon: <Info size={13} className="text-cyan" />, colorClass: 'border-cyan' },
  ];

  return (
    <div className="alerts-filter-bar glass-card">
      <div className="filter-top-row">
        {/* Search */}
        <div className="search-input-wrapper flex-1">
          <Search size={14} className="search-icon text-muted" />
          <input
            type="text"
            placeholder="Search alerts by reason, type, or agent..."
            value={searchQuery}
            onChange={e => onSearchChange(e.target.value)}
            className="search-input"
          />
        </div>

        {/* Agent Filter */}
        <div className="filter-select-wrapper">
          <Filter size={13} className="text-muted mr-1" />
          <select
            value={selectedAgent}
            onChange={e => onAgentChange(e.target.value)}
            className="filter-select font-mono text-xs"
          >
            <option value="ALL">All Agents</option>
            {availableAgents.map(ag => (
              <option key={ag} value={ag}>{ag}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Severity Filter Tabs */}
      <div className="severity-tabs-row">
        {severities.map(sev => {
          const count = sev.id === 'ALL'
            ? Object.values(severityCounts).reduce((a, b) => a + b, 0)
            : (severityCounts[sev.id] || 0);

          const isActive = selectedSeverity === sev.id;

          return (
            <button
              key={sev.id}
              onClick={() => onSeverityChange(sev.id)}
              className={`severity-tab ${isActive ? 'severity-tab-active' : ''}`}
            >
              {sev.icon}
              <span>{sev.label}</span>
              <span className={`count-pill ${isActive ? 'count-pill-active' : ''}`}>
                {count}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
