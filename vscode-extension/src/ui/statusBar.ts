import * as vscode from 'vscode';

export type ConnectionState = 'checking' | 'connected' | 'disconnected';

/**
 * Status bar controller for AegisMesh IDE integration.
 * Displays connection state and provides quick access to status inspection.
 */
export class AegisMeshStatusBar {
  private statusBarItem: vscode.StatusBarItem;
  private currentState: ConnectionState = 'checking';

  constructor() {
    this.statusBarItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Right,
      100
    );
    this.statusBarItem.command = 'aegismesh.showStatus';
    this.setChecking();
    this.statusBarItem.show();
  }

  /**
   * Sets the status bar to 'Checking...' state while probing backend health.
   */
  setChecking(): void {
    this.currentState = 'checking';
    this.statusBarItem.text = '$(sync~spin) AegisMesh: Checking...';
    this.statusBarItem.tooltip = 'Checking AegisMesh backend health...\nClick to show status';
    this.statusBarItem.backgroundColor = undefined;
  }

  /**
   * Sets the status bar to 'Connected' state upon successful health check.
   */
  setConnected(serviceName?: string, url?: string): void {
    this.currentState = 'connected';
    this.statusBarItem.text = '$(shield) AegisMesh: Connected';
    const detail = serviceName ? ` (${serviceName})` : '';
    const location = url ? `\nTarget: ${url}` : '';
    this.statusBarItem.tooltip = `AegisMesh Core is online & active${detail}${location}\nClick to show status`;
    this.statusBarItem.backgroundColor = undefined;
  }

  /**
   * Sets the status bar to 'Disconnected' state if backend is unreachable.
   */
  setDisconnected(errorMessage?: string, url?: string): void {
    this.currentState = 'disconnected';
    this.statusBarItem.text = '$(shield-slash) AegisMesh: Disconnected';
    const reason = errorMessage ? `\nReason: ${errorMessage}` : '';
    const location = url ? `\nTarget: ${url}` : '';
    this.statusBarItem.tooltip = `AegisMesh Core is unreachable${location}${reason}\nClick to inspect or reconnect`;
    this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
  }

  /**
   * Returns the current state string.
   */
  getState(): ConnectionState {
    return this.currentState;
  }

  /**
   * Disposes the status bar item.
   */
  dispose(): void {
    this.statusBarItem.dispose();
  }
}
