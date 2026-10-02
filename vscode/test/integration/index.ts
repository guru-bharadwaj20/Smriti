// Mocha-free entry point expected by @vscode/test-electron.
import { run as suite } from './suite';

export function run(): Promise<void> {
  return suite();
}
