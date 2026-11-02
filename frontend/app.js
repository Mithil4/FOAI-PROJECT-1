/**
 * Frontend Client JavaScript for SmartPack AI
 * Handles API communication with FastAPI backend:
 * - Real-time facility polling
 * - Dynamic locker matrix rendering
 * - Package intake, retrieval, and CSP solver triggers
 * - Benchmark visualization
 */

const API_BASE = window.location.origin;

// DOM Elements
const backendStatus = document.getElementById('backend-status');
const statTotal = document.getElementById('stat-total');
const statAvail = document.getElementById('stat-avail');
const statOccupied = document.getElementById('stat-occupied');
const statCold = document.getElementById('stat-cold');
const statQueue = document.getElementById('stat-queue');
const lockerMatrix = document.getElementById('locker-matrix');
const queueTableBody = document.getElementById('queue-table-body');
const queueBadge = document.getElementById('queue-badge');
const storedTableBody = document.getElementById('stored-table-body');
const benchmarkTableBody = document.getElementById('benchmark-table-body');

// Metric Box
const metricsBox = document.getElementById('solver-metrics-box');
const metricAlgo = document.getElementById('metric-algo');
const metricNodes = document.getElementById('metric-nodes');
const metricBacktracks = document.getElementById('metric-backtracks');
const metricLatency = document.getElementById('metric-latency');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initForms();
    fetchFacilityState();
    fetchBenchmarkData();
});

// Tab Switching
function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            const target = document.getElementById(btn.dataset.tab);
            if (target) target.classList.add('active');
        });
    });
}

// Fetch Full Facility State from Backend
async function fetchFacilityState() {
    try {
        const res = await fetch(`${API_BASE}/api/facility`);
        if (!res.ok) throw new Error('Backend offline');
        const data = await res.json();

        // Update Backend Status
        backendStatus.textContent = 'Backend Online (FastAPI)';
        backendStatus.className = 'status-pill status-online';

        // Update Stats
        statTotal.textContent = data.stats['Total Lockers'];
        statAvail.textContent = data.stats['Available Lockers'];
        statOccupied.textContent = `${data.stats['Occupied Lockers']} (${data.stats['Utilization Rate (%)']}%)`;
        statCold.textContent = data.stats['Cold Storage Occupied'];
        statQueue.textContent = data.stats['Pending in Queue'];
        queueBadge.textContent = `${data.pending_queue.length} items`;

        // Render Locker Grid
        renderLockerMatrix(data.lockers, data.active_packages);

        // Render Queue Table
        renderQueueTable(data.pending_queue);

        // Render Stored Packages
        renderStoredPackages(data.active_packages);

        // Render Last Solver Metrics
        if (data.last_solver_metrics) {
            updateMetricsBox(data.last_solver_metrics);
        }

    } catch (err) {
        backendStatus.textContent = 'Backend Offline';
        backendStatus.className = 'status-pill status-offline';
        console.error('Fetch error:', err);
    }
}

// Render Locker Cards
function renderLockerMatrix(lockers, activePackages) {
    lockerMatrix.innerHTML = '';
    const activeMap = {};
    activePackages.forEach(p => activeMap[p.ID] = p);

    lockers.forEach(l => {
        const isOcc = l.Status === 'Occupied';
        const card = document.createElement('div');
        card.className = `locker-item ${isOcc ? 'locker-occupied' : 'locker-available'}`;

        const pkg = isOcc ? activeMap[l['Package ID']] : null;
        const refrigIcon = l.Refrigerated === 'Yes' ? '❄️ Cold' : '🌡️ Ambient';
        const tierIcon = l.Tier === 'Tier 1' ? '👁️ Eye-Lvl' : '📐 Low/High';

        card.innerHTML = `
            <div>
                <div class="locker-id-row">
                    <span>${l['Locker ID']}</span>
                    <span class="locker-badge ${isOcc ? 'badge-occ' : 'badge-avail'}">${l.Status}</span>
                </div>
                <div class="locker-specs">
                    <b>Size:</b> ${l.Size} (Max ${l['Max Weight (kg)']}kg)<br>
                    <b>Type:</b> ${refrigIcon} | ${tierIcon}
                </div>
            </div>
            ${isOcc ? `
                <div class="locker-pkg-badge">
                    📦 ${l['Package ID']}<br>
                    <span style="font-size:0.65rem; color:#4B5563;">To: ${pkg ? pkg.Recipient : 'User'}</span>
                </div>
            ` : '<div style="font-size:0.7rem; color:#059669; font-weight:600;">✓ Ready</div>'}
        `;
        lockerMatrix.appendChild(card);
    });
}

// Render Pending Queue
function renderQueueTable(queue) {
    queueTableBody.innerHTML = '';
    if (queue.length === 0) {
        queueTableBody.innerHTML = '<tr><td colspan="7" class="text-center" style="color:#64748B;">No pending packages in queue.</td></tr>';
        return;
    }

    queue.forEach(p => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><b>${p.ID}</b></td>
            <td>${p['Tracking #']}</td>
            <td>${p.Recipient}</td>
            <td><span class="badge">${p.Size}</span></td>
            <td>${p['Weight (kg)']} kg</td>
            <td>${p.Perishable === 'Yes' ? '❄️ Yes' : 'No'}</td>
            <td><span class="badge" style="background:${p.Priority === 'Urgent' ? '#FEE2E2' : '#F1F5F9'}; color:${p.Priority === 'Urgent' ? '#B91C1C' : '#334155'};">${p.Priority}</span></td>
        `;
        queueTableBody.appendChild(tr);
    });
}

// Render Stored Parcels
function renderStoredPackages(packages) {
    storedTableBody.innerHTML = '';
    if (packages.length === 0) {
        storedTableBody.innerHTML = '<tr><td colspan="5" class="text-center">No stored packages currently.</td></tr>';
        return;
    }

    packages.forEach(p => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><span class="badge" style="background:#DBEAFE; color:#1E40AF; font-weight:bold;">${p['Assigned Locker']}</span></td>
            <td><b>${p.ID}</b></td>
            <td>${p['Tracking #']}</td>
            <td>${p.Recipient}</td>
            <td><button class="btn-danger-sm" onclick="quickRetrieve('${p.ID}')">Dispense</button></td>
        `;
        storedTableBody.appendChild(tr);
    });
}

// Form Handlers
function initForms() {
    // Refresh button
    document.getElementById('btn-refresh').addEventListener('click', fetchFacilityState);

    // Intake Form
    const intakeForm = document.getElementById('form-intake');
    intakeForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            tracking_number: document.getElementById('intake-tracking').value,
            recipient_name: document.getElementById('intake-recipient').value,
            size: document.getElementById('intake-size').value,
            weight_kg: parseFloat(document.getElementById('intake-weight').value),
            is_perishable: document.getElementById('intake-cold').checked,
            priority: document.getElementById('intake-priority').value
        };

        try {
            const res = await fetch(`${API_BASE}/api/packages/intake`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                intakeForm.reset();
                document.getElementById('intake-tracking').value = `TRK-${Math.floor(1000 + Math.random()*9000)}`;
                fetchFacilityState();
            }
        } catch (err) {
            alert('Failed to enqueue package: ' + err.message);
        }
    });

    // Reset Facility
    const btnResetFacility = document.getElementById('btn-reset-facility');
    if (btnResetFacility) {
        btnResetFacility.addEventListener('click', async () => {
            if (confirm('Are you sure you want to completely reset all lockers and queue?')) {
                await fetch(`${API_BASE}/api/facility/reset`, { method: 'POST' });
                const alertBox = document.getElementById('solver-alert');
                if (alertBox) alertBox.classList.add('hidden');
                fetchFacilityState();
            }
        });
    }

    // Clear Queue
    const btnClearQueue = document.getElementById('btn-clear-queue');
    if (btnClearQueue) {
        btnClearQueue.addEventListener('click', async () => {
            await fetch(`${API_BASE}/api/queue/clear`, { method: 'POST' });
            const alertBox = document.getElementById('solver-alert');
            if (alertBox) alertBox.classList.add('hidden');
            fetchFacilityState();
        });
    }

    // Load Sample Queue
    document.getElementById('btn-sample-queue').addEventListener('click', async () => {
        await fetch(`${API_BASE}/api/packages/load-sample`, { method: 'POST' });
        const alertBox = document.getElementById('solver-alert');
        if (alertBox) alertBox.classList.add('hidden');
        fetchFacilityState();
    });

    // Execute CSP Solver Allocation
    document.getElementById('btn-allocate').addEventListener('click', async () => {
        const algo = document.getElementById('algo-select').value;
        const btn = document.getElementById('btn-allocate');
        const alertBox = document.getElementById('solver-alert');
        btn.textContent = '⏳ Solving CSP...';
        btn.disabled = true;

        try {
            const res = await fetch(`${API_BASE}/api/allocate`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ algorithm: algo })
            });
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.detail || 'Allocation failed');
            }
            if (data.metrics) {
                updateMetricsBox(data.metrics);
            }

            if (alertBox) {
                alertBox.classList.remove('hidden');
                const assignedCount = data.metrics ? data.metrics['Assigned Packages'] : 0;
                if (data.success && assignedCount > 0) {
                    alertBox.className = 'alert alert-success';
                    alertBox.innerHTML = `<b>✓ Success:</b> Allocated <b>${assignedCount}</b> packages using <i>${data.algorithm_used}</i> in ${data.metrics['Execution Time (ms)']} ms! ${data.unassigned_count > 0 ? `<br><small>(${data.unassigned_count} packages remain in queue awaiting compatible compartments)</small>` : ''}`;
                } else {
                    alertBox.className = 'alert alert-error';
                    alertBox.innerHTML = `<b>Notice:</b> ${data.message || 'No packages could be allocated due to constraint mismatch (e.g. cold storage at full capacity).'}`;
                }
            }

            fetchFacilityState();
        } catch (err) {
            if (alertBox) {
                alertBox.classList.remove('hidden');
                alertBox.className = 'alert alert-error';
                alertBox.textContent = 'Allocation notice: ' + err.message;
            }
        } finally {
            btn.textContent = '⚡ Execute Allocation';
            btn.disabled = false;
        }
    });

    // Retrieval Form
    const retrieveForm = document.getElementById('form-retrieve');
    retrieveForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = document.getElementById('retrieve-query').value;
        quickRetrieve(query);
    });
}

// Quick Retrieve Action
async function quickRetrieve(query) {
    const alertBox = document.getElementById('retrieve-result');
    try {
        const res = await fetch(`${API_BASE}/api/retrieve`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ package_id_or_tracking: query })
        });
        const data = await res.json();
        if (res.ok) {
            alertBox.className = 'alert alert-success';
            alertBox.textContent = `✓ Success: ${data.message} Locker ${data.freed_locker['Locker ID']} is now available.`;
            alertBox.classList.remove('hidden');
            fetchFacilityState();
        } else {
            alertBox.className = 'alert alert-error';
            alertBox.textContent = data.detail || 'Package not found.';
            alertBox.classList.remove('hidden');
        }
    } catch (err) {
        alertBox.className = 'alert alert-error';
        alertBox.textContent = 'Network error: ' + err.message;
        alertBox.classList.remove('hidden');
    }
}

// Update Solver Diagnostic Box
function updateMetricsBox(metrics) {
    metricsBox.classList.remove('hidden');
    metricAlgo.textContent = metrics.Algorithm || metrics.algorithm_name;
    metricNodes.textContent = metrics['Nodes Explored'] ?? metrics.nodes_visited;
    metricBacktracks.textContent = metrics.Backtracks ?? metrics.backtracks;
    metricLatency.textContent = `${metrics['Execution Time (ms)'] ?? metrics.execution_time_ms} ms`;
}

// Fetch Benchmark Data
async function fetchBenchmarkData() {
    try {
        const res = await fetch(`${API_BASE}/api/benchmark-data`);
        if (!res.ok) return;
        const data = await res.json();
        benchmarkTableBody.innerHTML = '';
        data.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><b>${row.N}</b></td>
                <td>${row.Pure_Nodes}</td>
                <td>${row.Pure_Time_ms.toFixed(2)} ms</td>
                <td>${row.FC_Nodes}</td>
                <td>${row.FC_Time_ms.toFixed(2)} ms</td>
                <td style="color:#059669; font-weight:bold;">${row.Opt_Nodes}</td>
                <td style="color:#059669; font-weight:bold;">${row.Opt_Time_ms.toFixed(2)} ms</td>
            `;
            benchmarkTableBody.appendChild(tr);
        });
    } catch (err) {
        console.log('No benchmark data yet.');
    }
}

