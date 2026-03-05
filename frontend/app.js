/* app.js — Lumina Clippers LinkedIn Audit Tool frontend */

// ── Config ──
const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://lumina-audit-api.onrender.com';

const POLL_INTERVAL_MS = 2500;
const MAX_POLL_ATTEMPTS = 120; // 5 minutes

// ── State ──
let currentJobId = null;
let pollTimer = null;
let pollAttempts = 0;

// ── DOM refs ──
const urlInput      = document.getElementById('linkedinUrl');
const analyzeBtn    = document.getElementById('analyzeBtn');
const inputError    = document.getElementById('inputError');
const progressSec   = document.getElementById('progressSection');
const progressBar   = document.getElementById('progressBar');
const progressLabel = document.getElementById('progressLabel');
const jobIdDisplay  = document.getElementById('jobIdDisplay');
const stepEls       = document.querySelectorAll('.step');
const resultSec     = document.getElementById('resultSection');
const resultName    = document.getElementById('resultName');
const downloadBtn   = document.getElementById('downloadBtn');
const scoreValue    = document.getElementById('scoreValue');
const errorSec      = document.getElementById('errorSection');
const errorMsg      = document.getElementById('errorMsg');
const retryBtn      = document.getElementById('retryBtn');
const jobsTable     = document.getElementById('jobsTable');

// ── Step metadata ──
const STEP_LABELS = {
  queued:      { step: 0,  label: 'Queued…',              pct: 2  },
  scraping:    { step: 1,  label: 'Scraping LinkedIn…',   pct: 20 },
  researching: { step: 4,  label: 'Researching online…',  pct: 55 },
  analyzing:   { step: 5,  label: 'Analyzing with AI…',   pct: 75 },
  generating:  { step: 6,  label: 'Generating PDF…',      pct: 90 },
  complete:    { step: 6,  label: 'Complete!',              pct: 100 },
  failed:      { step: -1, label: 'Failed',                pct: 0  },
};

// ── Utility ──
function hide(...els) { els.forEach(el => el.classList.add('hidden')); }
function show(...els) { els.forEach(el => el.classList.remove('hidden')); }

function setInputError(msg) {
  inputError.textContent = msg;
  show(inputError);
}

function clearInputError() {
  inputError.textContent = '';
  hide(inputError);
}

function validateUrl(url) {
  const trimmed = url.trim().replace(/\/$/, '').split('?')[0];
  const re = /^https?:\/\/(www\.)?linkedin\.com\/in\/[\w\-%.]+\/?$/i;
  return re.test(trimmed) ? trimmed : null;
}

// ── Analyze flow ──
analyzeBtn.addEventListener('click', startAnalysis);
urlInput.addEventListener('keydown', e => { if (e.key === 'Enter') startAnalysis(); });
retryBtn.addEventListener('click', resetUI);

async function startAnalysis() {
  clearInputError();
  const raw = urlInput.value;
  const url = validateUrl(raw);

  if (!url) {
    setInputError('Please enter a valid LinkedIn profile URL (e.g. https://www.linkedin.com/in/username)');
    return;
  }

  hide(resultSec, errorSec);
  show(progressSec);
  analyzeBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `Server error ${res.status}`);
    }

    const { job_id } = await res.json();
    currentJobId = job_id;
    jobIdDisplay.textContent = job_id.slice(0, 8) + '…';

    startPolling(job_id);
  } catch (err) {
    showError(err.message || 'Failed to start audit.');
  }
}

// ── Polling ──
function startPolling(jobId) {
  pollAttempts = 0;
  pollTimer = setInterval(() => pollStatus(jobId), POLL_INTERVAL_MS);
}

async function pollStatus(jobId) {
  pollAttempts++;
  if (pollAttempts > MAX_POLL_ATTEMPTS) {
    clearInterval(pollTimer);
    showError('Audit timed out. The LinkedIn profile may be unavailable or the pipeline stalled.');
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/status/${jobId}`);
    if (!res.ok) return;
    const job = await res.json();
    updateProgress(job);

    if (job.status === 'complete') {
      clearInterval(pollTimer);
      showResult(job);
      loadJobs();
    } else if (job.status === 'failed') {
      clearInterval(pollTimer);
      showError(job.error_msg || 'The audit pipeline encountered an error.');
      loadJobs();
    }
  } catch {
    // Network hiccup — keep polling
  }
}

// ── Progress UI ──
function updateProgress(job) {
  const meta = STEP_LABELS[job.status] || { step: job.step || 0, label: job.status, pct: 10 };
  const pct = meta.pct || Math.min(((job.step || 0) / 6) * 100, 95);

  progressBar.style.width = `${pct}%`;
  progressLabel.textContent = meta.label;

  stepEls.forEach(el => {
    const s = parseInt(el.dataset.step, 10);
    el.classList.toggle('done', s < meta.step);
    el.classList.toggle('active', s === meta.step);
  });
}

// ── Result UI ──
function showResult(job) {
  hide(progressSec, errorSec);
  show(resultSec);

  resultName.textContent = job.prospect_name || 'Audit Complete';
  scoreValue.textContent = job.brand_score != null ? job.brand_score : '--';

  downloadBtn.onclick = () => {
    window.open(`${API_BASE}/download/${job.id}`, '_blank');
  };

  analyzeBtn.disabled = false;
}

function showError(msg) {
  hide(progressSec, resultSec);
  show(errorSec);
  errorMsg.textContent = msg;
  analyzeBtn.disabled = false;
}

function resetUI() {
  hide(progressSec, resultSec, errorSec, inputError);
  urlInput.value = '';
  currentJobId = null;
  if (pollTimer) clearInterval(pollTimer);
}

// ── Jobs dashboard ──
async function loadJobs() {
  try {
    const res = await fetch(`${API_BASE}/jobs`);
    if (!res.ok) return;
    const jobs = await res.json();
    renderJobs(jobs);
  } catch {
    // Silently fail
  }
}

function renderJobs(jobs) {
  if (!jobs.length) {
    jobsTable.innerHTML = '<div class="jobs-empty">No audits yet.</div>';
    return;
  }

  jobsTable.innerHTML = jobs.map(job => {
    const name = job.prospect_name || job.url.replace('https://www.linkedin.com/in/', '');
    const statusClass = `status-${job.status}`;
    const scoreText = job.brand_score != null ? `Score: ${job.brand_score}` : '';
    const downloadHtml = job.status === 'complete'
      ? `<button class="btn btn-secondary job-download-btn" onclick="window.open('${API_BASE}/download/${job.id}', '_blank')">Download</button>`
      : '';

    return `
      <div class="job-row">
        <div>
          <div class="job-name">${escHtml(name)}</div>
          <div class="job-url">${escHtml(job.url)}</div>
        </div>
        <div class="job-score">${escHtml(scoreText)}</div>
        <span class="job-status ${statusClass}">${escHtml(job.status)}</span>
        ${downloadHtml}
      </div>
    `;
  }).join('');
}

function escHtml(str) {
  if (!str) return '';
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Initial load
loadJobs();
// Refresh dashboard every 10s
setInterval(loadJobs, 10_000);
