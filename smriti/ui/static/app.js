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

document.querySelectorAll('[data-view]').forEach((button) => button.addEventListener('click', () => {
  document.querySelectorAll('[data-view]').forEach((item) => item.classList.toggle('active', item === button));
  document.querySelectorAll('.view').forEach((view) => { view.hidden = view.id !== `view-${button.dataset.view}`; });
}));
byId('refresh-status').addEventListener('click', refreshStatus);
refreshStatus();
