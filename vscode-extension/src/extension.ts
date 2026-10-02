import * as vscode from 'vscode';
import { getConfig, onConfigChanged } from './config';
import { HealthClient } from './client/health';
import { EnforcementClient } from './client/enforcement';
import { MissionClient } from './client/mission';
import { AegisMeshStatusBar } from './ui/statusBar';
import { disposeOutputChannel } from './ui/outputChannel';
import { registerCommands } from './commands';

let statusBar: AegisMeshStatusBar | undefined;
let healthClient: HealthClient | undefined;
let enforcementClient: EnforcementClient | undefined;
let missionClient: MissionClient | undefined;

/**
 * Extension entry point. Called by VS Code when the extension is activated.
 */
export function activate(context: vscode.ExtensionContext): void {
  const config = getConfig();
  console.log(`[AegisMesh] Initializing extension for agent: ${config.agentId} (Core URL: ${config.backendUrl})`);

  // Initialize service singletons
  healthClient = new HealthClient();
  enforcementClient = new EnforcementClient();
  missionClient = new MissionClient();
  statusBar = new AegisMeshStatusBar();
  context.subscriptions.push(statusBar);

  // Register commands
  registerCommands(context, statusBar, healthClient, enforcementClient, missionClient);

  // Listen for configuration updates
  const configSub = onConfigChanged((newConfig) => {
    console.log(`[AegisMesh] Configuration updated: Backend=${newConfig.backendUrl}, Agent=${newConfig.agentId}`);
    // Trigger background check on config change without intrusive notification
    vscode.commands.executeCommand('aegismesh.checkConnection', false);
  });
  context.subscriptions.push(configSub);

  // Perform initial background connection probe
  vscode.commands.executeCommand('aegismesh.checkConnection', false);
}

/**
 * Extension cleanup. Called when the extension is deactivated.
 */
export function deactivate(): void {
  if (statusBar) {
    statusBar.dispose();
    statusBar = undefined;
  }
  disposeOutputChannel();
  healthClient = undefined;
  enforcementClient = undefined;
  missionClient = undefined;
}
