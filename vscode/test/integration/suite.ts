// Runs inside the VS Code extension host.
import * as assert from 'node:assert/strict';
import * as path from 'node:path';
import * as vscode from 'vscode';

export async function run(): Promise<void> {
  const root = vscode.workspace.workspaceFolders![0].uri.fsPath;
  const document = await vscode.workspace.openTextDocument(path.join(root, 'app.py'));
  await vscode.window.showTextDocument(document);
  let titles: string[] = [];
  for (let attempt = 0; attempt < 40 && titles.length === 0; attempt++) {
    const lenses = (await vscode.commands.executeCommand<vscode.CodeLens[]>(
      'vscode.executeCodeLensProvider',
      document.uri,
    )) ?? [];
    titles = lenses.map((lens) => lens.command?.title ?? '');
    if (titles.length === 0) await new Promise((resolve) => setTimeout(resolve, 500));
  }
  assert.deepEqual(titles, ['✓ Smriti fresh: parse_header keeps the original casing']);
  const commands = await vscode.commands.getCommands(true);
  assert.ok(commands.includes('smriti.remember') && commands.includes('smriti.refresh'));
}
