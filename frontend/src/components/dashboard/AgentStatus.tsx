import React, { useState } from 'react';
import { Agent } from '../../types';
import { formatTimeIST } from '../../utils/time';
import { StatusBadge } from '../common/StatusBadge';
import { EmptyState } from '../common/EmptyState';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { KeyRound, Shield, Wrench, Clock, ChevronDown, ChevronUp, Bot } from 'lucide-react';

interface AgentStatusProps {
  agents: Agent[];
  isLoading?: boolean;
  onRefresh?: () => void;
}

export const AgentStatus: React.FC<AgentStatusProps> = ({
  agents,
  isLoading = false,
  onRefresh,
}) => {
  const [expandedAgentId, setExpandedAgentId] = useState<string | null>(null);

  const toggleExpand = (agentId: string) => {
    setExpandedAgentId(prev => (prev === agentId ? null : agentId));
  };

  const getTrustScoreColor = (score: number) => {
    if (score >= 90) return 'text-emerald';
    if (score >= 70) return 'text-amber';
    return 'text-rose';
  };

  const getTrustScoreBarColor = (score: number) => {
    if (score >= 90) return 'bg-emerald';
    if (score >= 70) return 'bg-amber';
    return 'bg-rose';
  };

  const formatTime = (isoString?: string) => {
    if (!isoString) return 'Never';
    return formatTimeIST(isoString);
  };

  return (
    <div className="dashboard-panel glass-card">
      <div className="panel-header">
        <div className="panel-title-group">
          <div className="panel-icon-box bg-indigo-glow">
            <Bot size={18} className="text-indigo" />
          </div>
          <div>
            <h2 className="panel-title">Monitored Agents</h2>
            <p className="panel-subtitle">Identity, trust status, and runtime behavioral posture</p>
          </div>
        </div>
        <div className="panel-meta">
          <span className="font-mono text-xs text-muted">
            {agents.length} AGENTS REGISTERED
          </span>
        </div>
      </div>

      <div className="panel-body">
        {isLoading && agents.length === 0 ? (
          <LoadingSpinner label="Querying agent registry..." />
        ) : agents.length === 0 ? (
          <EmptyState
            icon={Bot}
            title="No Agents Registered"
            description="No autonomous agents are currently registered with AegisMesh. When agents boot, they will appear here automatically."
            actionText="Refresh Registry"
            onAction={onRefresh}
          />
        ) : (
          <div className="agent-cards-list">
            {agents.map(agent => {
              const isExpanded = expandedAgentId === agent.id;
              const trustScore = agent.trust_score ?? 100.0;
              const trustScoreColor = getTrustScoreColor(trustScore);
              const barColor = getTrustScoreBarColor(trustScore);

              return (
                <div
                  key={agent.id}
                  className={`agent-card ${agent.status === 'quarantined' ? 'agent-quarantined' : ''} ${isExpanded ? 'agent-card-expanded' : ''}`}
                >
                  <div className="agent-card-main">
                    <div className="agent-info-col">
                      <div className="agent-name-row">
                        <span className="agent-name">{agent.name}</span>
                        <span className="agent-id-tag font-mono text-xs">{agent.id}</span>
                        <span className="agent-role-pill font-mono text-xs">{agent.role.toUpperCase()}</span>
                      </div>
                      <div className="agent-meta-row">
                        <span className="agent-meta-item">
                          <Clock size={12} className="text-muted mr-1" />
                          <span className="text-muted text-xs">Updated:</span>{' '}
                          <span className="font-mono text-xs text-secondary">{formatTime(agent.updated_at)}</span>
                        </span>
                        {agent.public_key && (
                          <span className="agent-meta-item" title={`Public Key: ${agent.public_key}`}>
                            <KeyRound size={12} className="text-cyan mr-1" />
                            <span className="font-mono text-xs text-cyan">Ed25519 Verified</span>
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="agent-status-col">
                      <StatusBadge status={agent.status} />
                    </div>

                    <div className="agent-trust-col">
                      <div className="trust-score-header">
                        <span className="text-xs text-muted">Trust Score</span>
                        <span className={`font-mono text-xs font-bold ${trustScoreColor}`}>
                          {trustScore.toFixed(1)} / 100
                        </span>
                      </div>
                      <div className="trust-meter-track">
                        <div
                          className={`trust-meter-fill ${barColor}`}
                          style={{ width: `${Math.min(100, Math.max(0, trustScore))}%` }}
                        />
                      </div>
                    </div>

                    <button
                      onClick={() => toggleExpand(agent.id)}
                      className="btn-icon"
                      title={isExpanded ? 'Hide agent details' : 'Inspect agent details'}
                    >
                      {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                  </div>

                  {/* Expandable Agent Details */}
                  {isExpanded && (
                    <div className="agent-expanded-details">
                      <div className="details-section">
                        <div className="details-section-title">
                          <Wrench size={13} className="text-muted mr-1 inline" />
                          Authorized Capabilities
                        </div>
                        {agent.capabilities && agent.capabilities.length > 0 ? (
                          <div className="capabilities-badges">
                            {agent.capabilities.map(cap => (
                              <span key={cap} className="capability-pill font-mono text-xs">
                                {cap}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-muted text-xs font-mono">No specific capabilities listed</span>
                        )}
                      </div>

                      {agent.metadata && Object.keys(agent.metadata).length > 0 && (
                        <div className="details-section mt-2">
                          <div className="details-section-title">
                            <Shield size={13} className="text-muted mr-1 inline" />
                            Agent Metadata
                          </div>
                          <pre className="code-block text-xs font-mono">
                            {JSON.stringify(agent.metadata, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
