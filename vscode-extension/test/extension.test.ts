// Import mockVscode FIRST so require('vscode') is intercepted before any other modules load
import './mockVscode';

import { describe, it, before, after } from 'node:test';
import assert from 'node:assert';
import * as http from 'node:http';
import { HealthClient } from '../src/client/health';
import { AegisMeshStatusBar } from '../src/ui/statusBar';
import { DEFAULT_CONFIG, getConfig } from '../src/config';
import { activate, deactivate } from '../src/extension';
import { mockCommands, mockSubscriptions } from './mockVscode';

describe('AegisMesh VS Code Extension Foundation', () => {
  let mockServer: http.Server | undefined;
  let mockServerPort = 0;
  let shouldFail = false;

  before(async () => {
    // Start a lightweight mock HTTP server for deterministic health testing
    mockServer = http.createServer((req, res) => {
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
    // Query an unused local port
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

    // Execute checkConnection command against mock server
    const checkCmd = mockCommands.get('aegismesh.checkConnection');
    assert.ok(checkCmd);

    // Clean up
    deactivate();
  });

  // ── 6. Live Backend Integration ──────────────────────────────────────────
  it('should query live local backend on port 8000 when available', async () => {
    const client = new HealthClient();
    const result = await client.check('http://127.0.0.1:8000');
    if (result.ok) {
      assert.strictEqual(result.data?.status, 'healthy');
      assert.strictEqual(result.data?.service, 'AegisMesh Runtime Integrity Core');
    }
  });
});
