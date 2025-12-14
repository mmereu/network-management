/**
 * Config Backup - Frontend Application
 */

// State
let sites = [];
let currentSite = null;

// History sorting state
let historyBackups = [];
let historySortColumn = 'timestamp';
let historySortOrder = 'desc';

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

    // Home button - navigate to main dashboard (port 80)
    const homeBtn = document.getElementById('home-btn');
    if (homeBtn) {
        homeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = `${window.location.protocol}//${window.location.hostname}/`;
        });
    }

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
            // Store backups for sorting
            historyBackups = data.backups;
            // Reset to default sort (newest first)
            historySortColumn = 'timestamp';
            historySortOrder = 'desc';
            sortAndRenderHistory();
            setupHistorySortableHeaders();
        }
    } catch (error) {
        console.error('Error loading history:', error);
        historyTbody.innerHTML = '<tr><td colspan="6" class="loading">Errore caricamento</td></tr>';
    }
}

// Sort and render history table
function sortAndRenderHistory() {
    if (!historyBackups.length) {
        historyTbody.innerHTML = '<tr><td colspan="6" class="loading">Nessun backup trovato</td></tr>';
        return;
    }

    // Sort backups
    const sorted = [...historyBackups].sort((a, b) => {
        let comparison = 0;

        switch (historySortColumn) {
            case 'sito':
                const sitoA = a.nome_sito || a.sito || '';
                const sitoB = b.nome_sito || b.sito || '';
                comparison = sitoA.localeCompare(sitoB);
                break;
            case 'ip':
                comparison = compareIPs(a.ip || '', b.ip || '');
                break;
            case 'timestamp':
                comparison = new Date(a.timestamp) - new Date(b.timestamp);
                break;
            case 'size':
                comparison = (a.config_size || 0) - (b.config_size || 0);
                break;
            default:
                comparison = 0;
        }

        return historySortOrder === 'asc' ? comparison : -comparison;
    });

    // Render table
    historyTbody.innerHTML = sorted.map(backup => {
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

    // Update sort icons
    updateHistorySortIcons();
}

// Setup history sortable headers click handlers
function setupHistorySortableHeaders() {
    document.querySelectorAll('.history-table th.sortable').forEach(th => {
        // Remove old listeners by cloning
        const newTh = th.cloneNode(true);
        th.parentNode.replaceChild(newTh, th);

        newTh.addEventListener('click', () => {
            const column = newTh.dataset.sort;

            if (historySortColumn === column) {
                // Toggle order
                historySortOrder = historySortOrder === 'asc' ? 'desc' : 'asc';
            } else {
                // New column, default to asc (except timestamp defaults to desc)
                historySortColumn = column;
                historySortOrder = column === 'timestamp' ? 'desc' : 'asc';
            }

            sortAndRenderHistory();
        });
    });
}

// Update history sort icons in headers
function updateHistorySortIcons() {
    document.querySelectorAll('.history-table th.sortable').forEach(th => {
        const icon = th.querySelector('.sort-icon');
        const column = th.dataset.sort;

        if (column === historySortColumn) {
            icon.textContent = historySortOrder === 'asc' ? '↑' : '↓';
            th.classList.add('sorted');
        } else {
            icon.textContent = '⇅';
            th.classList.remove('sorted');
        }
    });
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

// ============================================
// SUBNET BACKUP SECTION
// ============================================

// Subnet state for sorting
let subnetDevices = [];
let subnetSortColumn = 'ip';
let subnetSortOrder = 'asc';

// Subnet DOM Elements
const subnetForm = document.getElementById('subnet-form');
const subnetInput = document.getElementById('subnet-input');
const subnetSiteSelect = document.getElementById('subnet-site-select');
const subnetManualCreds = document.getElementById('subnet-manual-credentials');
const subnetUsername = document.getElementById('subnet-username');
const subnetPassword = document.getElementById('subnet-password');
const subnetUsernameCore = document.getElementById('subnet-username-core');
const subnetPasswordCore = document.getElementById('subnet-password-core');
const backupCoreOnly = document.getElementById('backup-core-only');
const backupL2Only = document.getElementById('backup-l2-only');
const subnetStatusMessage = document.getElementById('subnet-status-message');
const subnetProgress = document.getElementById('subnet-progress');
const stepDiscovery = document.getElementById('step-discovery');
const stepBackup = document.getElementById('step-backup');
const subnetProgressFill = document.getElementById('subnet-progress-fill');
const subnetProgressText = document.getElementById('subnet-progress-text');
const subnetResultsSection = document.getElementById('subnet-results-section');
const discoveryStats = document.getElementById('discovery-stats');
const devicesTbody = document.getElementById('devices-tbody');

// Initialize subnet dropdown
function populateSubnetSiteDropdown(dropdown) {
    subnetSiteSelect.innerHTML = '<option value="">-- Credenziali manuali --</option>';

    dropdown.forEach(site => {
        const option = document.createElement('option');
        option.value = site.value;
        option.textContent = site.label;
        subnetSiteSelect.appendChild(option);
    });
}

// Update loadSites to also populate subnet dropdown
const originalLoadSites = loadSites;
loadSites = async function() {
    try {
        const response = await fetch('/api/sites');
        const data = await response.json();

        if (data.success) {
            sites = data.sites;
            populateSiteDropdown(data.dropdown);
            populateSubnetSiteDropdown(data.dropdown);
            populateHistoryFilter(data.sites);
        }
    } catch (error) {
        console.error('Error loading sites:', error);
        siteSelect.innerHTML = '<option value="">Errore caricamento siti</option>';
    }
};

// Subnet site selection handler
subnetSiteSelect.addEventListener('change', () => {
    const sito = subnetSiteSelect.value;

    if (sito) {
        // Hide manual credentials and auto-fill from site
        subnetManualCreds.style.display = 'none';
        const site = sites.find(s => s.sito === sito);
        if (site && site.network) {
            subnetInput.value = site.network;
        }
    } else {
        // Show manual credentials
        subnetManualCreds.style.display = 'block';
    }
});

// Mutex for filter checkboxes (only one can be selected)
backupCoreOnly.addEventListener('change', () => {
    if (backupCoreOnly.checked) {
        backupL2Only.checked = false;
    }
});

backupL2Only.addEventListener('change', () => {
    if (backupL2Only.checked) {
        backupCoreOnly.checked = false;
    }
});

// Subnet form submission
subnetForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const subnet = subnetInput.value.trim();
    const sito = subnetSiteSelect.value;

    // Validation
    if (!subnet) {
        showSubnetStatus('Inserisci una subnet CIDR', 'error');
        return;
    }

    // Validate CIDR format
    const cidrRegex = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/;
    if (!cidrRegex.test(subnet)) {
        showSubnetStatus('Formato subnet non valido. Usa formato CIDR (es. 10.10.4.0/24)', 'error');
        return;
    }

    // Build payload
    const payload = {
        subnet: subnet,
        backup_core_only: backupCoreOnly.checked,
        backup_l2_only: backupL2Only.checked,
    };

    if (sito) {
        payload.sito = sito;
    } else {
        // Manual credentials
        const username = subnetUsername.value.trim();
        const password = subnetPassword.value;
        const usernameCore = subnetUsernameCore.value.trim();
        const passwordCore = subnetPasswordCore.value;

        if (!username || !password) {
            showSubnetStatus('Username e password L2 sono obbligatori', 'error');
            return;
        }

        payload.username = username;
        payload.password = password;
        payload.username_core = usernameCore || username;
        payload.password_core = passwordCore || password;
    }

    // Show progress
    showSubnetProgress();

    try {
        const response = await fetch('/api/backup/discover-and-backup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        const data = await response.json();

        hideSubnetProgress();

        if (data.success) {
            if (data.message) {
                // No devices found
                showSubnetStatus(data.message, 'info');
                hideSubnetResults();
            } else {
                showSubnetStatus('Backup subnet completato!', 'success');
                displaySubnetResults(data);
                loadHistory(); // Refresh history
            }
        } else {
            showSubnetStatus(`Errore: ${data.error}`, 'error');
            hideSubnetResults();
        }
    } catch (error) {
        hideSubnetProgress();
        showSubnetStatus(`Errore di connessione: ${error.message}`, 'error');
        hideSubnetResults();
    }
});

// Subnet status message
function showSubnetStatus(message, type) {
    subnetStatusMessage.textContent = message;
    subnetStatusMessage.className = `status-message ${type}`;
    subnetStatusMessage.classList.remove('hidden');
}

function hideSubnetStatus() {
    subnetStatusMessage.classList.add('hidden');
}

// Subnet progress
function showSubnetProgress() {
    subnetProgress.classList.remove('hidden');
    stepDiscovery.classList.add('active');
    stepBackup.classList.remove('active', 'complete');
    subnetProgressFill.style.width = '30%';
    subnetProgressText.textContent = 'Discovery...';

    // Simulate progress steps
    setTimeout(() => {
        stepDiscovery.classList.remove('active');
        stepDiscovery.classList.add('complete');
        stepBackup.classList.add('active');
        subnetProgressFill.style.width = '70%';
        subnetProgressText.textContent = 'Backup...';
    }, 3000);
}

function hideSubnetProgress() {
    subnetProgress.classList.add('hidden');
    stepDiscovery.classList.remove('active', 'complete');
    stepBackup.classList.remove('active', 'complete');
    subnetProgressFill.style.width = '0%';
}

// Display subnet results
function displaySubnetResults(data) {
    subnetResultsSection.classList.remove('hidden');

    const discovery = data.discovery || {};
    const backup = data.backup || {};

    // Stats
    discoveryStats.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${discovery.total_scanned || 0}</div>
            <div class="stat-label">IP Scansionati</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${discovery.devices_found || 0}</div>
            <div class="stat-label">Dispositivi Trovati</div>
        </div>
        <div class="stat-card success">
            <div class="stat-value">${backup.successful || 0}</div>
            <div class="stat-label">Backup Riusciti</div>
        </div>
        <div class="stat-card ${backup.failed_count > 0 ? 'error' : ''}">
            <div class="stat-value">${backup.failed_count || 0}</div>
            <div class="stat-label">Backup Falliti</div>
        </div>
    `;

    // Store devices for sorting
    subnetDevices = [
        ...(backup.results || []),
        ...(backup.failed || [])
    ];

    // Reset sort state and render
    subnetSortColumn = 'ip';
    subnetSortOrder = 'asc';
    sortAndRenderDevices();
    setupSortableHeaders();
}

// Sort and render devices table
function sortAndRenderDevices() {
    if (subnetDevices.length === 0) {
        devicesTbody.innerHTML = '<tr><td colspan="6" class="loading">Nessun dispositivo</td></tr>';
        return;
    }

    // Sort devices
    const sorted = [...subnetDevices].sort((a, b) => {
        let comparison = 0;

        switch (subnetSortColumn) {
            case 'ip':
                comparison = compareIPs(a.ip, b.ip);
                break;
            case 'hostname':
                comparison = (a.hostname || '').localeCompare(b.hostname || '');
                break;
            case 'status':
                comparison = (a.success === b.success) ? 0 : (a.success ? -1 : 1);
                break;
            default:
                comparison = 0;
        }

        return subnetSortOrder === 'asc' ? comparison : -comparison;
    });

    // Render table
    devicesTbody.innerHTML = sorted.map(device => {
        const typeBadge = device.type === 'core'
            ? '<span class="badge badge-core">Core</span>'
            : '<span class="badge badge-l2">L2</span>';

        const statusBadge = device.success
            ? '<span class="badge badge-success">OK</span>'
            : '<span class="badge badge-error">Fallito</span>';

        const backupId = device.backup_id ? `#${device.backup_id}` : '-';

        const note = device.error
            ? `<span class="error-text">${device.error}</span>`
            : (device.has_changes ? 'Config modificata' : (device.is_duplicate ? 'Invariata' : '-'));

        return `
            <tr class="${device.success ? '' : 'row-error'}">
                <td><strong>${device.ip}</strong></td>
                <td>${device.hostname || '-'}</td>
                <td>${typeBadge}</td>
                <td>${statusBadge}</td>
                <td>${backupId}</td>
                <td>${note}</td>
            </tr>
        `;
    }).join('');

    // Update sort icons
    updateSortIcons();
}

// Compare IP addresses numerically
function compareIPs(ip1, ip2) {
    const parts1 = ip1.split('.').map(Number);
    const parts2 = ip2.split('.').map(Number);

    for (let i = 0; i < 4; i++) {
        if (parts1[i] !== parts2[i]) {
            return parts1[i] - parts2[i];
        }
    }
    return 0;
}

// Setup sortable headers click handlers
function setupSortableHeaders() {
    document.querySelectorAll('.devices-table th.sortable').forEach(th => {
        // Remove old listeners by cloning
        const newTh = th.cloneNode(true);
        th.parentNode.replaceChild(newTh, th);

        newTh.addEventListener('click', () => {
            const column = newTh.dataset.sort;

            if (subnetSortColumn === column) {
                // Toggle order
                subnetSortOrder = subnetSortOrder === 'asc' ? 'desc' : 'asc';
            } else {
                // New column, default to asc
                subnetSortColumn = column;
                subnetSortOrder = 'asc';
            }

            sortAndRenderDevices();
        });
    });
}

// Update sort icons in headers
function updateSortIcons() {
    document.querySelectorAll('.devices-table th.sortable').forEach(th => {
        const icon = th.querySelector('.sort-icon');
        const column = th.dataset.sort;

        if (column === subnetSortColumn) {
            icon.textContent = subnetSortOrder === 'asc' ? '↑' : '↓';
            th.classList.add('sorted');
        } else {
            icon.textContent = '⇅';
            th.classList.remove('sorted');
        }
    });
}

function hideSubnetResults() {
    subnetResultsSection.classList.add('hidden');
}
