// Import mockVscode FIRST so require('vscode') is intercepted before any other modules load
import './mockVscode';

import { describe, it, before, after } from 'node:test';
import assert from 'node:assert';
import * as http from 'node:http';
import { HealthClient } from '../src/client/health';
import { EnforcementClient, ActionRequest } from '../src/client/enforcement';
import { AegisMeshStatusBar } from '../src/ui/statusBar';
import { DEFAULT_CONFIG, getConfig } from '../src/config';
import { activate, deactivate } from '../src/extension';
import { mockCommands, mockSubscriptions } from './mockVscode';

describe('AegisMesh VS Code Extension Foundation & Enforcement', () => {
  let mockServer: http.Server | undefined;
  let mockServerPort = 0;
  let shouldFail = false;

  before(async () => {
    // Start a lightweight mock HTTP server for deterministic testing
    mockServer = http.createServer(async (req, res) => {
      if (req.url === '/health' && req.method === 'GET') {
        if (shouldFail) {
          res.writeHead(500, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ status: 'unhealthy', error: 'Internal failure' }));
          return;
        }

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(
          JSON.stringify({
            status: 'healthy',
            service: 'AegisMesh Runtime Integrity Core (Mock)',
            environment: 'test',
            timestamp: new Date().toISOString(),
          })
        );
      } else if (req.url === '/enforce' && req.method === 'POST') {
        let bodyStr = '';
        req.on('data', (chunk) => {
          bodyStr += chunk;
        });
        req.on('end', () => {
          try {
            const body = JSON.parse(bodyStr || '{}') as ActionRequest;

            if (body.action === 'mock.500') {
              res.writeHead(500, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ detail: 'Internal enforcement error' }));
            } else if (body.action === 'mock.malformed') {
              res.writeHead(200, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ unexpected_payload: 123 }));
            } else if (body.action === 'mock.block') {
              res.writeHead(200, { 'Content-Type': 'application/json' });
              res.end(
                JSON.stringify({
                  decision: 'BLOCK',
                  allowed: false,
                  reason: 'POLICY_VIOLATION',
                  risk_level: 'critical',
                  agent_id: body.agent_id,
                  action: body.action,
                  event_id: 'ev-mock-block-001',
                  details: { rule: 'Block rule matched' },
                })
              );
            } else if (body.action === 'mock.approval') {
              res.writeHead(200, { 'Content-Type': 'application/json' });
              res.end(
                JSON.stringify({
                  decision: 'APPROVAL',
                  allowed: false,
                  reason: 'APPROVAL_REQUIRED',
                  risk_level: 'high',
                  agent_id: body.agent_id,
                  action: body.action,
                  event_id: 'ev-mock-approval-002',
                  details: { threshold: 'high_risk' },
                })
              );
            } else if (body.action === 'mock.quarantine') {
              res.writeHead(200, { 'Content-Type': 'application/json' });
              res.end(
                JSON.stringify({
                  decision: 'QUARANTINE',
                  allowed: false,
                  reason: 'AGENT_QUARANTINED',
                  risk_level: 'critical',
                  agent_id: body.agent_id,
                  action: body.action,
                  event_id: 'ev-mock-quarantine-003',
                  details: { message: 'Agent quarantined' },
                })
              );
            } else {
              // Default ALLOW response
              res.writeHead(200, { 'Content-Type': 'application/json' });
              res.end(
                JSON.stringify({
                  decision: 'ALLOW',
                  allowed: true,
                  reason: 'ALLOWED_BY_POLICY',
                  risk_level: 'low',
                  agent_id: body.agent_id,
                  action: body.action,
                  event_id: 'ev-mock-allow-000',
                  details: {},
                })
              );
            }
          } catch (e: any) {
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: e.message }));
          }
        });
      } else {
        res.writeHead(404);
        res.end();
      }
    });

    await new Promise<void>((resolve) => {
      mockServer!.listen(0, '127.0.0.1', () => {
        const address = mockServer!.address() as any;
        mockServerPort = address.port;
        resolve();
      });
    });
  });

  after(async () => {
    if (mockServer) {
      await new Promise<void>((resolve) => mockServer!.close(() => resolve()));
    }
  });

  // ── 1. Configuration tests ───────────────────────────────────────────────
  it('should define sensible development defaults for configuration', () => {
    assert.strictEqual(DEFAULT_CONFIG.backendUrl, 'http://127.0.0.1:8000');
    assert.strictEqual(DEFAULT_CONFIG.agentId, 'ide-agent-01');

    const config = getConfig();
    assert.strictEqual(config.backendUrl, 'http://127.0.0.1:8000');
    assert.strictEqual(config.agentId, 'ide-agent-01');
  });

  // ── 2. HealthClient: Success Handling ─────────────────────────────────────
  it('should successfully handle GET /health when backend is reachable', async () => {
    const client = new HealthClient();
    const result = await client.check(`http://127.0.0.1:${mockServerPort}`);

    assert.strictEqual(result.ok, true);
    assert.strictEqual(result.statusCode, 200);
    assert.strictEqual(result.data?.status, 'healthy');
    assert.strictEqual(result.data?.service, 'AegisMesh Runtime Integrity Core (Mock)');
    assert.strictEqual(result.error, undefined);
    assert.ok(result.durationMs >= 0);
  });

  // ── 3. HealthClient: Failure Handling ─────────────────────────────────────
  it('should gracefully handle connection refused without crashing', async () => {
    const client = new HealthClient();
    const result = await client.check('http://127.0.0.1:59999', 1000);

    assert.strictEqual(result.ok, false);
    assert.ok(result.error !== undefined);
    assert.strictEqual(result.data, undefined);
  });

  it('should handle HTTP error status codes gracefully', async () => {
    shouldFail = true;
    const client = new HealthClient();
    const result = await client.check(`http://127.0.0.1:${mockServerPort}`);
    shouldFail = false;

    assert.strictEqual(result.ok, false);
    assert.strictEqual(result.statusCode, 500);
    assert.ok(result.error?.includes('500'));
  });

  // ── 4. StatusBar Transitions ─────────────────────────────────────────────
  it('should properly transition status bar between checking, connected, and disconnected', () => {
    const statusBar = new AegisMeshStatusBar();

    // Initial state
    assert.strictEqual(statusBar.getState(), 'checking');

    // Transition to Connected
    statusBar.setConnected('Core', 'http://127.0.0.1:8000');
    assert.strictEqual(statusBar.getState(), 'connected');

    // Transition to Disconnected
    statusBar.setDisconnected('Connection refused', 'http://127.0.0.1:8000');
    assert.strictEqual(statusBar.getState(), 'disconnected');

    // Transition back to Checking
    statusBar.setChecking();
    assert.strictEqual(statusBar.getState(), 'checking');

    statusBar.dispose();
  });

  // ── 5. Extension Activation & Command Registration ───────────────────────
  it('should activate extension and register commands', async () => {
    const mockContext: any = {
      subscriptions: mockSubscriptions,
    };

    activate(mockContext);

    // Verify commands registered
    assert.ok(mockCommands.has('aegismesh.showStatus'));
    assert.ok(mockCommands.has('aegismesh.checkConnection'));
    assert.ok(mockCommands.has('aegismesh.testAction'));

    // Clean up
    deactivate();
  });

  // ── 6. EnforcementClient Tests (Checkpoint B Requirements) ───────────────
  it('should handle /enforce success with ALLOW', async () => {
    const client = new EnforcementClient();
    const req: ActionRequest = {
      agent_id: 'ide-agent-01',
      action: 'mock.allow',
      payload: { command: 'echo hello' },
    };

    const res = await client.enforce(req, `http://127.0.0.1:${mockServerPort}`);
    assert.strictEqual(res.ok, true);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.decision?.decision, 'ALLOW');
    assert.strictEqual(res.decision?.allowed, true);
    assert.strictEqual(res.decision?.reason, 'ALLOWED_BY_POLICY');
    assert.strictEqual(res.decision?.risk_level, 'low');
    assert.strictEqual(res.decision?.event_id, 'ev-mock-allow-000');
  });

  it('should handle /enforce with BLOCK', async () => {
    const client = new EnforcementClient();
    const req: ActionRequest = {
      agent_id: 'ide-agent-01',
      action: 'mock.block',
      payload: { command: 'rm -rf /' },
    };

    const res = await client.enforce(req, `http://127.0.0.1:${mockServerPort}`);
    assert.strictEqual(res.ok, true);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.decision?.decision, 'BLOCK');
    assert.strictEqual(res.decision?.allowed, false);
    assert.strictEqual(res.decision?.reason, 'POLICY_VIOLATION');
    assert.strictEqual(res.decision?.risk_level, 'critical');
    assert.strictEqual(res.decision?.event_id, 'ev-mock-block-001');
  });

  it('should handle /enforce with APPROVAL', async () => {
    const client = new EnforcementClient();
    const req: ActionRequest = {
      agent_id: 'ide-agent-01',
      action: 'mock.approval',
      payload: { command: 'deploy.prod' },
    };

    const res = await client.enforce(req, `http://127.0.0.1:${mockServerPort}`);
    assert.strictEqual(res.ok, true);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.decision?.decision, 'APPROVAL');
    assert.strictEqual(res.decision?.allowed, false);
    assert.strictEqual(res.decision?.reason, 'APPROVAL_REQUIRED');
    assert.strictEqual(res.decision?.risk_level, 'high');
  });

  it('should handle /enforce with QUARANTINE', async () => {
    const client = new EnforcementClient();
    const req: ActionRequest = {
      agent_id: 'ide-agent-01',
      action: 'mock.quarantine',
      payload: { command: 'rogue.behavior' },
    };

    const res = await client.enforce(req, `http://127.0.0.1:${mockServerPort}`);
    assert.strictEqual(res.ok, true);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.decision?.decision, 'QUARANTINE');
    assert.strictEqual(res.decision?.allowed, false);
    assert.strictEqual(res.decision?.reason, 'AGENT_QUARANTINED');
    assert.strictEqual(res.decision?.risk_level, 'critical');
  });

  it('should handle /enforce HTTP 500 error gracefully', async () => {
    const client = new EnforcementClient();
    const req: ActionRequest = {
      agent_id: 'ide-agent-01',
      action: 'mock.500',
    };

    const res = await client.enforce(req, `http://127.0.0.1:${mockServerPort}`);
    assert.strictEqual(res.ok, false);
    assert.strictEqual(res.statusCode, 500);
    assert.ok(res.error?.includes('500'));
    assert.strictEqual(res.decision, undefined);
  });

  it('should handle /enforce connection failure gracefully', async () => {
    const client = new EnforcementClient();
    const req: ActionRequest = {
      agent_id: 'ide-agent-01',
      action: 'shell.exec',
    };

    const res = await client.enforce(req, 'http://127.0.0.1:59999', 1000);
    assert.strictEqual(res.ok, false);
    assert.ok(res.error !== undefined);
    assert.strictEqual(res.decision, undefined);
  });

  it('should handle /enforce malformed/unexpected backend response', async () => {
    const client = new EnforcementClient();
    const req: ActionRequest = {
      agent_id: 'ide-agent-01',
      action: 'mock.malformed',
    };

    const res = await client.enforce(req, `http://127.0.0.1:${mockServerPort}`);
    assert.strictEqual(res.ok, false);
    assert.ok(res.error?.includes('Malformed'));
    assert.strictEqual(res.decision, undefined);
  });

  // ── 7. Command Execution: testAction ─────────────────────────────────────
  it('should execute aegismesh.testAction command successfully', async () => {
    const mockContext: any = {
      subscriptions: mockSubscriptions,
    };
    activate(mockContext);

    const testCmd = mockCommands.get('aegismesh.testAction');
    assert.ok(testCmd);

    // Call test command directly passing parameters
    const res = await testCmd('mock.allow', 'echo hello', 'ide-agent-01');
    assert.ok(res);
    assert.strictEqual(res.ok, true);

    deactivate();
  });

  // ── 8. Live Backend Integration ──────────────────────────────────────────
  it('should query live local backend on port 8000 when available', async () => {
    const client = new HealthClient();
    const result = await client.check('http://127.0.0.1:8000');
    if (result.ok) {
      assert.strictEqual(result.data?.status, 'healthy');
      assert.strictEqual(result.data?.service, 'AegisMesh Runtime Integrity Core');
    }
  });

  it('should submit live action to real backend and receive real decision', async () => {
    const healthClient = new HealthClient();
    const health = await healthClient.check('http://127.0.0.1:8000');
    if (!health.ok) return;

    const enforcementClient = new EnforcementClient();

    // 1. Test real registered agent with permitted action (ALLOW)
    const allowReq: ActionRequest = {
      agent_id: 'researcher-01',
      action: 'web.search',
      payload: { query: 'threat intelligence' },
    };
    const allowRes = await enforcementClient.enforce(allowReq, 'http://127.0.0.1:8000');
    assert.strictEqual(allowRes.ok, true);
    assert.strictEqual(allowRes.decision?.decision, 'ALLOW');
    assert.strictEqual(allowRes.decision?.allowed, true);
    assert.ok(allowRes.decision?.event_id !== undefined);

    // 2. Test real registered agent with contract forbidden action (BLOCK)
    const blockReq: ActionRequest = {
      agent_id: 'researcher-01',
      action: 'shell.exec',
      payload: { command: 'cat /etc/passwd' },
    };
    const blockRes = await enforcementClient.enforce(blockReq, 'http://127.0.0.1:8000');
    assert.strictEqual(blockRes.ok, true);
    assert.strictEqual(blockRes.decision?.decision, 'BLOCK');
    assert.strictEqual(blockRes.decision?.allowed, false);

    // 3. Test unregistered IDE agent (BLOCK by identity)
    const unregReq: ActionRequest = {
      agent_id: 'ide-agent-01',
      action: 'shell.exec',
      payload: { command: 'echo test' },
    };
    const unregRes = await enforcementClient.enforce(unregReq, 'http://127.0.0.1:8000');
    assert.strictEqual(unregRes.ok, true);
    assert.strictEqual(unregRes.decision?.decision, 'BLOCK');
    assert.strictEqual(unregRes.decision?.allowed, false);
    assert.strictEqual(unregRes.decision?.reason, 'INVALID_IDENTITY');
  });
});
