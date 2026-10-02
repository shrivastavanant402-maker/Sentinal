import React from 'react';
import { Users, Activity, Link2, CheckCircle2, AlertTriangle } from 'lucide-react';

export default function MetricsBar({ agentCount, eventCount, ledgerReport }) {
  const isChainValid = ledgerReport?.chain_valid ?? true;

  return (
    <div className="metrics-grid">
      <div className="glass-card metric-card">
        <div className="metric-icon-wrapper" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8' }}>
          <Users size={22} />
        </div>
        <div>
          <div className="metric-value">{agentCount}</div>
          <div className="metric-label">Registered Agents</div>
        </div>
      </div>

      <div className="glass-card metric-card">
        <div className="metric-icon-wrapper" style={{ background: 'rgba(6, 182, 212, 0.15)', color: '#22d3ee' }}>
          <Activity size={22} />
        </div>
        <div>
          <div className="metric-value">{eventCount}</div>
          <div className="metric-label">Recorded Events</div>
        </div>
      </div>

      <div className="glass-card metric-card">
        <div className="metric-icon-wrapper" style={{ background: isChainValid ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)', color: isChainValid ? '#34d399' : '#fb7185' }}>
          {isChainValid ? <CheckCircle2 size={22} /> : <AlertTriangle size={22} />}
        </div>
        <div>
          <div className="metric-value" style={{ color: isChainValid ? '#34d399' : '#fb7185' }}>
            {isChainValid ? 'VERIFIED' : 'TAMPERED'}
          </div>
          <div className="metric-label">Ledger Integrity</div>
        </div>
      </div>

      <div className="glass-card metric-card">
        <div className="metric-icon-wrapper" style={{ background: 'rgba(139, 92, 246, 0.15)', color: '#a78bfa' }}>
          <Link2 size={22} />
        </div>
        <div>
          <div className="metric-value">{ledgerReport?.checked ?? 0}</div>
          <div className="metric-label">Chained Blocks Verified</div>
        </div>
      </div>
    </div>
  );
}
