// Pure helpers shared by the extension and its tests; no VS Code dependency.

export interface Anchor {
  symbol_id: string;
  content_hash: string;
}

export interface Fact {
  id: string;
  text: string;
  freshness: 'fresh' | 'stale' | 'orphaned' | string;
  anchors: Anchor[];
}

export interface SymbolInfo {
  id: string;
  path: string;
  name: string;
  kind: string;
  start_line: number;
  content_hash: string;
}

export interface Lens {
  line: number;
  title: string;
  factIds: string[];
}

const ICON: Record<string, string> = { fresh: '✓', stale: '⚠', orphaned: '✗' };

/** Normalize a workspace-relative path the way Smriti stores it. */
export function toIndexPath(relative: string): string {
  return relative.replace(/\\/g, '/').replace(/^\.\//, '');
}

/** One lens per symbol in `path` that has anchored facts, worst freshness first. */
export function lensesForFile(path: string, symbols: SymbolInfo[], facts: Fact[]): Lens[] {
  const wanted = toIndexPath(path);
  const bySymbol = new Map<string, Fact[]>();
  for (const fact of facts) {
    for (const anchor of fact.anchors) {
      const list = bySymbol.get(anchor.symbol_id) ?? [];
      list.push(fact);
      bySymbol.set(anchor.symbol_id, list);
    }
  }
  const rank = (f: Fact) => (f.freshness === 'fresh' ? 2 : f.freshness === 'stale' ? 1 : 0);
  const lenses: Lens[] = [];
  for (const symbol of symbols) {
    const anchored = bySymbol.get(symbol.id);
    if (symbol.path !== wanted || !anchored) continue;
    anchored.sort((a, b) => rank(a) - rank(b) || a.id.localeCompare(b.id));
    const first = anchored[0];
    const more = anchored.length > 1 ? ` (+${anchored.length - 1} more)` : '';
    lenses.push({
      line: Math.max(0, symbol.start_line - 1),
      title: `${ICON[first.freshness] ?? '?'} Smriti ${first.freshness}: ${truncate(first.text, 80)}${more}`,
      factIds: anchored.map((f) => f.id),
    });
  }
  return lenses.sort((a, b) => a.line - b.line);
}

/** The innermost indexed symbol in `path` that starts at or above `line` (1-based). */
export function symbolAt(path: string, line: number, symbols: SymbolInfo[]): SymbolInfo | undefined {
  const wanted = toIndexPath(path);
  return symbols
    .filter((s) => s.path === wanted && s.kind !== 'module' && s.start_line <= line)
    .sort((a, b) => b.start_line - a.start_line)[0];
}

export function anchorArgument(symbol: SymbolInfo): string {
  return `${symbol.id}=${symbol.content_hash}`;
}

function truncate(text: string, limit: number): string {
  const single = text.replace(/\s+/g, ' ').trim();
  return single.length <= limit ? single : `${single.slice(0, limit - 1)}…`;
}
