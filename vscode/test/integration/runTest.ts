import * as path from 'node:path';
import { runTests } from '@vscode/test-electron';

async function main(): Promise<void> {
  // Terminals hosted by VS Code export this, which would make Code.exe run as plain Node.
  delete process.env.ELECTRON_RUN_AS_NODE;
  const workspace = process.argv[2];
  if (!workspace) throw new Error('usage: node runTest.js <indexed workspace>');
  await runTests({
    extensionDevelopmentPath: path.resolve(__dirname, '../../..'),
    extensionTestsPath: path.resolve(__dirname, 'index'),
    launchArgs: [workspace, '--disable-extensions'],
  });
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
