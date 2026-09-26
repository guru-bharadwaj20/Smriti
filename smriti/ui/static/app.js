'use strict';

const byId = (id) => document.getElementById(id);
const notify = (message) => {
  byId('notice').textContent = message;
  byId('notice').hidden = !message;
};

async function request(path, options = {}) {
  const response = await fetch(path, {...options, headers: {'Content-Type': 'application/json', ...options.headers}});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  return data;
}

async function refreshStatus() {
  try {
    const status = await request('/api/status');
    byId('repository-name').textContent = status.repository;
    byId('repository-root').textContent = status.root;
    byId('index-state').textContent = status.indexed ? 'Index ready · published snapshot' : 'Repository not indexed yet';
    byId('index-dot').style.background = status.indexed ? 'var(--accent)' : 'var(--warn)';
    for (const metric of ['files', 'symbols', 'edges', 'version']) byId(`metric-${metric}`).textContent = status[metric].toLocaleString();
    notify('');
  } catch (error) { notify(error.message); }
}

function element(tag, text = '', className = '') {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  return node;
}

async function showGraph(id) {
  try {
    const graph = await request(`/api/graph/${encodeURIComponent(id)}`);
    const detail = byId('symbol-detail');
    const names = new Map([graph.symbol, ...graph.neighbors].map((symbol) => [symbol.id, symbol.qualname]));
    detail.replaceChildren(element('h2', graph.symbol.qualname), element('p', `${graph.symbol.path}:${graph.symbol.start_line} · ${graph.symbol.kind}`, 'muted'));
    if (graph.symbol.docstring) detail.append(element('p', graph.symbol.docstring));
    detail.append(element('pre', graph.symbol.body || graph.symbol.signature || 'External reference', 'source-code'));
    detail.append(element('h3', 'Connected symbols'));
    for (const edge of graph.edges) {
      const target = edge.source === id ? edge.target : edge.source;
      const row = element('div', '', 'relation');
      row.append(element('span', `${edge.kind} · ${edge.confidence.toFixed(2)}`, 'relation-kind'));
      const button = element('button', names.get(target) || target, 'text-button');
      button.addEventListener('click', () => showGraph(target));
      row.append(button);
      detail.append(row);
    }
    if (!graph.edges.length) detail.append(element('p', 'No graph edges in this snapshot.', 'empty'));
    notify('');
  } catch (error) { notify(error.message); }
}

async function searchSymbols(event) {
  event?.preventDefault();
  try {
    const symbols = await request(`/api/symbols?q=${encodeURIComponent(byId('symbol-query').value)}`);
    const table = byId('symbol-results');
    table.replaceChildren();
    byId('symbol-count').textContent = `${symbols.length} FOUND`;
    byId('symbol-empty').hidden = symbols.length > 0;
    byId('symbol-empty').textContent = 'No matching definitions. Check that the repository is indexed.';
    for (const symbol of symbols) {
      const row = element('tr');
      const name = element('td');
      const button = element('button', symbol.qualname, 'text-button');
      button.addEventListener('click', () => showGraph(symbol.id));
      name.append(button);
      row.append(name, element('td', symbol.kind), element('td', `${symbol.path}:${symbol.start_line}`, 'location'));
      table.append(row);
    }
    notify('');
  } catch (error) { notify(error.message); }
}

async function buildContext(event) {
  event.preventDefault();
  const button = byId('context-submit');
  button.disabled = true;
  button.textContent = 'Retrieving…';
  try {
    const data = await request('/api/context', {method: 'POST', body: JSON.stringify({task: byId('context-task').value, budget: Number(byId('context-budget').value)})});
    byId('context-count').textContent = `${data.token_count.toLocaleString()} / ${data.budget.toLocaleString()} TOKENS`;
    byId('context-metadata').textContent = `${data.items.length} selected definitions · index ${data.index_version} · ${data.tokenizer}`;
    byId('context-output').textContent = data.text || 'No code fits this budget.';
    byId('context-output').hidden = false;
    byId('context-table').hidden = data.items.length === 0;
    const items = byId('context-items');
    items.replaceChildren();
    for (const item of data.items) {
      const row = element('tr');
      const name = element('td');
      const button = element('button', item.path, 'text-button');
      button.addEventListener('click', () => { document.querySelector('[data-view="symbols"]').click(); showGraph(item.symbol_id); });
      name.append(button);
      row.append(name, element('td', {1: 'Name', 2: 'Signature', 3: 'Full body'}[item.level] || String(item.level)), element('td', item.reason));
      items.append(row);
    }
    notify('');
  } catch (error) { notify(error.message); }
  finally { button.disabled = false; button.textContent = 'Build context →'; }
}

async function recallMemory(event) {
  event?.preventDefault();
  try {
    const data = await request(`/api/memory?q=${encodeURIComponent(byId('memory-query').value)}`);
    byId('memory-branch').textContent = data.branch;
    byId('memory-count').textContent = `${data.facts.length} remembered facts`;
    const results = byId('memory-results');
    results.replaceChildren();
    for (const fact of data.facts) {
      const card = element('article', '', 'memory-card');
      const heading = element('div', '', 'panel-heading');
      heading.append(element('span', fact.freshness.toUpperCase(), `pill freshness-${fact.freshness}`), element('span', `${fact.confidence.toFixed(2)} confidence`, 'location'));
      card.append(heading, element('p', fact.text, 'fact-text'));
      if (fact.freshness !== 'fresh') card.append(element('p', fact.freshness_reason || 'The source needs revalidation.', 'freshness-warning'));
      const anchors = element('div', '', 'anchor-list');
      for (const anchor of fact.anchors) {
        const button = element('button', `↗ ${anchor.symbol_id.slice(0, 12)} · ${anchor.content_hash.slice(0, 8)}`, 'text-button');
        button.addEventListener('click', () => { document.querySelector('[data-view="symbols"]').click(); showGraph(anchor.symbol_id); });
        anchors.append(button);
      }
      if (!fact.anchors.length) anchors.append(element('span', 'Project fact · no code anchor', 'muted'));
      card.append(anchors);
      const details = element('details');
      details.append(element('summary', 'Provenance'));
      for (const field of ['id', 'source', 'session', 'user', 'tool', 'subject', 'valid_from', 'valid_to', 'recorded_at', 'triggering_commit']) {
        if (fact[field]) details.append(element('p', `${field.replaceAll('_', ' ')}: ${fact[field]}`, 'provenance'));
      }
      card.append(details);
      results.append(card);
    }
    if (!data.facts.length) results.append(element('p', 'No matching facts on this branch.', 'empty'));
    notify('');
  } catch (error) { notify(error.message); }
}

async function loadHistory() {
  try {
    const data = await request('/api/history');
    byId('history-head').textContent = data.head ? data.head.slice(0, 12) : 'EMPTY HISTORY';
    const results = byId('history-results');
    results.replaceChildren();
    for (const operation of data.operations) {
      const row = element('article', '', 'history-row');
      const heading = element('div', '', 'panel-heading');
      heading.append(element('span', operation.kind.toUpperCase(), 'pill'), element('span', operation.recorded_at || '', 'location'));
      row.append(heading, element('p', operation.id, 'provenance'));
      const button = element('button', 'Compare from this operation →', 'text-button');
      button.addEventListener('click', () => { byId('diff-left').value = operation.id; byId('diff-right').value = ''; byId('diff-form').requestSubmit(); });
      row.append(button);
      const details = element('details');
      details.append(element('summary', 'Operation details'), element('pre', JSON.stringify(operation, null, 2), 'source-code'));
      row.append(details);
      results.append(row);
    }
    if (!data.operations.length) results.append(element('p', 'No memory operations on this branch.', 'empty'));
    notify('');
  } catch (error) { notify(error.message); }
}

async function compareMemory(event) {
  event.preventDefault();
  try {
    const params = new URLSearchParams({left: byId('diff-left').value.trim(), right: byId('diff-right').value.trim()});
    const diff = await request(`/api/diff?${params}`);
    const results = byId('diff-results');
    results.replaceChildren();
    let count = 0;
    for (const kind of ['added', 'removed', 'changed']) {
      for (const [id, value] of Object.entries(diff[kind] || {})) {
        count++;
        const row = element('article', '', 'diff-row');
        row.append(element('span', kind.toUpperCase(), `pill diff-${kind}`), element('p', id, 'provenance'));
        if (kind === 'changed') {
          row.append(element('p', `Before: ${value.before.text}`, 'diff-before'), element('p', `After: ${value.after.text}`, 'fact-text'));
        } else { row.append(element('p', value.text, 'fact-text')); }
        results.append(row);
      }
    }
    if (!count) results.append(element('p', 'These memory states have no differences.', 'empty'));
    notify('');
  } catch (error) { notify(error.message); }
}

let mergeState = null;

async function loadBranches() {
  try {
    const data = await request('/api/branches');
    const source = byId('merge-source');
    source.replaceChildren();
    const placeholder = element('option', `Merge into ${data.current} from…`);
    placeholder.value = '';
    source.append(placeholder);
    for (const name of Object.keys(data.heads).filter((name) => name !== data.current).sort()) {
      const option = element('option', name);
      option.value = name;
      source.append(option);
    }
    mergeState = null;
    byId('apply-merge').disabled = true;
    notify('');
  } catch (error) { notify(error.message); }
}

function updateMergeButton() {
  const choices = [...document.querySelectorAll('[data-conflict-id]')];
  byId('apply-merge').disabled = !mergeState || choices.some((choice) => !choice.value);
}

async function previewMerge(event) {
  event.preventDefault();
  try {
    mergeState = await request(`/api/merge-preview?source=${encodeURIComponent(byId('merge-source').value)}`);
    const conflicts = Object.entries(mergeState.conflicts);
    byId('merge-state').textContent = `${mergeState.current} ← ${mergeState.source} · ${conflicts.length} conflicts`;
    const results = byId('merge-conflicts');
    results.replaceChildren();
    for (const [id, conflict] of conflicts) {
      const card = element('article', '', 'panel conflict-card');
      card.append(element('h2', conflict.kind === 'delete_update' ? 'Deletion conflicts with an update' : 'Both branches changed this fact'), element('p', id, 'provenance'));
      const versions = element('div', '', 'conflict-grid');
      for (const [key, label] of [['base', 'Common ancestor'], ['ours', 'Current branch'], ['theirs', 'Source branch']]) {
        const variant = element('div', '', 'conflict-variant');
        variant.append(element('h3', label), element('p', conflict[key]?.text || 'Fact absent', 'fact-text'));
        versions.append(variant);
      }
      card.append(versions);
      const label = element('label', 'Retain this version', 'conflict-label');
      const choice = element('select', '', 'history-input');
      choice.dataset.conflictId = id;
      for (const [key, text] of [['', 'Choose a resolution…'], ['ours', 'Current branch'], ['theirs', 'Source branch'], ['base', 'Common ancestor'], ['delete', 'Delete the fact']]) {
        const option = element('option', text);
        option.value = key;
        choice.append(option);
      }
      choice.addEventListener('change', updateMergeButton);
      label.append(choice);
      card.append(label);
      results.append(card);
    }
    if (!conflicts.length) results.append(element('p', 'No conflicts. The branches can merge directly.', 'empty'));
    updateMergeButton();
    notify('');
  } catch (error) { mergeState = null; updateMergeButton(); notify(error.message); }
}

async function applyMerge() {
  if (!mergeState) return;
  const resolutions = Object.fromEntries([...document.querySelectorAll('[data-conflict-id]')].map((choice) => [choice.dataset.conflictId, choice.value]));
  byId('apply-merge').disabled = true;
  try {
    const result = await request('/api/merge', {method: 'POST', body: JSON.stringify({source: mergeState.source, resolutions})});
    byId('merge-state').textContent = `Merged into ${result.branch} · operation ${result.operation_id.slice(0, 12)}`;
    byId('merge-conflicts').replaceChildren(element('p', 'The selected resolutions are recorded in memory history.', 'empty'));
    mergeState = null;
    notify('');
  } catch (error) { updateMergeButton(); notify(error.message); }
}

document.querySelectorAll('[data-view]').forEach((button) => button.addEventListener('click', () => {
  document.querySelectorAll('[data-view]').forEach((item) => item.classList.toggle('active', item === button));
  document.querySelectorAll('.view').forEach((view) => { view.hidden = view.id !== `view-${button.dataset.view}`; });
}));
byId('refresh-status').addEventListener('click', refreshStatus);
byId('symbol-search').addEventListener('submit', searchSymbols);
byId('context-form').addEventListener('submit', buildContext);
byId('memory-search').addEventListener('submit', recallMemory);
byId('refresh-history').addEventListener('click', loadHistory);
byId('diff-form').addEventListener('submit', compareMemory);
byId('load-branches').addEventListener('click', loadBranches);
byId('merge-form').addEventListener('submit', previewMerge);
byId('apply-merge').addEventListener('click', applyMerge);
refreshStatus();
