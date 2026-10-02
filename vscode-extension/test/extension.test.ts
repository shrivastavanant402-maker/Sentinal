// Import mockVscode FIRST so require('vscode') is intercepted before any other modules load
import './mockVscode';

import { describe, it, before, after } from 'node:test';
import assert from 'node:assert';
import * as http from 'node:http';
import { HealthClient } from '../src/client/health';
import { EnforcementClient, ActionRequest } from '../src/client/enforcement';
import { MissionClient, MissionResult } from '../src/client/mission';
import { AegisMeshStatusBar } from '../src/ui/statusBar';
import { formatMissionOutput, getOutputChannel } from '../src/ui/outputChannel';
import { DEFAULT_CONFIG, getConfig } from '../src/config';
import { activate, deactivate } from '../src/extension';
import { mockCommands, mockSubscriptions, mockConfigValues, mockOutputChannels } from './mockVscode';

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
      } else if ((req.url === '/missions/run' || req.url === '/api/v1/missions/run') && req.method === 'POST') {
        let bodyStr = '';
        req.on('data', (chunk) => {
          bodyStr += chunk;
        });
        req.on('end', () => {
          try {
            const body = JSON.parse(bodyStr || '{}');

            if (body.goal === 'mock.500') {
              res.writeHead(500, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ detail: 'Internal mission execution error' }));
            } else if (body.goal === 'test.blocked') {
              res.writeHead(200, { 'Content-Type': 'application/json' });
              res.end(
                JSON.stringify({
                  mission_id: 'mission-mock-block-001',
                  session_id: 'session-mock-block-001',
                  goal: body.goal,
                  status: 'BLOCKED',
                  planner_result: null,
                  researcher_result: null,
                  executor_result: null,
                  execution_trace: [
                    {
                      step: 1,
                      agent_id: 'planner-01',
                      action: 'task.delegate',
                      status: 'BLOCKED',
                      decision: 'BLOCKED',
                      reason: 'POLICY_VIOLATION',
                      risk: 'critical',
                      event_id: 'evt-mock-block-001',
                      error: 'Action prohibited by contract',
                    },
                  ],
                  event_ids: ['evt-mock-block-001'],
                  error: 'Action prohibited by contract',
                  error_details: { reason: 'POLICY_VIOLATION' },
                })
              );
            } else {
              res.writeHead(200, { 'Content-Type': 'application/json' });
              res.end(
                JSON.stringify({
                  mission_id: 'mission-mock-happy-100',
                  session_id: 'session-mock-happy-100',
                  goal: body.goal,
                  status: 'COMPLETED',
                  planner_result: { status: 'delegated', target_agent: 'researcher-01' },
                  researcher_result: { status: 'success', results: ['Intel 1', 'Intel 2'] },
                  executor_result: { status: 'generated', content: 'AegisMesh briefing' },
                  execution_trace: [
                    {
                      step: 1,
                      agent_id: 'planner-01',
                      action: 'task.delegate',
                      status: 'ALLOW',
                      decision: 'ALLOW',
                      reason: 'ALLOWED_BY_POLICY',
                      risk: 'low',
                      event_id: 'evt-mock-plan-101',
                    },
                    {
                      step: 2,
                      agent_id: 'researcher-01',
                      action: 'web.search',
                      status: 'ALLOW',
                      decision: 'ALLOW',
                      reason: 'ALLOWED_BY_POLICY',
                      risk: 'low',
                      event_id: 'evt-mock-res-102',
                    },
                    {
                      step: 3,
                      agent_id: 'executor-01',
                      action: 'report.generate',
                      status: 'ALLOW',
                      decision: 'ALLOW',
                      reason: 'ALLOWED_BY_POLICY',
                      risk: 'low',
                      event_id: 'evt-mock-exec-103',
                    },
                  ],
                  event_ids: [
                    'evt-mock-plan-101',
                    'evt-mock-res-102',
                    'evt-mock-exec-103',
                  ],
                  error: null,
                  error_details: null,
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
      if (typeof (mockServer as any).closeAllConnections === 'function') {
        (mockServer as any).closeAllConnections();
      }
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
    mockConfigValues.set('aegismesh.backendUrl', `http://127.0.0.1:${mockServerPort}`);
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

  // ── 9. Mission Control Tests ─────────────────────────────────────────────
  it('should contribute and register aegismesh.runMission command', () => {
    assert.strictEqual(mockCommands.has('aegismesh.runMission'), true);
  });

  it('should handle empty or whitespace mission goal input by rejecting gracefully', async () => {
    const runMission = mockCommands.get('aegismesh.runMission');
    assert.ok(runMission);

    // Empty string
    const res1 = await runMission('');
    assert.strictEqual(res1, undefined);

    // Whitespace string
    const res2 = await runMission('   ');
    assert.strictEqual(res2, undefined);
  });

  it('should handle successful mission response and write real IDs to output channel', async () => {
    mockConfigValues.set('aegismesh.backendUrl', `http://127.0.0.1:${mockServerPort}`);
    const runMission = mockCommands.get('aegismesh.runMission');
    assert.ok(runMission);

    const goal = 'Analyze supply chain integrity';
    const result = await runMission(goal);

    assert.ok(result);
    assert.strictEqual(result.ok, true);
    assert.strictEqual(result.data?.status, 'COMPLETED');
    assert.strictEqual(result.data?.mission_id, 'mission-mock-happy-100');
    assert.strictEqual(result.data?.event_ids.length, 3);

    // Verify output channel contains real mission and event IDs
    const channel = mockOutputChannels.get('AegisMesh');
    assert.ok(channel);
    const text = channel.lines.join('\n');
    assert.ok(text.includes('Mission: mission-mock-happy-100'));
    assert.ok(text.includes('Mission Status: COMPLETED'));
    assert.ok(text.includes('evt-mock-plan-101'));
    assert.ok(text.includes('evt-mock-res-102'));
    assert.ok(text.includes('evt-mock-exec-103'));
  });

  it('should handle blocked mission response correctly', async () => {
    mockConfigValues.set('aegismesh.backendUrl', `http://127.0.0.1:${mockServerPort}`);
    const runMission = mockCommands.get('aegismesh.runMission');
    assert.ok(runMission);

    const result = await runMission('test.blocked');
    assert.ok(result);
    assert.strictEqual(result.ok, true);
    assert.strictEqual(result.data?.status, 'BLOCKED');
    assert.strictEqual(result.data?.mission_id, 'mission-mock-block-001');
    assert.strictEqual(result.data?.error, 'Action prohibited by contract');

    const channel = mockOutputChannels.get('AegisMesh');
    assert.ok(channel);
    const text = channel.lines.join('\n');
    assert.ok(text.includes('Mission Status: BLOCKED'));
    assert.ok(text.includes('Error: Action prohibited by contract'));
    assert.ok(text.includes('evt-mock-block-001'));
  });

  it('should handle failed backend request gracefully', async () => {
    mockConfigValues.set('aegismesh.backendUrl', `http://127.0.0.1:${mockServerPort}`);
    const runMission = mockCommands.get('aegismesh.runMission');
    assert.ok(runMission);

    // HTTP 500 error from backend
    const res500 = await runMission('mock.500');
    assert.ok(res500);
    assert.strictEqual(res500.ok, false);
    assert.strictEqual(res500.statusCode, 500);

    // Unreachable port
    mockConfigValues.set('aegismesh.backendUrl', 'http://127.0.0.1:1');
    const resUnreach = await runMission('unreachable.test');
    assert.ok(resUnreach);
    assert.strictEqual(resUnreach.ok, false);
    assert.ok(resUnreach.error?.length);
  });

  it('should format mission output correctly for both COMPLETED and BLOCKED states', () => {
    const successResult: MissionResult = {
      mission_id: 'mission-fmt-1',
      session_id: 'session-fmt-1',
      goal: 'Format test goal',
      status: 'COMPLETED',
      execution_trace: [
        {
          step: 1,
          agent_id: 'planner-01',
          action: 'task.delegate',
          status: 'ALLOW',
          decision: 'ALLOW',
          reason: 'ALLOWED_BY_POLICY',
          risk: 'low',
          event_id: 'evt-fmt-1',
        },
      ],
      event_ids: ['evt-fmt-1'],
    };

    const formattedSuccess = formatMissionOutput(successResult);
    assert.ok(formattedSuccess.includes('AegisMesh Mission'));
    assert.ok(formattedSuccess.includes('Mission: mission-fmt-1'));
    assert.ok(formattedSuccess.includes('Session: session-fmt-1'));
    assert.ok(formattedSuccess.includes('Goal:\nFormat test goal'));
    assert.ok(formattedSuccess.includes('Execution Trace'));
    assert.ok(formattedSuccess.includes('[1] planner-01'));
    assert.ok(formattedSuccess.includes('Action: task.delegate'));
    assert.ok(formattedSuccess.includes('Decision: ALLOW'));
    assert.ok(formattedSuccess.includes('Reason: ALLOWED_BY_POLICY'));
    assert.ok(formattedSuccess.includes('Risk: low'));
    assert.ok(formattedSuccess.includes('Event ID: evt-fmt-1'));
    assert.ok(formattedSuccess.includes('Mission Status: COMPLETED'));
    assert.ok(formattedSuccess.includes('Event IDs:\nevt-fmt-1'));

    const blockedResult: MissionResult = {
      mission_id: 'mission-fmt-2',
      session_id: 'session-fmt-2',
      goal: 'Blocked test goal',
      status: 'BLOCKED',
      execution_trace: [
        {
          step: 1,
          agent_id: 'planner-01',
          action: 'task.delegate',
          status: 'BLOCKED',
          decision: 'BLOCKED',
          reason: 'FORBIDDEN_ACTION',
          risk: 'critical',
          event_id: 'evt-fmt-2',
          error: 'Action forbidden',
        },
      ],
      event_ids: ['evt-fmt-2'],
      error: 'Action forbidden by policy',
    };

    const formattedBlocked = formatMissionOutput(blockedResult);
    assert.ok(formattedBlocked.includes('Mission Status: BLOCKED'));
    assert.ok(formattedBlocked.includes('Error: Action forbidden by policy'));
    assert.ok(formattedBlocked.includes('Event ID: evt-fmt-2'));
  });

  it('should run real live mission end-to-end against backend port 8000 when available', async () => {
    const healthClient = new HealthClient();
    const health = await healthClient.check('http://127.0.0.1:8000');
    if (!health.ok) return;

    mockConfigValues.set('aegismesh.backendUrl', 'http://127.0.0.1:8000');
    const runMission = mockCommands.get('aegismesh.runMission');
    assert.ok(runMission);

    const liveResult = await runMission('Live E2E VS Code Sentinel Integration Mission');
    assert.ok(liveResult);
    assert.strictEqual(liveResult.ok, true);
    assert.strictEqual(liveResult.data?.status, 'COMPLETED');
    assert.ok(liveResult.data?.mission_id.length);
    assert.strictEqual(liveResult.data?.event_ids.length, 3);

    for (const eid of liveResult.data?.event_ids || []) {
      assert.ok(eid.length > 0);
    }
  });
});
