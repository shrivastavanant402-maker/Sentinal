import React from 'react';
import { Shield, RefreshCw, Database } from 'lucide-react';

export default function Header({ health, isRefreshing, onRefresh }) {
  const isHealthy = health?.status === 'healthy';
  const supabaseConnected = health?.supabase?.connected;

  return (
    <header className="glass-card app-header">
      <div className="brand-section">
        <div className="brand-logo-icon">
          <Shield size={24} />
        </div>
        <div>
          <h1 className="brand-title">AegisMesh</h1>
          <p className="brand-subtitle">Autonomous Agent Runtime Integrity System</p>
        </div>
      </div>

      <div className="header-status-group">
        <div className={`status-badge ${supabaseConnected ? '' : 'error'}`} title={health?.supabase?.message || health?.supabase?.error || 'Database Status'}>
          <Database size={14} />
          <span>{supabaseConnected ? 'Supabase Connected' : 'In-Memory / SQLite'}</span>
        </div>

        <div className={`status-badge ${isHealthy ? '' : 'error'}`}>
          <div className="status-dot"></div>
          <span>{isHealthy ? 'System Core Active' : 'System Degraded'}</span>
        </div>

        <button 
          className="btn btn-secondary btn-sm"
          onClick={onRefresh}
          disabled={isRefreshing}
          title="Refresh Dashboard Data"
        >
          <RefreshCw size={14} className={isRefreshing ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>
    </header>
  );
}
