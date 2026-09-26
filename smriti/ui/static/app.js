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

document.querySelectorAll('[data-view]').forEach((button) => button.addEventListener('click', () => {
  document.querySelectorAll('[data-view]').forEach((item) => item.classList.toggle('active', item === button));
  document.querySelectorAll('.view').forEach((view) => { view.hidden = view.id !== `view-${button.dataset.view}`; });
}));
byId('refresh-status').addEventListener('click', refreshStatus);
byId('symbol-search').addEventListener('submit', searchSymbols);
byId('context-form').addEventListener('submit', buildContext);
refreshStatus();
