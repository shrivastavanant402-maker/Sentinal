import React, { useState } from 'react';
import { View } from '../types/figma';
import {
  Terminal,
  Copy,
  Check,
  Cpu,
  Layers,
  FileCode,
  Lock,
  ArrowRight,
} from 'lucide-react';

interface IDEIntegrationProps {
  go?: (view: View) => void;
}

export const IDEIntegration: React.FC<IDEIntegrationProps> = ({ go }) => {
  const [activeTab, setActiveTab] = useState<'claude' | 'cursor' | 'vscode'>('cursor');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const copyToClipboard = async (text: string, key: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    } catch {
      // Fallback
    }
  };

  const cursorConfig = JSON.stringify(
    {
      mcpServers: {
        aegismesh: {
          command: "python",
          args: ["scripts/mcp_server.py"],
          env: {
            AEGISMESH_URL: "http://127.0.0.1:8000",
          },
        },
      },
    },
    null,
    2
  );

  const claudeConfig = JSON.stringify(
    {
      mcpServers: {
        aegismesh: {
          command: "python",
          args: ["scripts/mcp_server.py"],
          env: {
            AEGISMESH_URL: "http://127.0.0.1:8000",
          },
        },
      },
    },
    null,
    2
  );

  const vscodeConfig = JSON.stringify(
    {
      "mcp.servers": {
        aegismesh: {
          command: "python",
          args: ["scripts/mcp_server.py"],
          env: {
            AEGISMESH_URL: "http://127.0.0.1:8000",
          },
        },
      },
    },
    null,
    2
  );

  return (
    <div className="view-content" style={{ padding: '24px 28px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '6px',
                background: 'var(--accent-soft)',
                border: '1px solid var(--accent-border)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--accent-text)',
              }}
            >
              <Terminal size={18} />
            </div>
            <h1 style={{ margin: 0, fontSize: '20px', fontWeight: 600, color: 'var(--text)' }}>
              IDE / MCP Integration
            </h1>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                padding: '2px 8px',
                borderRadius: '4px',
                background: 'var(--success-soft)',
                color: 'var(--success-text)',
                border: '1px solid var(--success-border)',
              }}
            >
              Stdio Ready
            </span>
          </div>
          <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-2)' }}>
            Model Context Protocol (MCP) server adapter connecting external AI coding assistants and IDEs directly to AegisMesh Policy Enforcement Point (PEP).
          </p>
        </div>

        {go && (
          <button
            onClick={() => go('operations')}
            className="action-btn"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              fontSize: '12px',
              borderRadius: 'var(--radius)',
              background: 'var(--surface-raised)',
              border: '1px solid var(--border)',
              color: 'var(--text)',
              cursor: 'pointer',
            }}
          >
            Live Operations <ArrowRight size={13} />
          </button>
        )}
      </div>

      {/* Security Enforcement Callout */}
      <div
        style={{
          background: 'var(--surface-raised)',
          border: '1px solid var(--border)',
          borderLeft: '3px solid var(--accent)',
          borderRadius: 'var(--radius)',
          padding: '14px 18px',
          marginBottom: '24px',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '12px',
        }}
      >
        <Lock size={18} style={{ color: 'var(--accent)', marginTop: '2px', flexShrink: 0 }} />
        <div style={{ fontSize: '12.5px', lineHeight: 1.5, color: 'var(--text-2)' }}>
          <strong style={{ color: 'var(--text)', fontWeight: 600 }}>Zero-Bypass Policy Enforcement Gate: </strong>
          Every action submitted through the MCP adapter is routed directly into AegisMesh Core:
          <span style={{ fontFamily: 'monospace', color: 'var(--text)', margin: '0 4px' }}>
            Identity → Mission Contract → Policy → Trust → PEP Enforcement → Cryptographic Ledger
          </span>.
          No tools or commands are executed blindly without authoritative PEP authorization.
        </div>
      </div>

      {/* Grid: Tool Specification & Configuration */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: '20px', marginBottom: '24px' }}>
        {/* Card 1: Tool Specification */}
        <div
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '18px 20px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <Cpu size={16} style={{ color: 'var(--accent)' }} />
            <h2 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--text)' }}>
              Exposed MCP Tool Specification
            </h2>
          </div>

          <div
            style={{
              background: 'var(--surface-inset)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              padding: '12px',
              fontFamily: 'monospace',
              fontSize: '12px',
              color: 'var(--text)',
              marginBottom: '12px',
            }}
          >
            <div style={{ color: 'var(--accent-text)', fontWeight: 600, marginBottom: '4px' }}>
              tool: aegismesh_enforce
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-3)', marginBottom: '8px' }}>
              Enforces runtime policy and records cryptographic ledger evidence before executing an individual tool action.
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-2)' }}>
              <div><strong>agent_id:</strong> string (e.g. &quot;researcher-01&quot;)</div>
              <div><strong>action:</strong> string (e.g. &quot;web.search&quot;, &quot;shell.exec&quot;)</div>
              <div><strong>payload:</strong> object (optional)</div>
              <div><strong>mission_id:</strong> string (optional)</div>
              <div><strong>session_id:</strong> string (optional)</div>
            </div>
          </div>

          <div
            style={{
              background: 'var(--surface-inset)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              padding: '12px',
              fontFamily: 'monospace',
              fontSize: '12px',
              color: 'var(--text)',
              marginBottom: '14px',
            }}
          >
            <div style={{ color: 'var(--accent-text)', fontWeight: 600, marginBottom: '4px' }}>
              tool: aegismesh_run_mission
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-3)', marginBottom: '8px' }}>
              Executes a full multi-agent mission across Planner → Researcher → Executor. Every step is guarded by PEP enforcement.
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-2)' }}>
              <div><strong>goal:</strong> string (e.g. &quot;Research a topic and generate a report.&quot;)</div>
              <div><strong>mission_id:</strong> string (optional)</div>
              <div><strong>session_id:</strong> string (optional)</div>
            </div>
          </div>

          <div style={{ fontSize: '12px', color: 'var(--text-2)', lineHeight: 1.6 }}>
            <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: '6px' }}>Enforcement Outcomes:</div>
            <ul style={{ margin: 0, paddingLeft: '18px' }}>
              <li><strong style={{ color: 'var(--success-text)' }}>ALLOW / COMPLETED:</strong> Mission/action adheres to active mission contracts.</li>
              <li><strong style={{ color: 'var(--critical-text)' }}>BLOCK / BLOCKED:</strong> Unauthorized action, mission halts immediately.</li>
              <li><strong style={{ color: 'var(--warning-text)' }}>APPROVAL:</strong> High-risk action requiring administrator review.</li>
              <li><strong style={{ color: 'var(--critical-text)' }}>QUARANTINE:</strong> Agent isolated due to compromise or critical drift.</li>
            </ul>
          </div>
        </div>

        {/* Card 2: MCP Client Configuration */}
        <div
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '18px 20px',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Layers size={16} style={{ color: 'var(--accent)' }} />
              <h2 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--text)' }}>
                Client Configuration
              </h2>
            </div>

            {/* Client Tabs */}
            <div style={{ display: 'flex', background: 'var(--surface-muted)', borderRadius: '4px', padding: '2px' }}>
              <button
                onClick={() => setActiveTab('cursor')}
                style={{
                  padding: '3px 9px',
                  fontSize: '11px',
                  fontWeight: 500,
                  borderRadius: '3px',
                  border: 'none',
                  cursor: 'pointer',
                  background: activeTab === 'cursor' ? 'var(--surface)' : 'transparent',
                  color: activeTab === 'cursor' ? 'var(--text)' : 'var(--text-3)',
                }}
              >
                Cursor
              </button>
              <button
                onClick={() => setActiveTab('claude')}
                style={{
                  padding: '3px 9px',
                  fontSize: '11px',
                  fontWeight: 500,
                  borderRadius: '3px',
                  border: 'none',
                  cursor: 'pointer',
                  background: activeTab === 'claude' ? 'var(--surface)' : 'transparent',
                  color: activeTab === 'claude' ? 'var(--text)' : 'var(--text-3)',
                }}
              >
                Claude Desktop
              </button>
              <button
                onClick={() => setActiveTab('vscode')}
                style={{
                  padding: '3px 9px',
                  fontSize: '11px',
                  fontWeight: 500,
                  borderRadius: '3px',
                  border: 'none',
                  cursor: 'pointer',
                  background: activeTab === 'vscode' ? 'var(--surface)' : 'transparent',
                  color: activeTab === 'vscode' ? 'var(--text)' : 'var(--text-3)',
                }}
              >
                VS Code
              </button>
            </div>
          </div>

          <div style={{ position: 'relative', flex: 1 }}>
            <pre
              style={{
                margin: 0,
                background: 'var(--surface-inset)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
                padding: '12px',
                fontSize: '11.5px',
                fontFamily: 'monospace',
                color: 'var(--text)',
                overflowX: 'auto',
                lineHeight: 1.45,
                height: '190px',
              }}
            >
              {activeTab === 'cursor' ? cursorConfig : activeTab === 'claude' ? claudeConfig : vscodeConfig}
            </pre>
            <button
              onClick={() => {
                const text = activeTab === 'cursor' ? cursorConfig : activeTab === 'claude' ? claudeConfig : vscodeConfig;
                copyToClipboard(text, activeTab);
              }}
              style={{
                position: 'absolute',
                top: '8px',
                right: '8px',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                padding: '4px 8px',
                fontSize: '11px',
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: '4px',
                color: 'var(--text-2)',
                cursor: 'pointer',
              }}
            >
              {copiedKey === activeTab ? <Check size={12} style={{ color: 'var(--success)' }} /> : <Copy size={12} />}
              {copiedKey === activeTab ? 'Copied' : 'Copy JSON'}
            </button>
          </div>

          <div style={{ marginTop: '10px', fontSize: '11px', color: 'var(--text-3)' }}>
            {activeTab === 'cursor' && 'Add to .cursor/mcp.json in your workspace root, or Cursor Settings > Features > MCP.'}
            {activeTab === 'claude' && 'Add to %APPDATA%/Claude/claude_desktop_config.json on Windows, or ~/Library/Application Support/Claude on Mac.'}
            {activeTab === 'vscode' && 'Add to your VS Code MCP client extension configuration (e.g. Roo Code / Cline).'}
          </div>
        </div>
      </div>

      {/* Integration Walkthrough Steps */}
      <div
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: '18px 20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
          <FileCode size={16} style={{ color: 'var(--accent)' }} />
          <h2 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--text)' }}>
            Quickstart Workflow
          </h2>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '14px' }}>
          <div style={{ background: 'var(--surface-raised)', padding: '12px', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--accent)', marginBottom: '4px' }}>STEP 1</div>
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text)', marginBottom: '4px' }}>Start Core Backend</div>
            <div style={{ fontSize: '11px', color: 'var(--text-3)', lineHeight: 1.4 }}>
              FastAPI core daemon running on port 8000:
              <code style={{ display: 'block', background: 'var(--surface-inset)', padding: '2px 4px', borderRadius: '3px', marginTop: '4px' }}>
                uvicorn backend.app.main:app
              </code>
            </div>
          </div>

          <div style={{ background: 'var(--surface-raised)', padding: '12px', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--accent)', marginBottom: '4px' }}>STEP 2</div>
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text)', marginBottom: '4px' }}>Register MCP Server</div>
            <div style={{ fontSize: '11px', color: 'var(--text-3)', lineHeight: 1.4 }}>
              Copy the JSON snippet above into your IDE&apos;s MCP config file. The stdio protocol initiates automatically.
            </div>
          </div>

          <div style={{ background: 'var(--surface-raised)', padding: '12px', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--accent)', marginBottom: '4px' }}>STEP 3</div>
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text)', marginBottom: '4px' }}>Tool Enforced</div>
            <div style={{ fontSize: '11px', color: 'var(--text-3)', lineHeight: 1.4 }}>
              The AI assistant calls <span style={{ fontFamily: 'monospace' }}>aegismesh_enforce</span> with agent ID <span style={{ fontFamily: 'monospace' }}>researcher-01</span> before tool execution.
            </div>
          </div>

          <div style={{ background: 'var(--surface-raised)', padding: '12px', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--accent)', marginBottom: '4px' }}>STEP 4</div>
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text)', marginBottom: '4px' }}>Live SOC Audit</div>
            <div style={{ fontSize: '11px', color: 'var(--text-3)', lineHeight: 1.4 }}>
              Every evaluation produces a verifiable ledger event visible in the Operations, Alerts, and Ledger dashboards.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
