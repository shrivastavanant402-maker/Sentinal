import * as vscode from 'vscode';
import { getConfig } from '../config';
import { HealthClient } from '../client/health';
import { EnforcementClient, ActionRequest } from '../client/enforcement';
import { AegisMeshStatusBar } from '../ui/statusBar';

/**
 * Registers all commands contributed by the AegisMesh extension.
 */
export function registerCommands(
  context: vscode.ExtensionContext,
  statusBar: AegisMeshStatusBar,
  healthClient: HealthClient,
  enforcementClient: EnforcementClient
): void {
  // ── Command: AegisMesh: Check Connection ─────────────────────────────────
  const checkConnectionCommand = vscode.commands.registerCommand(
    'aegismesh.checkConnection',
    async (showNotification = true) => {
      statusBar.setChecking();
      const config = getConfig();

      const result = await healthClient.check(config.backendUrl);

      if (result.ok) {
        const serviceName = result.data?.service || 'Runtime Integrity Core';
        statusBar.setConnected(serviceName, config.backendUrl);

        if (showNotification) {
          vscode.window.showInformationMessage(
            `AegisMesh Core is online and reachable at ${config.backendUrl} (${result.durationMs}ms). Service: ${serviceName}`
          );
        }
      } else {
        statusBar.setDisconnected(result.error, config.backendUrl);

        if (showNotification) {
          vscode.window.showWarningMessage(
            `AegisMesh backend could not be reached at ${config.backendUrl}: ${result.error || 'Connection failed'}. (Agent ID: ${config.agentId})`
          );
        }
      }

      return result;
    }
  );

  // ── Command: AegisMesh: Show Status ──────────────────────────────────────
  const showStatusCommand = vscode.commands.registerCommand(
    'aegismesh.showStatus',
    async () => {
      const config = getConfig();
      const state = statusBar.getState();
      const stateLabel =
        state === 'connected'
          ? 'Connected (Active)'
          : state === 'disconnected'
          ? 'Disconnected (Offline)'
          : 'Checking...';

      const selection = await vscode.window.showInformationMessage(
        `AegisMesh IDE Sentinel Status:\n` +
          `• State: ${stateLabel}\n` +
          `• Backend URL: ${config.backendUrl}\n` +
          `• Agent ID: ${config.agentId}`,
        'Check Connection',
        'Test Action',
        'Configure Settings'
      );

      if (selection === 'Check Connection') {
        await vscode.commands.executeCommand('aegismesh.checkConnection', true);
      } else if (selection === 'Test Action') {
        await vscode.commands.executeCommand('aegismesh.testAction');
      } else if (selection === 'Configure Settings') {
        vscode.commands.executeCommand(
          'workbench.action.openSettings',
          'aegismesh'
        );
      }
    }
  );

  // ── Command: AegisMesh: Test Action ──────────────────────────────────────
  const testActionCommand = vscode.commands.registerCommand(
    'aegismesh.testAction',
    async (providedAction?: string, providedCommand?: string, providedAgentId?: string) => {
      const config = getConfig();

      // 1. Prompt for action name (default: shell.exec)
      let action = providedAction;
      if (!action) {
        action = await vscode.window.showInputBox({
          title: 'AegisMesh: Test Action Name',
          prompt: 'Enter the action/tool name to submit to PEP /enforce',
          value: 'shell.exec',
        });
        if (!action) {
          return; // Cancelled
        }
      }

      // 2. Prompt for command / payload
      let commandStr = providedCommand;
      if (commandStr === undefined) {
        commandStr = await vscode.window.showInputBox({
          title: `AegisMesh: Action Payload for '${action}'`,
          prompt: 'Enter the command string or payload parameter',
          value: action === 'shell.exec' ? 'whoami' : '',
        });
        if (commandStr === undefined) {
          return; // Cancelled
        }
      }

      // 3. Agent ID (defaults to configured agentId, or parameter)
      const agentId = providedAgentId || config.agentId;

      const payload: Record<string, any> =
        action === 'shell.exec' ? { command: commandStr } : { input: commandStr };

      const actionRequest: ActionRequest = {
        agent_id: agentId,
        action,
        payload,
      };

      const result = await enforcementClient.enforce(actionRequest, config.backendUrl);

      if (!result.ok || !result.decision) {
        vscode.window.showErrorMessage(
          `AegisMesh enforcement request failed: ${result.error || 'Connection error'}`
        );
        return result;
      }

      const decision = result.decision;

      // Helper to display detailed breakdown modal
      const showDetailsModal = (sel?: string) => {
        if (sel === 'Inspect Details') {
          vscode.window.showInformationMessage(
            `AegisMesh PEP Decision Breakdown:\n` +
              `• Decision: ${decision.decision}\n` +
              `• Allowed: ${decision.allowed}\n` +
              `• Reason: ${decision.reason}\n` +
              `• Risk Level: ${decision.risk_level}\n` +
              `• Agent ID: ${decision.agent_id}\n` +
              `• Action: ${decision.action}\n` +
              `• Event ID: ${decision.event_id || 'None'}\n` +
              `• Details: ${JSON.stringify(decision.details || {})}`
          );
        }
      };

      // Format notification based on exact decision
      if (decision.decision === 'ALLOW') {
        const msg = `AegisMesh allowed ${decision.action}`;
        const p = vscode.window.showInformationMessage(msg, 'Inspect Details');
        if (p && typeof p.then === 'function') {
          p.then(showDetailsModal);
        }
      } else if (decision.decision === 'BLOCK') {
        const msg = `AegisMesh blocked ${decision.action} — ${decision.reason}`;
        const p = vscode.window.showErrorMessage(msg, 'Inspect Details');
        if (p && typeof p.then === 'function') {
          p.then(showDetailsModal);
        }
      } else if (decision.decision === 'APPROVAL') {
        const msg = `AegisMesh requires approval for ${decision.action}`;
        const p = vscode.window.showWarningMessage(msg, 'Inspect Details');
        if (p && typeof p.then === 'function') {
          p.then(showDetailsModal);
        }
      } else if (decision.decision === 'QUARANTINE') {
        const msg = `AegisMesh quarantined the agent: ${decision.agent_id} (${decision.reason})`;
        const p = vscode.window.showErrorMessage(msg, 'Inspect Details');
        if (p && typeof p.then === 'function') {
          p.then(showDetailsModal);
        }
      } else {
        const msg = `AegisMesh returned ${decision.decision} for ${decision.action} (${decision.reason})`;
        const p = vscode.window.showInformationMessage(msg, 'Inspect Details');
        if (p && typeof p.then === 'function') {
          p.then(showDetailsModal);
        }
      }

      return result;
    }
  );

  context.subscriptions.push(checkConnectionCommand, showStatusCommand, testActionCommand);
}
