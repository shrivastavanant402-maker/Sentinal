import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import MetricsBar from './components/MetricsBar';
import AgentList from './components/AgentList';
import EventStream from './components/EventStream';
import LedgerStatus from './components/LedgerStatus';
import { fetchHealth, fetchAgents, fetchEvents, emitEvent, verifyLedger } from './services/api';

export default function App() {
  const [health, setHealth] = useState(null);
  const [agents, setAgents] = useState([]);
  const [events, setEvents] = useState([]);
  const [ledgerReport, setLedgerReport] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const loadData = useCallback(async () => {
    setIsRefreshing(true);
    setErrorMsg(null);
    try {
      const [hData, aData, eData, lData] = await Promise.all([
        fetchHealth().catch(err => ({ status: 'error', error: err.message })),
        fetchAgents().catch(() => []),
        fetchEvents().catch(() => []),
        verifyLedger().catch(err => ({ ok: false, checked: 0, chain_valid: false, errors: [err.message] })),
      ]);

      setHealth(hData);
      setAgents(aData);
      setEvents(eData);
      setLedgerReport(lData);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to communicate with AegisMesh Core API');
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    // Poll every 5s for live dashboard updates
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleVerifyLedger = async () => {
    try {
      const report = await verifyLedger();
      setLedgerReport(report);
    } catch (err) {
      setErrorMsg(`Verification failed: ${err.message}`);
    }
  };

  const handleTriggerAction = async (agent) => {
    try {
      let eventPayload = {};
      let action = 'custom.action';
      let eventType = 'tool_call_request';

      if (agent.role === 'planner') {
        eventType = 'plan_declared';
        action = 'plan.declare';
        eventPayload = {
          goal: 'Autonomous Vulnerability Discovery and Mitigation Workflow',
          total_steps: 2,
          steps: [
            { step: 1, agent: 'researcher-01', action: 'Search security repositories for CVEs' },
            { step: 2, agent: 'executor-01', action: 'Synthesize integrity audit report' },
          ],
        };
      } else if (agent.role === 'researcher') {
        eventType = 'tool_call_request';
        action = 'web.search';
        eventPayload = {
          tool: 'web.search',
          query: 'Autonomous AI agent runtime verification and cryptographic ledger',
          max_results: 5,
        };
      } else if (agent.role === 'executor') {
        eventType = 'tool_call_request';
        action = 'report.generate';
        eventPayload = {
          tool: 'report.generate',
          title: 'AegisMesh Runtime Security Assessment',
          classification: 'CONFIDENTIAL',
          output_format: 'markdown',
        };
      }

      await emitEvent({
        agent_id: agent.id,
        event_type: eventType,
        action: action,
        payload: eventPayload,
        session_id: 'session-demo-01',
      });

      // Reload state after emitting
      await loadData();
    } catch (err) {
      setErrorMsg(`Failed to dispatch event: ${err.message}`);
    }
  };

  return (
    <div className="app-container">
      <Header
        health={health}
        isRefreshing={isRefreshing}
        onRefresh={loadData}
      />

      {errorMsg && (
        <div style={{
          padding: '12px 16px',
          background: 'rgba(244, 63, 94, 0.15)',
          border: '1px solid rgba(244, 63, 94, 0.4)',
          borderRadius: '8px',
          color: '#fb7185',
          fontSize: '0.875rem'
        }}>
          {errorMsg}
        </div>
      )}

      <LedgerStatus
        ledgerReport={ledgerReport}
        onVerifyLedger={handleVerifyLedger}
      />

      <MetricsBar
        agentCount={agents.length}
        eventCount={events.length}
        ledgerReport={ledgerReport}
      />

      <main className="main-grid">
        <AgentList
          agents={agents}
          onTriggerAction={handleTriggerAction}
        />

        <EventStream
          events={events}
        />
      </main>
    </div>
  );
}
