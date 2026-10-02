import * as vscode from 'vscode';

export interface AegisMeshConfig {
  backendUrl: string;
  agentId: string;
}

export const DEFAULT_CONFIG: AegisMeshConfig = {
  backendUrl: 'http://127.0.0.1:8000',
  agentId: 'ide-agent-01',
};

/**
 * Retrieves the current AegisMesh extension configuration from VS Code settings.
 */
export function getConfig(): AegisMeshConfig {
  const configuration = vscode.workspace.getConfiguration('aegismesh');
  const backendUrl = configuration.get<string>('backendUrl', DEFAULT_CONFIG.backendUrl).trim().replace(/\/+$/, '');
  const agentId = configuration.get<string>('agentId', DEFAULT_CONFIG.agentId).trim();

  return {
    backendUrl: backendUrl || DEFAULT_CONFIG.backendUrl,
    agentId: agentId || DEFAULT_CONFIG.agentId,
  };
}

/**
 * Registers a listener for changes to the 'aegismesh' configuration section.
 */
export function onConfigChanged(listener: (config: AegisMeshConfig) => void): vscode.Disposable {
  return vscode.workspace.onDidChangeConfiguration((e) => {
    if (e.affectsConfiguration('aegismesh')) {
      listener(getConfig());
    }
  });
}
