/**
 * Config Backup - Frontend Application
 */

// State
let sites = [];
let currentSite = null;

// DOM Elements
const siteSelect = document.getElementById('site-select');
const ipInput = document.getElementById('ip-input');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const backupForm = document.getElementById('backup-form');
const statusMessage = document.getElementById('status-message');
const resultsSection = document.getElementById('results-section');
const backupResult = document.getElementById('backup-result');
const diffSection = document.getElementById('diff-section');
const diffStats = document.getElementById('diff-stats');
const diffViewer = document.getElementById('diff-viewer');
const showOnlyDiff = document.getElementById('show-only-diff');
const historyTbody = document.getElementById('history-tbody');
const historyFilterSite = document.getElementById('history-filter-site');
const loadingOverlay = document.getElementById('loading-overlay');
const loadingText = document.getElementById('loading-text');
const themeToggle = document.getElementById('theme-toggle');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadSites();
    loadHistory();
    setupEventListeners();
});

// Theme Management
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
        document.body.classList.add('light');
    }
}

function toggleTheme() {
    document.body.classList.toggle('light');
    const isLight = document.body.classList.contains('light');
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
}

// Event Listeners
function setupEventListeners() {
    // Theme toggle
    themeToggle.addEventListener('click', toggleTheme);

    // Site selection
    siteSelect.addEventListener('change', onSiteSelect);

    // Manual IP clears site selection
    ipInput.addEventListener('input', () => {
        if (ipInput.value) {
            siteSelect.value = '';
            currentSite = null;
        }
    });

    // Backup form submission
    backupForm.addEventListener('submit', onBackupSubmit);

    // Diff toggle
    showOnlyDiff.addEventListener('change', () => {
        diffViewer.classList.toggle('only-diff', showOnlyDiff.checked);
    });

    // History filter
    historyFilterSite.addEventListener('change', loadHistory);
    document.getElementById('btn-refresh-history').addEventListener('click', loadHistory);
}

// Load sites from CSV
async function loadSites() {
    try {
        const response = await fetch('/api/sites');
        const data = await response.json();

        if (data.success) {
            sites = data.sites;
            populateSiteDropdown(data.dropdown);
            populateHistoryFilter(data.sites);
        }
    } catch (error) {
        console.error('Error loading sites:', error);
        siteSelect.innerHTML = '<option value="">Errore caricamento siti</option>';
    }
}

function populateSiteDropdown(dropdown) {
    siteSelect.innerHTML = '<option value="">-- Seleziona sito --</option>';

    dropdown.forEach(site => {
        const option = document.createElement('option');
        option.value = site.value;
        option.textContent = site.label;
        option.dataset.ip = site.ip;
        siteSelect.appendChild(option);
    });
}

function populateHistoryFilter(sites) {
    historyFilterSite.innerHTML = '<option value="">Tutti i siti</option>';

    sites.forEach(site => {
        const option = document.createElement('option');
        option.value = site.sito;
        option.textContent = `${site.nome} (${site.sito})`;
        historyFilterSite.appendChild(option);
    });
}

// Site selection handler
function onSiteSelect() {
    const sito = siteSelect.value;

    if (!sito) {
        currentSite = null;
        ipInput.value = '';
        usernameInput.value = '';
        passwordInput.value = '';
        return;
    }

    // Find site in loaded data
    currentSite = sites.find(s => s.sito === sito);

    if (currentSite) {
        ipInput.value = currentSite.switch_core_ip;
        usernameInput.value = currentSite.utente_core || currentSite.utente;
        passwordInput.value = currentSite.password_core || currentSite.password;
    }
}

// Backup submission
async function onBackupSubmit(e) {
    e.preventDefault();

    const sito = siteSelect.value;
    const ip = ipInput.value.trim();
    const username = usernameInput.value.trim();
    const password = passwordInput.value;

    // Validation
    if (!ip && !sito) {
        showStatus('Seleziona un sito o inserisci un IP', 'error');
        return;
    }

    if (!username || !password) {
        showStatus('Username e password sono obbligatori', 'error');
        return;
    }

    // Show loading
    showLoading('Connessione in corso...');

    try {
        const payload = {
            sito: sito || null,
            ip: ip || null,
            username: username,
            password: password,
        };

        const response = await fetch('/api/backup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        const data = await response.json();

        hideLoading();

        if (data.success) {
            showStatus('Backup completato con successo!', 'success');
            displayBackupResult(data);

            if (data.diff && data.has_changes) {
                displayDiff(data.diff);
            } else if (data.is_duplicate) {
                showStatus('Configurazione invariata rispetto all\'ultimo backup', 'info');
                hideDiff();
            } else {
                hideDiff();
            }

            // Refresh history
            loadHistory();
        } else {
            showStatus(`Errore: ${data.error}`, 'error');
            hideResults();
        }
    } catch (error) {
        hideLoading();
        showStatus(`Errore di connessione: ${error.message}`, 'error');
        hideResults();
    }
}

// Display functions
function showStatus(message, type) {
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
    statusMessage.classList.remove('hidden');
}

function hideStatus() {
    statusMessage.classList.add('hidden');
}

function showLoading(text = 'Caricamento...') {
    loadingText.textContent = text;
    loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
    loadingOverlay.classList.add('hidden');
}

function displayBackupResult(data) {
    resultsSection.classList.remove('hidden');

    const methodBadge = data.connection_method === 'SSH'
        ? '<span class="badge badge-ssh">SSH</span>'
        : '<span class="badge badge-telnet">Telnet</span>';

    backupResult.innerHTML = `
        <div class="result-item">
            <div class="label">ID Backup</div>
            <div class="value">#${data.id}</div>
        </div>
        <div class="result-item">
            <div class="label">File</div>
            <div class="value">${data.filename}</div>
        </div>
        <div class="result-item">
            <div class="label">Dimensione</div>
            <div class="value">${formatBytes(data.size)}</div>
        </div>
        <div class="result-item">
            <div class="label">Metodo</div>
            <div class="value">${methodBadge}</div>
        </div>
        <div class="result-item">
            <div class="label">Hash</div>
            <div class="value" title="${data.hash}">${data.hash.substring(0, 16)}...</div>
        </div>
        <div class="result-item">
            <div class="label">Modifiche</div>
            <div class="value">${data.has_changes ? 'Si' : 'No'}</div>
        </div>
    `;
}

function hideResults() {
    resultsSection.classList.add('hidden');
    hideDiff();
}

function displayDiff(diff) {
    diffSection.classList.remove('hidden');

    // Stats
    diffStats.innerHTML = `
        <div class="stat-item added">
            <span class="stat-value">+${diff.added_count}</span>
            <span>aggiunte</span>
        </div>
        <div class="stat-item removed">
            <span class="stat-value">-${diff.removed_count}</span>
            <span>rimosse</span>
        </div>
        <div class="stat-item unchanged">
            <span class="stat-value">${diff.old_line_count}</span>
            <span>righe precedenti</span>
        </div>
    `;

    // Side-by-side diff
    let diffHtml = '';

    diff.side_by_side.forEach(row => {
        diffHtml += `
            <div class="diff-row ${row.status}">
                <div class="diff-line-num">${row.left_num || ''}</div>
                <div class="diff-content left">${escapeHtml(row.left)}</div>
                <div class="diff-line-num">${row.right_num || ''}</div>
                <div class="diff-content right">${escapeHtml(row.right)}</div>
            </div>
        `;
    });

    diffViewer.innerHTML = diffHtml;
    diffViewer.classList.toggle('only-diff', showOnlyDiff.checked);
}

function hideDiff() {
    diffSection.classList.add('hidden');
}

// History
async function loadHistory() {
    const sito = historyFilterSite.value;

    try {
        let url = '/api/backups?limit=50';
        if (sito) {
            url += `&sito=${encodeURIComponent(sito)}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        if (data.success) {
            displayHistory(data.backups);
        }
    } catch (error) {
        console.error('Error loading history:', error);
        historyTbody.innerHTML = '<tr><td colspan="6" class="loading">Errore caricamento</td></tr>';
    }
}

function displayHistory(backups) {
    if (!backups.length) {
        historyTbody.innerHTML = '<tr><td colspan="6" class="loading">Nessun backup trovato</td></tr>';
        return;
    }

    historyTbody.innerHTML = backups.map(backup => {
        const methodBadge = backup.connection_method === 'SSH'
            ? '<span class="badge badge-ssh">SSH</span>'
            : '<span class="badge badge-telnet">Telnet</span>';

        return `
            <tr>
                <td><strong>${backup.nome_sito || backup.sito}</strong></td>
                <td>${backup.ip}</td>
                <td>${formatDate(backup.timestamp)}</td>
                <td>${methodBadge}</td>
                <td>${formatBytes(backup.config_size)}</td>
                <td>
                    <button class="action-btn" onclick="downloadBackup(${backup.id})">
                        Download
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

// Actions
function downloadBackup(id) {
    window.location.href = `/api/backups/${id}/download`;
}

// Utility functions
function formatBytes(bytes) {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('it-IT', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
