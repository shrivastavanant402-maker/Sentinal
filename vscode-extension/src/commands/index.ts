import * as vscode from 'vscode';
import { getConfig } from '../config';
import { HealthClient } from '../client/health';
import { AegisMeshStatusBar } from '../ui/statusBar';

/**
 * Registers all commands contributed by the AegisMesh extension.
 */
export function registerCommands(
  context: vscode.ExtensionContext,
  statusBar: AegisMeshStatusBar,
  healthClient: HealthClient
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
        'Configure Settings'
      );

      if (selection === 'Check Connection') {
        await vscode.commands.executeCommand('aegismesh.checkConnection', true);
      } else if (selection === 'Configure Settings') {
        vscode.commands.executeCommand(
          'workbench.action.openSettings',
          'aegismesh'
        );
      }
    }
  );

  context.subscriptions.push(checkConnectionCommand, showStatusCommand);
}
