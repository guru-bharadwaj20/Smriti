import { execFile } from 'node:child_process';
import * as vscode from 'vscode';
import { anchorArgument, Fact, lensesForFile, symbolAt, SymbolInfo } from './memory';

function run(root: string, args: string[]): Promise<string> {
  const executable = vscode.workspace.getConfiguration('smriti').get<string>('executable', 'smriti');
  return new Promise((resolve, reject) => {
    execFile(executable, [...args, '--root', root], { maxBuffer: 64 * 1024 * 1024 }, (error, stdout, stderr) => {
      if (error) reject(new Error(stderr.trim() || error.message));
      else resolve(stdout);
    });
  });
}

class MemoryLenses implements vscode.CodeLensProvider {
  private readonly changed = new vscode.EventEmitter<void>();
  readonly onDidChangeCodeLenses = this.changed.event;
  private cache = new Map<string, { symbols: SymbolInfo[]; facts: Fact[] }>();

  refresh(): void {
    this.cache.clear();
    this.changed.fire();
  }

  async provideCodeLenses(document: vscode.TextDocument): Promise<vscode.CodeLens[]> {
    const folder = vscode.workspace.getWorkspaceFolder(document.uri);
    if (!folder) return [];
    const root = folder.uri.fsPath;
    let state = this.cache.get(root);
    if (!state) {
      try {
        const [symbols, facts] = await Promise.all([
          run(root, ['find-symbol', '']).then((out) => JSON.parse(out) as SymbolInfo[]),
          run(root, ['recall', '']).then((out) => JSON.parse(out) as Fact[]),
        ]);
        state = { symbols, facts };
        this.cache.set(root, state);
      } catch {
        return [];
      }
    }
    const relative = vscode.workspace.asRelativePath(document.uri, false);
    return lensesForFile(relative, state.symbols, state.facts).map((lens) => {
      const range = new vscode.Range(lens.line, 0, lens.line, 0);
      return new vscode.CodeLens(range, {
        title: lens.title,
        command: 'smriti.show',
        arguments: [state!.facts.filter((f) => lens.factIds.includes(f.id))],
      });
    });
  }
}

export function activate(context: vscode.ExtensionContext): void {
  const lenses = new MemoryLenses();
  context.subscriptions.push(
    vscode.languages.registerCodeLensProvider({ scheme: 'file' }, lenses),
    vscode.commands.registerCommand('smriti.show', async (facts: Fact[]) => {
      await vscode.window.showQuickPick(
        facts.map((f) => ({ label: f.text, description: `${f.freshness} · ${f.id}` })),
        { title: 'Smriti memory anchored here' },
      );
    }),
    vscode.commands.registerCommand('smriti.refresh', async () => {
      for (const folder of vscode.workspace.workspaceFolders ?? []) {
        await run(folder.uri.fsPath, ['index']);
      }
      lenses.refresh();
    }),
    vscode.commands.registerCommand('smriti.remember', async () => {
      const editor = vscode.window.activeTextEditor;
      const folder = editor && vscode.workspace.getWorkspaceFolder(editor.document.uri);
      if (!editor || !folder) return;
      const root = folder.uri.fsPath;
      if (editor.document.isDirty) await editor.document.save();
      await run(root, ['index']);
      const symbols = JSON.parse(await run(root, ['find-symbol', ''])) as SymbolInfo[];
      const relative = vscode.workspace.asRelativePath(editor.document.uri, false);
      const symbol = symbolAt(relative, editor.selection.active.line + 1, symbols);
      if (!symbol) {
        void vscode.window.showWarningMessage('Smriti: no indexed definition at the cursor.');
        return;
      }
      const text = await vscode.window.showInputBox({ prompt: `Fact about ${symbol.name}` });
      if (!text) return;
      await run(root, ['remember', text, '--anchor', anchorArgument(symbol)]);
      lenses.refresh();
      void vscode.window.showInformationMessage(`Smriti: remembered fact about ${symbol.name}.`);
    }),
    vscode.workspace.onDidSaveTextDocument(() => lenses.refresh()),
  );
}

export function deactivate(): void {}
