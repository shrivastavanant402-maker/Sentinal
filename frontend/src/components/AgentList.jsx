import React, { useState } from 'react';
import { Bot, Play, Compass, Search, FileText, Check } from 'lucide-react';

export default function AgentList({ agents, onTriggerAction }) {
  const [triggering, setTriggering] = useState(null);

  const getAgentRoleColor = (role) => {
    switch (role?.toLowerCase()) {
      case 'planner':
        return { bg: 'rgba(99, 102, 241, 0.15)', text: '#818cf8', border: 'rgba(99, 102, 241, 0.3)' };
      case 'researcher':
        return { bg: 'rgba(6, 182, 212, 0.15)', text: '#22d3ee', border: 'rgba(6, 182, 212, 0.3)' };
      case 'executor':
        return { bg: 'rgba(16, 185, 129, 0.15)', text: '#34d399', border: 'rgba(16, 185, 129, 0.3)' };
      default:
        return { bg: 'rgba(148, 163, 184, 0.15)', text: '#cbd5e1', border: 'rgba(148, 163, 184, 0.3)' };
    }
  };

  const getAgentIcon = (role) => {
    switch (role?.toLowerCase()) {
      case 'planner': return <Compass size={18} />;
      case 'researcher': return <Search size={18} />;
      case 'executor': return <FileText size={18} />;
      default: return <Bot size={18} />;
    }
  };

  const handleAction = async (agent) => {
    setTriggering(agent.id);
    try {
      await onTriggerAction(agent);
    } finally {
      setTriggering(null);
    }
  };

  const getActionButtonLabel = (agent) => {
    switch (agent.role?.toLowerCase()) {
      case 'planner':
        return 'Declare Plan';
      case 'researcher':
        return 'Run Web Search';
      case 'executor':
        return 'Generate Report';
      default:
        return 'Emit Action';
    }
  };

  return (
    <div className="glass-card section-card">
      <div className="section-header">
        <div className="section-title">
          <Bot size={18} style={{ color: '#818cf8' }} />
          <span>Active Agents ({agents.length})</span>
        </div>
      </div>

      <div className="section-body">
        <div className="agent-list">
          {agents.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No agents registered yet.</p>
          ) : (
            agents.map((agent) => {
              const roleStyle = getAgentRoleColor(agent.role);
              const isActionRunning = triggering === agent.id;

              return (
                <div key={agent.id} className="agent-item">
                  <div className="agent-item-top">
                    <div className="agent-info">
                      <div className="agent-avatar" style={{ background: roleStyle.bg, color: roleStyle.text }}>
                        {getAgentIcon(agent.role)}
                      </div>
                      <div>
                        <div className="agent-name">{agent.name}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                          {agent.id}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span 
                        className="agent-role-pill"
                        style={{ background: roleStyle.bg, color: roleStyle.text, border: `1px solid ${roleStyle.border}` }}
                      >
                        {agent.role}
                      </span>
                      <span className="status-badge" style={{ padding: '2px 8px', fontSize: '0.6875rem' }}>
                        {agent.status}
                      </span>
                    </div>
                  </div>

                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    Capabilities: {agent.capabilities?.join(', ') || 'none'}
                  </div>

                  <div className="agent-action-row">
                    <button
                      className="btn btn-secondary btn-sm"
                      style={{ flex: 1 }}
                      onClick={() => handleAction(agent)}
                      disabled={isActionRunning}
                    >
                      {isActionRunning ? (
                        <span>Emitting Event...</span>
                      ) : (
                        <>
                          <Play size={12} />
                          <span>{getActionButtonLabel(agent)}</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
