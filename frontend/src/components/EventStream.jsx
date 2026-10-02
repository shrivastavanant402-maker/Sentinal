import React, { useState } from 'react';
import { ShieldCheck, ChevronDown, ChevronRight, Hash, Clock, ArrowRight } from 'lucide-react';

export default function EventStream({ events }) {
  const [expandedIds, setExpandedIds] = useState(new Set());

  const toggleExpand = (id) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const formatHash = (h) => {
    if (!h) return '—';
    if (h.length <= 16) return h;
    return `${h.slice(0, 10)}...${h.slice(-8)}`;
  };

  const formatTime = (ts) => {
    if (!ts) return '';
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return ts;
    }
  };

  return (
    <div className="glass-card section-card">
      <div className="section-header">
        <div className="section-title">
          <ShieldCheck size={18} style={{ color: '#34d399' }} />
          <span>Cryptographic Event Ledger ({events.length} Events)</span>
        </div>
      </div>

      <div className="section-body">
        {events.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            No events recorded yet. Click one of the agent actions to emit the first ledger entry!
          </p>
        ) : (
          <div className="event-stream-container">
            {events.map((ev) => {
              const isExpanded = expandedIds.has(ev.id);
              return (
                <div key={ev.id} className="event-item">
                  <div className="event-item-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span className="event-seq-badge">#{ev.seq}</span>
                      <span style={{ fontWeight: 600, fontSize: '0.875rem', color: '#f1f5f9' }}>
                        {ev.action}
                      </span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        ({ev.event_type})
                      </span>
                    </div>

                    <div className="event-meta">
                      <span style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Clock size={12} />
                        {formatTime(ev.timestamp)}
                      </span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: '#818cf8' }}>
                        {ev.agent_id}
                      </span>
                      <button
                        onClick={() => toggleExpand(ev.id)}
                        className="btn btn-secondary btn-sm"
                        style={{ padding: '2px 6px', background: 'transparent', border: 'none' }}
                        title="Toggle payload details"
                      >
                        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      </button>
                    </div>
                  </div>

                  {/* Hash chain verification block */}
                  <div className="hash-chain-box">
                    <div className="hash-row">
                      <span className="hash-label">Prev Hash:</span>
                      <span className="hash-val" title={ev.previous_hash}>{formatHash(ev.previous_hash)}</span>
                      <ArrowRight size={12} style={{ color: 'var(--text-muted)' }} />
                      <span className="hash-label" style={{ width: 'auto' }}>Event Hash:</span>
                      <span className="hash-val" style={{ color: '#34d399' }} title={ev.event_hash}>
                        {formatHash(ev.event_hash)}
                      </span>
                    </div>
                    <div className="hash-row">
                      <span className="hash-label">Content:</span>
                      <span className="hash-val" style={{ color: '#a78bfa' }} title={ev.content_hash}>
                        {formatHash(ev.content_hash)}
                      </span>
                    </div>
                  </div>

                  {/* Expanded JSON details */}
                  {isExpanded && (
                    <div style={{
                      marginTop: '8px',
                      padding: '10px',
                      background: 'rgba(5, 8, 14, 0.9)',
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                      fontFamily: 'var(--font-mono)',
                      overflowX: 'auto',
                      border: '1px solid rgba(255, 255, 255, 0.05)'
                    }}>
                      <div style={{ color: 'var(--text-muted)', marginBottom: '4px' }}>Payload:</div>
                      <pre style={{ color: '#38bdf8' }}>{JSON.stringify(ev.payload, null, 2)}</pre>
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
}
