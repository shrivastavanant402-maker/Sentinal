import React, { useState, useMemo } from 'react';
import { EventLog } from '../../types';
import { formatTimeIST } from '../../utils/time';
import { DecisionBadge } from '../common/DecisionBadge';
import { EmptyState } from '../common/EmptyState';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { Activity, Search, Filter, Hash, ChevronDown, ChevronUp, Copy, Check, Shield } from 'lucide-react';

interface EventStreamProps {
  events: EventLog[];
  isLoading?: boolean;
  onRefresh?: () => void;
}

export const EventStream: React.FC<EventStreamProps> = ({
  events,
  isLoading = false,
  onRefresh,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAgent, setSelectedAgent] = useState<string>('ALL');
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  // Extract unique agents and event types for filter dropdowns
  const uniqueAgents = useMemo(() => {
    const set = new Set<string>();
    events.forEach(e => {
      if (e.agent_id) set.add(e.agent_id);
    });
    return Array.from(set).sort();
  }, [events]);

  const uniqueTypes = useMemo(() => {
    const set = new Set<string>();
    events.forEach(e => {
      if (e.event_type) set.add(e.event_type);
    });
    return Array.from(set).sort();
  }, [events]);

  // Filter events
  const filteredEvents = useMemo(() => {
    return events.filter(e => {
      if (selectedAgent !== 'ALL' && e.agent_id !== selectedAgent) return false;
      if (selectedType !== 'ALL' && e.event_type !== selectedType) return false;
      if (searchQuery.trim() !== '') {
        const query = searchQuery.toLowerCase();
        const matchAction = e.action.toLowerCase().includes(query);
        const matchAgent = e.agent_id.toLowerCase().includes(query);
        const matchType = e.event_type.toLowerCase().includes(query);
        const matchPayload = JSON.stringify(e.payload || {}).toLowerCase().includes(query);
        return matchAction || matchAgent || matchType || matchPayload;
      }
      return true;
    });
  }, [events, selectedAgent, selectedType, searchQuery]);

  const toggleExpand = (id: string) => {
    setExpandedEventId(prev => (prev === id ? null : id));
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(label);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const formatTimestamp = (iso?: string) => {
    return formatTimeIST(iso, { includeMs: true, includeTz: true });
  };

  return (
    <div className="dashboard-panel glass-card">
      <div className="panel-header">
        <div className="panel-title-group">
          <div className="panel-icon-box bg-cyan-glow">
            <Activity size={18} className="text-cyan" />
          </div>
          <div>
            <h2 className="panel-title">Live Event Stream</h2>
            <p className="panel-subtitle">Real-time intercepted tool executions, plans, and PEP decisions</p>
          </div>
        </div>
        <div className="panel-meta">
          <span className="font-mono text-xs text-muted">
            {filteredEvents.length} OF {events.length} EVENTS
          </span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="filter-bar">
        <div className="search-input-wrapper">
          <Search size={14} className="search-icon text-muted" />
          <input
            type="text"
            placeholder="Search action, payload, agent..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="filter-select-group">
          <div className="filter-select-wrapper">
            <Filter size={13} className="text-muted mr-1" />
            <select
              value={selectedAgent}
              onChange={e => setSelectedAgent(e.target.value)}
              className="filter-select font-mono text-xs"
            >
              <option value="ALL">All Agents</option>
              {uniqueAgents.map(ag => (
                <option key={ag} value={ag}>{ag}</option>
              ))}
            </select>
          </div>

          <div className="filter-select-wrapper">
            <select
              value={selectedType}
              onChange={e => setSelectedType(e.target.value)}
              className="filter-select font-mono text-xs"
            >
              <option value="ALL">All Event Types</option>
              {uniqueTypes.map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Event Stream Table */}
      <div className="panel-body no-padding">
        {isLoading && events.length === 0 ? (
          <LoadingSpinner label="Listening to event stream..." />
        ) : filteredEvents.length === 0 ? (
          <EmptyState
            icon={Activity}
            title={events.length === 0 ? 'No Events in Ledger' : 'No Events Match Filter'}
            description={
              events.length === 0
                ? 'No actions or tool calls have been logged to the ledger yet. When agents execute tasks, they will stream in real time.'
                : 'Try adjusting your search query or agent filter to view more events.'
            }
            actionText={events.length === 0 ? 'Refresh Stream' : 'Reset Filters'}
            onAction={events.length === 0 ? onRefresh : () => { setSearchQuery(''); setSelectedAgent('ALL'); setSelectedType('ALL'); }}
            compact
          />
        ) : (
          <div className="event-table-container">
            <table className="event-table">
              <thead>
                <tr>
                  <th style={{ width: '80px' }}>Seq</th>
                  <th style={{ width: '110px' }}>Time</th>
                  <th style={{ width: '130px' }}>Agent</th>
                  <th style={{ width: '150px' }}>Event Type</th>
                  <th>Action</th>
                  <th style={{ width: '110px' }}>Decision</th>
                  <th style={{ width: '90px' }}>Risk</th>
                  <th style={{ width: '50px' }}></th>
                </tr>
              </thead>
              <tbody>
                {filteredEvents.map(event => {
                  const isExpanded = expandedEventId === event.id;
                  const riskLevel = event.decision?.risk_level || event.decision?.risk || '—';
                  const riskScore = event.decision?.risk_score;

                  return (
                    <React.Fragment key={event.id || event.seq}>
                      <tr
                        onClick={() => toggleExpand(event.id)}
                        className={`event-row cursor-pointer ${isExpanded ? 'event-row-active' : ''}`}
                      >
                        <td className="font-mono text-xs text-muted">
                          #{event.seq}
                        </td>
                        <td className="font-mono text-xs text-secondary whitespace-nowrap">
                          {formatTimestamp(event.timestamp)}
                        </td>
                        <td>
                          <span className="font-mono text-xs font-semibold text-white">
                            {event.agent_id}
                          </span>
                        </td>
                        <td>
                          <span className="event-type-badge font-mono text-xs">
                            {event.event_type}
                          </span>
                        </td>
                        <td>
                          <span className="font-mono text-xs text-cyan font-medium">
                            {event.action}
                          </span>
                        </td>
                        <td>
                          <DecisionBadge decision={event.decision} />
                        </td>
                        <td>
                          {riskLevel !== '—' ? (
                            <span className={`risk-badge risk-${String(riskLevel).toLowerCase()} font-mono text-xs`}>
                              {String(riskLevel).toUpperCase()}
                              {riskScore !== undefined ? ` (${riskScore})` : ''}
                            </span>
                          ) : (
                            <span className="text-muted text-xs">—</span>
                          )}
                        </td>
                        <td className="text-right">
                          <button className="btn-icon">
                            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          </button>
                        </td>
                      </tr>

                      {/* Expanded View */}
                      {isExpanded && (
                        <tr className="event-detail-row">
                          <td colSpan={8}>
                            <div className="event-detail-content">
                              <div className="event-detail-grid">
                                {/* Left: Payload & Decision */}
                                <div className="event-detail-left">
                                  <div className="detail-box">
                                    <div className="detail-box-title">
                                      <span>Payload Parameters</span>
                                    </div>
                                    <pre className="code-block text-xs font-mono">
                                      {JSON.stringify(event.payload || {}, null, 2)}
                                    </pre>
                                  </div>

                                  {event.decision && Object.keys(event.decision).length > 0 && (
                                    <div className="detail-box mt-3">
                                      <div className="detail-box-title">
                                        <Shield size={13} className="text-indigo mr-1" />
                                        <span>PEP Evaluation & Policy Reason</span>
                                      </div>
                                      <pre className="code-block text-xs font-mono">
                                        {JSON.stringify(event.decision, null, 2)}
                                      </pre>
                                    </div>
                                  )}
                                </div>

                                {/* Right: Cryptographic Provenance */}
                                <div className="event-detail-right">
                                  <div className="detail-box">
                                    <div className="detail-box-title">
                                      <Hash size={13} className="text-cyan mr-1" />
                                      <span>Cryptographic Ledger Evidence</span>
                                    </div>

                                    <div className="crypto-hash-field">
                                      <span className="crypto-label">Event Hash (Block ID):</span>
                                      <div className="crypto-hash-value font-mono text-xs">
                                        <span className="truncate">{event.event_hash}</span>
                                        <button
                                          onClick={(e) => { e.stopPropagation(); copyToClipboard(event.event_hash, 'event'); }}
                                          className="btn-copy"
                                          title="Copy Event Hash"
                                        >
                                          {copiedHash === 'event' ? <Check size={12} className="text-emerald" /> : <Copy size={12} />}
                                        </button>
                                      </div>
                                    </div>

                                    <div className="crypto-hash-field mt-2">
                                      <span className="crypto-label">Previous Hash (Chain Link):</span>
                                      <div className="crypto-hash-value font-mono text-xs">
                                        <span className="truncate">{event.previous_hash}</span>
                                        <button
                                          onClick={(e) => { e.stopPropagation(); copyToClipboard(event.previous_hash, 'prev'); }}
                                          className="btn-copy"
                                          title="Copy Previous Hash"
                                        >
                                          {copiedHash === 'prev' ? <Check size={12} className="text-emerald" /> : <Copy size={12} />}
                                        </button>
                                      </div>
                                    </div>

                                    <div className="crypto-hash-field mt-2">
                                      <span className="crypto-label">Content SHA-256:</span>
                                      <div className="crypto-hash-value font-mono text-xs">
                                        <span className="truncate">{event.content_hash}</span>
                                        <button
                                          onClick={(e) => { e.stopPropagation(); copyToClipboard(event.content_hash, 'content'); }}
                                          className="btn-copy"
                                          title="Copy Content Hash"
                                        >
                                          {copiedHash === 'content' ? <Check size={12} className="text-emerald" /> : <Copy size={12} />}
                                        </button>
                                      </div>
                                    </div>

                                    {event.agent_signature && (
                                      <div className="crypto-hash-field mt-2">
                                        <span className="crypto-label">Agent Ed25519 Signature:</span>
                                        <div className="crypto-hash-value font-mono text-xs">
                                          <span className="truncate">{event.agent_signature}</span>
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
