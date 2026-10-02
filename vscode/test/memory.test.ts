import * as assert from 'node:assert/strict';
import { test } from 'node:test';
import { anchorArgument, lensesForFile, symbolAt, SymbolInfo, Fact, toIndexPath } from '../src/memory';

const symbols: SymbolInfo[] = [
  { id: 'm', path: 'pkg/app.py', name: 'app', kind: 'module', start_line: 1, content_hash: 'h0' },
  { id: 'a', path: 'pkg/app.py', name: 'parse', kind: 'function', start_line: 3, content_hash: 'h1' },
  { id: 'b', path: 'pkg/app.py', name: 'load', kind: 'function', start_line: 10, content_hash: 'h2' },
  { id: 'c', path: 'other.py', name: 'parse', kind: 'function', start_line: 1, content_hash: 'h3' },
];
const facts: Fact[] = [
  { id: 'f1', text: 'parse keeps casing', freshness: 'fresh', anchors: [{ symbol_id: 'a', content_hash: 'h1' }] },
  { id: 'f2', text: 'parse splits once', freshness: 'stale', anchors: [{ symbol_id: 'a', content_hash: 'old' }] },
  { id: 'f3', text: 'elsewhere', freshness: 'fresh', anchors: [{ symbol_id: 'c', content_hash: 'h3' }] },
];

test('lenses show the worst freshness first, only for this file', () => {
  const lenses = lensesForFile('pkg\\app.py', symbols, facts);
  assert.equal(lenses.length, 1);
  assert.equal(lenses[0].line, 2);
  assert.match(lenses[0].title, /^⚠ Smriti stale: parse splits once \(\+1 more\)$/);
  assert.deepEqual(lenses[0].factIds, ['f2', 'f1']);
});

test('symbolAt picks the nearest enclosing definition, not the module', () => {
  assert.equal(symbolAt('pkg/app.py', 12, symbols)?.id, 'b');
  assert.equal(symbolAt('pkg/app.py', 5, symbols)?.id, 'a');
  assert.equal(symbolAt('pkg/app.py', 1, symbols), undefined);
});

test('anchor argument and path normalization match the CLI', () => {
  assert.equal(anchorArgument(symbols[1]), 'a=h1');
  assert.equal(toIndexPath('.\\pkg\\app.py'), 'pkg/app.py');
});
