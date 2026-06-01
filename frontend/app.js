/**
 * AI Dataset Validator — Frontend Application
 *
 * Handles all UI interactions, API calls, result rendering,
 * Chart.js analytics visualizations, and error injection workflows.
 */

// ─── Configuration ──────────────────────────────────────────────────────────

const API_BASE = window.location.origin.includes('file://')
    ? 'http://localhost:8000'
    : window.location.origin;

// ─── Tab Navigation ─────────────────────────────────────────────────────────

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        // Deactivate all
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

        // Activate selected
        btn.classList.add('active');
        const panelId = `panel-${btn.dataset.tab}`;
        document.getElementById(panelId).classList.add('active');

        // Refresh analytics when switching to that tab
        if (btn.dataset.tab === 'analytics') {
            refreshAnalytics();
        }
    });
});

// ─── API Helpers ────────────────────────────────────────────────────────────

async function apiCall(endpoint, method = 'GET', body = null) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);

    const res = await fetch(`${API_BASE}${endpoint}`, opts);
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

// ─── Toast Notifications ────────────────────────────────────────────────────

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ─── Pipeline ───────────────────────────────────────────────────────────────

function setNlInput(text) {
    document.getElementById('nl-input').value = text;
    document.getElementById('nl-input').focus();
}

async function runPipeline() {
    const text = document.getElementById('nl-input').value.trim();
    if (!text) {
        showToast('Please enter a natural language query.', 'error');
        return;
    }

    const btn = document.getElementById('btn-pipeline');
    btn.classList.add('loading');
    btn.disabled = true;

    try {
        const result = await apiCall('/api/pipeline', 'POST', { text });

        // Show results container
        document.getElementById('pipeline-results').style.display = 'block';

        // Generated call
        document.getElementById('pipeline-json').value =
            JSON.stringify(result.generated_call, null, 2);

        // Validation
        renderValidation(result.validation, 'pipeline-validation');

        // Query results
        if (result.data && result.data.rows) {
            document.getElementById('pipeline-data-card').style.display = 'block';
            renderDataTable(result.data, 'pipeline-data');
        } else {
            document.getElementById('pipeline-data-card').style.display = 'none';
        }

        // Dataset QA
        if (result.analysis) {
            document.getElementById('pipeline-qa-card').style.display = 'block';
            renderQAReport(result.analysis, 'pipeline-qa');
        } else {
            document.getElementById('pipeline-qa-card').style.display = 'none';
        }

        showToast('Pipeline completed successfully!', 'success');
    } catch (err) {
        showToast(`Pipeline error: ${err.message}`, 'error');
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}

// Enter key triggers pipeline
document.getElementById('nl-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') runPipeline();
});

// ─── Validator ──────────────────────────────────────────────────────────────

async function runValidation() {
    const raw = document.getElementById('validator-input').value.trim();
    if (!raw) {
        showToast('Please enter a function call JSON.', 'error');
        return;
    }

    try {
        const result = await apiCall('/api/validate', 'POST', { raw_json: raw });
        document.getElementById('validator-results').classList.add('visible');
        renderValidation(result, 'validator-validation');
        document.getElementById('validator-exec-results').style.display = 'none';
        showToast(`Validation: ${result.status.toUpperCase()}`, result.status === 'valid' ? 'success' : 'error');
    } catch (err) {
        showToast(`Validation error: ${err.message}`, 'error');
    }
}

async function runValidateAndExecute() {
    const raw = document.getElementById('validator-input').value.trim();
    if (!raw) {
        showToast('Please enter a function call JSON.', 'error');
        return;
    }

    try {
        const result = await apiCall('/api/analyze', 'POST', { raw_json: raw });

        // Show validation
        document.getElementById('validator-results').classList.add('visible');
        if (result.execution && result.execution.validation) {
            renderValidation(result.execution.validation, 'validator-validation');
        }

        // Show execution results
        if (result.execution && result.execution.executed && result.execution.data) {
            document.getElementById('validator-exec-results').style.display = 'block';
            renderDataTable(result.execution.data, 'validator-data');

            if (result.analysis) {
                renderQAReport(result.analysis, 'validator-qa');
            }
            showToast('Executed and analyzed!', 'success');
        } else {
            document.getElementById('validator-exec-results').style.display = 'none';
            const errMsg = result.execution?.error || 'Validation failed — cannot execute.';
            showToast(errMsg, 'error');
        }
    } catch (err) {
        showToast(`Error: ${err.message}`, 'error');
    }
}

function formatJson() {
    const textarea = document.getElementById('validator-input');
    try {
        const parsed = JSON.parse(textarea.value);
        textarea.value = JSON.stringify(parsed, null, 2);
        showToast('JSON formatted!', 'success');
    } catch {
        showToast('Cannot format: Invalid JSON.', 'error');
    }
}

function clearValidator() {
    document.getElementById('validator-input').value = '';
    document.getElementById('validator-results').classList.remove('visible');
    document.getElementById('validator-exec-results').style.display = 'none';
}

// ─── Rendering Helpers ──────────────────────────────────────────────────────

function renderValidation(result, containerId) {
    const container = document.getElementById(containerId);
    const statusEmoji = { valid: '✅', invalid: '❌', warning: '⚠️' };

    let html = `
        <div class="status-banner ${result.status}">
            <span style="font-size: 1.3rem;">${statusEmoji[result.status] || '❓'}</span>
            <span>Status: ${result.status.toUpperCase()}</span>
        </div>
        <div class="checks-grid">
    `;

    const checkLabels = {
        json_valid: 'JSON Valid',
        schema_match: 'Schema Match',
        types_valid: 'Types Valid',
        sql_safe: 'SQL Safe',
    };

    for (const [key, label] of Object.entries(checkLabels)) {
        const val = result.checks[key];
        let cls, icon;
        if (val === true) { cls = 'pass'; icon = '✓'; }
        else if (val === false) { cls = 'fail'; icon = '✗'; }
        else { cls = 'na'; icon = '—'; }

        html += `
            <div class="check-item">
                <div class="check-icon ${cls}">${icon}</div>
                <span>${label}</span>
            </div>
        `;
    }
    html += '</div>';

    if (result.errors && result.errors.length > 0) {
        html += '<ul class="error-list">';
        for (const err of result.errors) {
            html += `<li>❌ ${escapeHtml(err)}</li>`;
        }
        html += '</ul>';
    }

    if (result.warnings && result.warnings.length > 0) {
        html += '<ul class="warning-list" style="margin-top: 8px;">';
        for (const warn of result.warnings) {
            html += `<li>⚠️ ${escapeHtml(warn)}</li>`;
        }
        html += '</ul>';
    }

    container.innerHTML = html;
}

function renderDataTable(data, containerId) {
    const container = document.getElementById(containerId);

    if (!data.rows || data.rows.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="icon">📭</div>
                <p>Query returned 0 rows.</p>
            </div>
        `;
        return;
    }

    let html = '<div class="data-table-wrap"><table class="data-table"><thead><tr>';
    for (const col of data.columns) {
        html += `<th>${escapeHtml(col)}</th>`;
    }
    html += '</tr></thead><tbody>';

    for (const row of data.rows.slice(0, 100)) {
        html += '<tr>';
        for (const col of data.columns) {
            const val = row[col];
            html += `<td>${val === null ? '<span style="color: var(--accent-error); opacity: 0.6;">NULL</span>' : escapeHtml(String(val))}</td>`;
        }
        html += '</tr>';
    }

    html += '</tbody></table></div>';
    html += `<div class="row-count">${data.row_count} row(s) returned${data.row_count > 100 ? ' (showing first 100)' : ''}</div>`;

    container.innerHTML = html;
}

function renderQAReport(analysis, containerId) {
    const container = document.getElementById(containerId);
    const s = analysis.summary;

    let html = `
        <div class="qa-summary">
            <div class="qa-stat score">
                <span class="value">${s.quality_score}%</span>
                <span class="label">Quality Score</span>
            </div>
            <div class="qa-stat">
                <span class="value" style="color: var(--text-primary);">${s.total_rows}</span>
                <span class="label">Rows</span>
            </div>
            <div class="qa-stat">
                <span class="value" style="color: var(--text-primary);">${s.total_columns}</span>
                <span class="label">Columns</span>
            </div>
            <div class="qa-stat errors">
                <span class="value">${s.errors}</span>
                <span class="label">Errors</span>
            </div>
            <div class="qa-stat warnings">
                <span class="value">${s.warnings}</span>
                <span class="label">Warnings</span>
            </div>
            <div class="qa-stat info">
                <span class="value">${s.info}</span>
                <span class="label">Info</span>
            </div>
        </div>
    `;

    if (analysis.issues.length === 0) {
        html += `
            <div class="empty-state" style="padding: 20px;">
                <p style="color: var(--accent-primary);">✓ No issues detected — dataset looks clean!</p>
            </div>
        `;
    } else {
        for (const issue of analysis.issues) {
            html += `
                <div class="issue-item">
                    <span class="issue-badge ${issue.severity}">${issue.severity}</span>
                    <span class="issue-text">${escapeHtml(issue.message)}</span>
                </div>
            `;
        }
    }

    container.innerHTML = html;
}

// ─── Error Injector ─────────────────────────────────────────────────────────

async function loadInjectionModes() {
    try {
        const result = await apiCall('/api/injection-modes');
        const container = document.getElementById('injection-modes');

        const icons = {
            invalid_json: '🔤',
            wrong_schema: '📐',
            sql_syntax_error: '🐛',
            sql_injection: '💀',
            wrong_types: '🔢',
            unknown_function: '❓',
        };

        container.innerHTML = result.modes.map(mode => `
            <div class="injection-card" onclick="injectError('${mode.id}')">
                <div class="mode-name">${icons[mode.id] || '💉'} ${escapeHtml(mode.name)}</div>
                <div class="mode-desc">${escapeHtml(mode.description)}</div>
            </div>
        `).join('');
    } catch (err) {
        console.error('Failed to load injection modes:', err);
    }
}

async function injectError(mode) {
    const raw = document.getElementById('injector-input').value.trim();
    let call;
    try {
        call = JSON.parse(raw);
    } catch {
        showToast('Base function call is not valid JSON.', 'error');
        return;
    }

    try {
        const result = await apiCall('/api/inject-error', 'POST', { call, mode });

        // Show result
        const resultDiv = document.getElementById('injection-result');
        resultDiv.classList.add('visible');

        document.getElementById('injection-description').textContent =
            `💉 ${result.injection_name}: ${result.injection_description}`;

        document.getElementById('diff-original').textContent =
            JSON.stringify(result.original_call, null, 2);

        const corrupted = result.corrupted_call;
        document.getElementById('diff-corrupted').textContent =
            typeof corrupted === 'string' ? corrupted : JSON.stringify(corrupted, null, 2);

        // Show validation of corrupted
        renderValidation(result.validation_of_corrupted, 'injection-validation');

        showToast(`Injected: ${result.injection_name}`, 'error');
    } catch (err) {
        showToast(`Injection error: ${err.message}`, 'error');
    }
}

// ─── Function Registry ──────────────────────────────────────────────────────

async function loadRegistry() {
    try {
        const result = await apiCall('/api/registry');
        const container = document.getElementById('registry-list');
        document.getElementById('registry-count').textContent = `${result.total} functions`;

        container.innerHTML = result.functions.map(func => `
            <div class="registry-item">
                <div class="func-name">${escapeHtml(func.name)}</div>
                <div class="func-desc">${escapeHtml(func.description)}</div>
                <div class="param-tags">
                    ${func.parameters.map(p => `
                        <span class="param-tag ${p.required ? 'required' : 'optional'}">
                            ${escapeHtml(p.name)}: ${escapeHtml(p.type)}${p.required ? ' *' : ''}
                        </span>
                    `).join('')}
                </div>
            </div>
        `).join('');
    } catch (err) {
        console.error('Failed to load registry:', err);
    }
}

// ─── Sample Calls ───────────────────────────────────────────────────────────

const GOOD_SAMPLES = [
    { name: "query_database", arguments: { query: "SELECT * FROM users WHERE city = 'Dhaka' AND age > 20" } },
    { name: "get_user_stats", arguments: { user_id: 1 } },
    { name: "search_products", arguments: { keyword: "Electronics", max_price: 2000 } },
    { name: "get_order_history", arguments: { user_id: 5, limit: 5 } },
    { name: "query_database", arguments: { query: "SELECT name, email, age FROM users WHERE age >= 25 ORDER BY age DESC" } },
];

const BAD_SAMPLES = [
    { name: "query_database", arguments: { query: "SELECT * FROM users WHERE age => 20" } },
    { name: "query_database", arguments: { query: "SELECT * FROM users WHERE name = '' OR '1'='1'; DROP TABLE users; --" } },
    { name: "query_database", arguments: {} },
    { name: "hack_database", arguments: { query: "SELECT * FROM secrets" } },
    { name: "get_user_stats", arguments: { user_id: "not_a_number" } },
];

function loadSamples() {
    const goodContainer = document.getElementById('good-samples');
    const badContainer = document.getElementById('bad-samples');

    goodContainer.innerHTML = GOOD_SAMPLES.map(call => `
        <div class="sample-item" onclick='loadSample(${JSON.stringify(JSON.stringify(call, null, 2)).replace(/'/g, "\\'")})'>${escapeHtml(JSON.stringify(call, null, 2))}</div>
    `).join('');

    badContainer.innerHTML = BAD_SAMPLES.map(call => `
        <div class="sample-item bad" onclick='loadSample(${JSON.stringify(JSON.stringify(call, null, 2)).replace(/'/g, "\\'")})'>${escapeHtml(JSON.stringify(call, null, 2))}</div>
    `).join('');
}

function loadSample(jsonStr) {
    document.getElementById('validator-input').value = jsonStr;
    showToast('Sample loaded into editor!', 'info');
}

// ─── Analytics Dashboard ────────────────────────────────────────────────────

let chartValidation = null;
let chartErrors = null;
let chartFunctions = null;
let chartSql = null;

const CHART_COLORS = {
    green: '#06d6a0',
    red: '#ef476f',
    yellow: '#ffd166',
    blue: '#118ab2',
    cyan: '#73d2de',
    purple: '#8b5cf6',
    orange: '#f97316',
};

function getChartDefaults() {
    return {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: {
                labels: {
                    color: '#94a3b8',
                    font: { family: "'Inter', sans-serif", size: 12 },
                    padding: 16,
                },
            },
        },
    };
}

async function refreshAnalytics() {
    try {
        const data = await apiCall('/api/analytics');

        // Update stat cards
        document.getElementById('stat-total').textContent = data.total_runs;
        document.getElementById('stat-valid').textContent = `${data.valid_pct}%`;
        document.getElementById('stat-invalid').textContent = `${data.invalid_pct}%`;
        document.getElementById('stat-quality').textContent = data.avg_quality_score || '—';

        // Validation pie chart
        updateValidationChart(data);

        // Error breakdown chart
        updateErrorChart(data);

        // Function usage chart
        updateFunctionChart(data);

        // SQL chart
        updateSqlChart(data);

        // Recent runs table
        renderRecentRuns(data.recent_runs);

    } catch (err) {
        console.error('Failed to refresh analytics:', err);
    }
}

function updateValidationChart(data) {
    const ctx = document.getElementById('chart-validation');
    if (chartValidation) chartValidation.destroy();

    chartValidation = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Valid', 'Invalid', 'Warning'],
            datasets: [{
                data: [data.valid_pct, data.invalid_pct, data.warning_pct],
                backgroundColor: [CHART_COLORS.green, CHART_COLORS.red, CHART_COLORS.yellow],
                borderWidth: 0,
                hoverOffset: 8,
            }],
        },
        options: {
            ...getChartDefaults(),
            cutout: '65%',
            plugins: {
                ...getChartDefaults().plugins,
                legend: {
                    ...getChartDefaults().plugins.legend,
                    position: 'bottom',
                },
            },
        },
    });
}

function updateErrorChart(data) {
    const ctx = document.getElementById('chart-errors');
    if (chartErrors) chartErrors.destroy();

    const labels = Object.keys(data.error_breakdown);
    const values = Object.values(data.error_breakdown);
    const colors = [CHART_COLORS.red, CHART_COLORS.orange, CHART_COLORS.yellow, CHART_COLORS.purple, CHART_COLORS.cyan];

    chartErrors = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Error Count',
                data: values,
                backgroundColor: labels.map((_, i) => colors[i % colors.length] + '80'),
                borderColor: labels.map((_, i) => colors[i % colors.length]),
                borderWidth: 1.5,
                borderRadius: 6,
            }],
        },
        options: {
            ...getChartDefaults(),
            indexAxis: 'y',
            scales: {
                x: {
                    ticks: { color: '#64748b', font: { size: 11 } },
                    grid: { color: 'rgba(148,163,184,0.08)' },
                },
                y: {
                    ticks: { color: '#94a3b8', font: { size: 11 } },
                    grid: { display: false },
                },
            },
            plugins: {
                ...getChartDefaults().plugins,
                legend: { display: false },
            },
        },
    });
}

function updateFunctionChart(data) {
    const ctx = document.getElementById('chart-functions');
    if (chartFunctions) chartFunctions.destroy();

    const labels = Object.keys(data.function_usage);
    const values = Object.values(data.function_usage);
    const colors = [CHART_COLORS.cyan, CHART_COLORS.blue, CHART_COLORS.green, CHART_COLORS.purple, CHART_COLORS.orange];

    chartFunctions = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Calls',
                data: values,
                backgroundColor: labels.map((_, i) => colors[i % colors.length] + '80'),
                borderColor: labels.map((_, i) => colors[i % colors.length]),
                borderWidth: 1.5,
                borderRadius: 6,
            }],
        },
        options: {
            ...getChartDefaults(),
            scales: {
                x: {
                    ticks: { color: '#94a3b8', font: { size: 10 }, maxRotation: 20 },
                    grid: { display: false },
                },
                y: {
                    ticks: { color: '#64748b', font: { size: 11 }, stepSize: 1 },
                    grid: { color: 'rgba(148,163,184,0.08)' },
                },
            },
            plugins: {
                ...getChartDefaults().plugins,
                legend: { display: false },
            },
        },
    });
}

function updateSqlChart(data) {
    const ctx = document.getElementById('chart-sql');
    if (chartSql) chartSql.destroy();

    const successRate = 100 - data.sql_failure_rate;

    chartSql = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Success', 'Failure'],
            datasets: [{
                data: [successRate, data.sql_failure_rate],
                backgroundColor: [CHART_COLORS.green, CHART_COLORS.red],
                borderWidth: 0,
                hoverOffset: 8,
            }],
        },
        options: {
            ...getChartDefaults(),
            cutout: '65%',
            plugins: {
                ...getChartDefaults().plugins,
                legend: {
                    ...getChartDefaults().plugins.legend,
                    position: 'bottom',
                },
            },
        },
    });
}

function renderRecentRuns(runs) {
    const container = document.getElementById('recent-runs');

    if (!runs || runs.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="icon">📊</div>
                <p>No pipeline runs yet. Go to the Pipeline tab to start!</p>
            </div>
        `;
        return;
    }

    let html = `
        <div class="data-table-wrap">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Function</th>
                        <th>Status</th>
                        <th>Executed</th>
                        <th>Quality</th>
                        <th>Issues</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody>
    `;

    for (const run of runs) {
        const time = new Date(run.timestamp).toLocaleTimeString();
        html += `
            <tr>
                <td>${run.id}</td>
                <td style="font-family: var(--font-mono); font-size: 0.8rem;">${escapeHtml(run.function_name)}</td>
                <td><span class="status-dot ${run.validation_status}"></span>${run.validation_status}</td>
                <td>${run.execution_success === null ? '—' : (run.execution_success ? '✅' : '❌')}</td>
                <td>${run.quality_score !== null ? run.quality_score + '%' : '—'}</td>
                <td>${run.dataset_issue_count || '—'}</td>
                <td style="color: var(--text-muted);">${time}</td>
            </tr>
        `;
    }

    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// ─── Clipboard ──────────────────────────────────────────────────────────────

function copyToClipboard(elementId) {
    const el = document.getElementById(elementId);
    const text = el.value || el.textContent;
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard!', 'success');
    }).catch(() => {
        showToast('Failed to copy.', 'error');
    });
}

// ─── Utilities ──────────────────────────────────────────────────────────────

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ─── Initialization ─────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    loadRegistry();
    loadInjectionModes();
    loadSamples();
    refreshAnalytics();
});
