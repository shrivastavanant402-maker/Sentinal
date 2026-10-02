// Minimal mock of the vscode API for unit testing extension logic in pure Node.
import Module from 'module';

export const mockSubscriptions: any[] = [];
export const mockCommands: Map<string, (...args: any[]) => any> = new Map();
export const mockConfigValues: Map<string, any> = new Map();

export const StatusBarAlignment = {
  Left: 1,
  Right: 2,
};

export class ThemeColor {
  constructor(public id: string) {}
}

export class MockStatusBarItem {
  text = '';
  tooltip = '';
  command = '';
  backgroundColor: ThemeColor | undefined;
  visible = false;

  show() {
    this.visible = true;
  }
  hide() {
    this.visible = false;
  }
  dispose() {
    this.visible = false;
  }
}

export const window = {
  createStatusBarItem: (_alignment: any, _priority?: number) => {
    return new MockStatusBarItem();
  },
  showInformationMessage: async (_message: string, ..._items: string[]) => {
    return _items[0];
  },
  showWarningMessage: async (_message: string, ..._items: string[]) => {
    return _items[0];
  },
  showErrorMessage: async (_message: string, ..._items: string[]) => {
    return _items[0];
  },
};

export const commands = {
  registerCommand: (command: string, callback: (...args: any[]) => any) => {
    mockCommands.set(command, callback);
    return {
      dispose: () => mockCommands.delete(command),
    };
  },
  executeCommand: async (command: string, ...args: any[]) => {
    const handler = mockCommands.get(command);
    if (handler) {
      return handler(...args);
    }
    return undefined;
  },
};

export const workspace = {
  getConfiguration: (section?: string) => {
    return {
      get: <T>(key: string, defaultValue?: T): T => {
        const fullKey = section ? `${section}.${key}` : key;
        if (mockConfigValues.has(fullKey)) {
          return mockConfigValues.get(fullKey);
        }
        return defaultValue as T;
      },
    };
  },
  onDidChangeConfiguration: (_listener: (e: any) => void) => {
    return { dispose: () => {} };
  },
};

const mockVscodeInstance = {
  StatusBarAlignment,
  ThemeColor,
  window,
  commands,
  workspace,
};

// Hook Node's module loader so require('vscode') resolves cleanly in unit tests
const originalRequire = (Module.prototype as any).require;
(Module.prototype as any).require = function (id: string) {
  if (id === 'vscode') {
    return mockVscodeInstance;
  }
  return originalRequire.apply(this, arguments);
};
