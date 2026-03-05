/* app.js — Lumina Clippers LinkedIn Audit Tool frontend */

// API base URL — set via inline script in index.html
const API_BASE = (typeof window !== 'undefined' && window.LUMINA_API_URL)
  ? window.LUMINA_API_URL.replace(/\/$/, '')
  : '';

// ============================================================
// STATE
// ============================================================
const state = {
  jobs: {},          // jobId → { id, url, name, status, progress, result, error, ts }
};

// ============================================================
// UTILITIES
// ============================================================
function genId() {
  return Math.random().toString(36).slice(2, 9);
}

function formatUrl(url) {
  try {
    const u = new URL(url);
    return u.hostname + u.pathname.replace(/\/$/, '');
  } catch {
    return url;
  }
}

function nameFromUrl(url) {
  try {
    const parts = new URL(url).pathname.split('/').filter(Boolean);
    // linkedin.com/in/<slug>  → use slug
    const inIdx = parts.indexOf('in');
    if (inIdx !== -1 && parts[inIdx + 1]) {
      return parts[inIdx + 1].replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }
    return parts.pop() || url;
  } catch {
    return url;
  }
}

function sanitizeLinkedInUrl(raw) {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  // Allow full URLs or short "linkedin.com/in/..." 
  try {
    const u = new URL(trimmed.startsWith('http') ? trimmed : 'https://' + trimmed);
    if (!u.hostname.includes('linkedin.com')) return null;
    return u.href;
  } catch {
    return null;
  }
}

// ============================================================
// DOM REFS
// ============================================================
const urlInput    = document.getElementById('url-input');
const analyzeBtn  = document.getElementById('analyze-btn');
const inputError  = document.getElementById('input-error');
const emptyState  = document.getElementById('empty-state');

const progressSection  = document.getElementById('progress-section');
const completedSection = document.getElementById('completed-section');
const failedSection    = document.getElementById('failed-section');

const progressJobs  = document.getElementById('progress-jobs');
const completedJobs = document.getElementById('completed-jobs');
const failedJobs    = document.getElementById('failed-jobs');

// ============================================================
// RENDER
// ============================================================
function render() {
  const jobs = Object.values(state.jobs);
  const inProgress = jobs.filter(j => j.status === 'pending' || j.status === 'running');
  const completed  = jobs.filter(j => j.status === 'complete');
  const failed     = jobs.filter(j => j.status === 'failed');

  // Empty state
  emptyState.style.display = jobs.length === 0 ? '' : 'none';

  // Sections
  progressSection.style.display  = inProgress.length ? '' : 'none';
  completedSection.style.display = completed.length  ? '' : 'none';
  failedSection.style.display    = failed.length     ? '' : 'none';

  progressJobs.innerHTML  = inProgress.map(renderCard).join('');
  completedJobs.innerHTML = completed.map(renderCard).join('');
  failedJobs.innerHTML    = failed.map(renderCard).join('');
}

function renderCard(job) {
  const statusBadge = {
    pending:  '<span class="badge badge-pending">Pending</span>',
    running:  '<span class="badge badge-running">Running</span>',
    complete: '<span class="badge badge-complete">Complete</span>',
    failed:   '<span class="badge badge-failed">Failed</span>',
  }[job.status] || '';

  const progressBar = (job.status === 'pending' || job.status === 'running')
    ? `<div class="progress-bar-wrap">
         <div class="progress-bar" style="width:${job.progress ?? 0}%"></div>
       </div>
       <div class="progress-label">${job.statusLabel || 'Analysing…'}</div>`
    : '';

  const resultHtml = job.status === 'complete' && job.result
    ? renderAuditResult(job.result, job.id)
    : '';

  const errorHtml = job.status === 'failed'
    ? `<div style="color:var(--color-error);font-size:var(--text-xs);">${job.error || 'Unknown error'}</div>`
    : '';

  const copyBtn = job.status === 'complete'
    ? `<button class="btn btn-outline" style="font-size:var(--text-xs);padding:var(--space-1) var(--space-3)" onclick="copyResult('${job.id}')">
         Copy JSON
       </button>`
    : '';

  const dismissBtn = `<button class="btn-icon" title="Dismiss" onclick="dismissJob('${job.id}')">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  </button>`;

  return `
  <div class="job-card" id="job-${job.id}">
    <div class="job-card-header">
      <div class="job-card-meta">
        <div class="job-card-name">${job.name}</div>
        <div class="job-card-url">${formatUrl(job.url)}</div>
      </div>
      <div class="job-card-actions">
        ${statusBadge}
        ${copyBtn}
        ${dismissBtn}
      </div>
    </div>
    ${progressBar}
    ${resultHtml}
    ${errorHtml}
  </div>`;
}

function renderAuditResult(result, jobId) {
  // Score row
  const scores = [
    { label: 'Personal Brand',  value: result.personal_brand_score },
    { label: 'Company',         value: result.company_score },
    { label: 'Content',         value: result.content_score },
    { label: 'Overall',         value: result.overall_score },
  ].filter(s => s.value != null);

  const scoreHtml = scores.length
    ? `<div class="score-row">${scores.map(s =>
        `<div class="score-card">
           <div class="score-value">${s.value}<span style="font-size:var(--text-sm);font-weight:400">/10</span></div>
           <div class="score-label">${s.label}</div>
         </div>`
      ).join('')}</div>`
    : '';

  // Tabs: Summary | Strengths | Gaps | Recommendations | Raw
  const tabId = `tabs-${jobId}`;
  const panelId = `panel-${jobId}`;

  const sections = [
    { key: 'summary',         label: 'Summary',        field: 'summary' },
    { key: 'strengths',       label: 'Strengths',      field: 'strengths' },
    { key: 'gaps',            label: 'Gaps',           field: 'gaps' },
    { key: 'recommendations', label: 'Recommendations',field: 'recommendations' },
  ].filter(s => result[s.field]);

  const tabsHtml = `
  <div class="tabs" id="${tabId}" role="tablist">
    ${sections.map((s, i) =>
      `<button class="tab ${i === 0 ? 'active' : ''}" role="tab"
        onclick="switchTab('${tabId}','${panelId}','${s.key}')">
        ${s.label}
      </button>`
    ).join('')}
    <button class="tab" role="tab" onclick="switchTab('${tabId}','${panelId}','raw')">
      Raw
    </button>
  </div>`;

  const panelsHtml = `
  <div id="${panelId}">
    ${sections.map((s, i) => `
      <div data-tab="${s.key}" style="display:${i === 0 ? '' : 'none'}">
        ${renderInsight(s.label, result[s.field])}
      </div>`
    ).join('')}
    <div data-tab="raw" style="display:none">
      <pre class="raw-json">${JSON.stringify(result, null, 2)}</pre>
    </div>
  </div>`;

  return `<div class="audit-result">${scoreHtml}${tabsHtml}${panelsHtml}</div>`;
}

function renderInsight(heading, content) {
  if (Array.isArray(content)) {
    return `
      <div class="insight-section">
        <div class="insight-heading">${heading}</div>
        <ul class="insight-list">
          ${content.map(item => `<li class="insight-item">${item}</li>`).join('')}
        </ul>
      </div>`;
  }
  if (typeof content === 'string') {
    return `
      <div class="insight-section">
        <div class="insight-heading">${heading}</div>
        <p style="font-size:var(--text-sm);color:var(--color-text-muted);line-height:1.6">${content}</p>
      </div>`;
  }
  return '';
}

// ============================================================
// TAB SWITCHING
// ============================================================
function switchTab(tabsId, panelId, key) {
  const tabsEl  = document.getElementById(tabsId);
  const panelEl = document.getElementById(panelId);
  if (!tabsEl || !panelEl) return;

  tabsEl.querySelectorAll('.tab').forEach((btn, i) => {
    const tabKey = btn.getAttribute('onclick').match(/'([^']+)'\s*\)$/)?.[1];
    btn.classList.toggle('active', tabKey === key);
  });
  panelEl.querySelectorAll('[data-tab]').forEach(div => {
    div.style.display = div.dataset.tab === key ? '' : 'none';
  });
}

// ============================================================
// COPY / DISMISS
// ============================================================
function copyResult(jobId) {
  const job = state.jobs[jobId];
  if (!job?.result) return;
  navigator.clipboard.writeText(JSON.stringify(job.result, null, 2))
    .then(() => {
      const btn = document.querySelector(`#job-${jobId} .btn-outline`);
      if (btn) { btn.textContent = 'Copied!'; setTimeout(() => btn.textContent = 'Copy JSON', 1500); }
    })
    .catch(() => {});
}

function dismissJob(jobId) {
  delete state.jobs[jobId];
  render();
}

// ============================================================
// API CALLS
// ============================================================
async function submitAudit(profileUrl) {
  const res = await fetch(`${API_BASE}/audit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile_url: profileUrl }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.error || `HTTP ${res.status}`);
  }
  return res.json(); // { job_id }
}

async function pollStatus(jobId, stateJobId) {
  const INTERVAL = 2500;
  const MAX_POLLS = 120; // 5 min
  let polls = 0;

  const tick = async () => {
    if (!state.jobs[stateJobId]) return; // dismissed
    polls++;
    if (polls > MAX_POLLS) {
      state.jobs[stateJobId].status = 'failed';
      state.jobs[stateJobId].error  = 'Timed out waiting for result';
      render();
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/audit/${jobId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const job = state.jobs[stateJobId];
      if (!job) return;

      job.progress    = data.progress ?? job.progress;
      job.statusLabel = data.status_label ?? '';

      if (data.status === 'complete') {
        job.status  = 'complete';
        job.result  = data.result;
        render();
        return;
      }
      if (data.status === 'failed') {
        job.status = 'failed';
        job.error  = data.error || 'Audit failed';
        render();
        return;
      }

      job.status = data.status || 'running';
      render();
      setTimeout(tick, INTERVAL);
    } catch (err) {
      const job = state.jobs[stateJobId];
      if (job) { job.status = 'failed'; job.error = err.message; render(); }
    }
  };

  setTimeout(tick, INTERVAL);
}

// ============================================================
// EVENT HANDLERS
// ============================================================
analyzeBtn.addEventListener('click', async () => {
  const raw = urlInput.value;
  const url = sanitizeLinkedInUrl(raw);

  inputError.style.display = 'none';

  if (!url) {
    inputError.textContent = 'Please enter a valid LinkedIn profile URL (e.g. https://linkedin.com/in/username)';
    inputError.style.display = '';
    urlInput.focus();
    return;
  }

  urlInput.value = '';
  analyzeBtn.disabled = true;

  const localId = genId();
  state.jobs[localId] = {
    id: localId,
    url,
    name: nameFromUrl(url),
    status: 'pending',
    progress: 0,
    statusLabel: 'Submitting…',
    result: null,
    error: null,
  };
  render();

  try {
    const { job_id } = await submitAudit(url);
    state.jobs[localId].status      = 'running';
    state.jobs[localId].statusLabel = 'Running…';
    render();
    pollStatus(job_id, localId);
  } catch (err) {
    state.jobs[localId].status = 'failed';
    state.jobs[localId].error  = err.message;
    render();
  } finally {
    analyzeBtn.disabled = false;
  }
});

urlInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') analyzeBtn.click();
});
