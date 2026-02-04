// Leaderboard filtering and sorting functionality

let leaderboardData = null;
const tableSortStates = new WeakMap();

function loadLeaderboardData() {
    if (!leaderboardData) {
        const dataScript = document.getElementById('leaderboard-data');
        if (dataScript) {
            try {
                leaderboardData = JSON.parse(dataScript.textContent);
            } catch (error) {
                // Keep sorting/filtering functional even if embedded JSON is invalid.
                console.warn('Failed to parse leaderboard data:', error);
                leaderboardData = null;
            }
        }
    }
    return leaderboardData;
}

function initLeaderboard() {
    // Data is optional for sorting; keep UI interactions enabled regardless.
    loadLeaderboardData();

    // Set up filter event listeners
    const difficultyFilter = document.getElementById('difficulty-filter');
    const modelFilter = document.getElementById('model-filter');
    const taskFilter = document.getElementById('task-filter');

    if (difficultyFilter) {
        difficultyFilter.addEventListener('change', applyFilters);
    }
    if (modelFilter) {
        modelFilter.addEventListener('change', applyFilters);
    }
    if (taskFilter) {
        taskFilter.addEventListener('change', applyFilters);
    }

    // Set up sortable headers
    const sortableHeaders = document.querySelectorAll('.table th.sortable');
    sortableHeaders.forEach(header => {
        header.addEventListener('click', () => handleSort(header));
    });

    // Initialize per-table sort states from markup and apply initial sorts.
    initializeTableSortStates();
}

function applyFilters() {
    const difficultyFilter = document.getElementById('difficulty-filter');
    const modelFilter = document.getElementById('model-filter');
    const taskFilter = document.getElementById('task-filter');

    const difficulty = difficultyFilter ? difficultyFilter.value : 'all';
    const model = modelFilter ? modelFilter.value : 'all';
    const task = taskFilter ? taskFilter.value : 'all';

    const tableBody = document.getElementById('leaderboard-body');
    if (!tableBody) return;

    const rows = tableBody.querySelectorAll('tr');
    let visibleCount = 0;

    rows.forEach(row => {
        const rowDifficulty = row.getAttribute('data-difficulty');
        const rowModel = row.getAttribute('data-model');
        const rowTask = row.getAttribute('data-task');

        const matchesDifficulty = difficulty === 'all' || rowDifficulty === difficulty;
        const matchesModel = model === 'all' || rowModel === model;
        const matchesTask = task === 'all' || rowTask === task;

        if (matchesDifficulty && matchesModel && matchesTask) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });

    // Show/hide no results message
    const noResults = document.querySelector('.no-results');
    if (noResults) {
        noResults.style.display = visibleCount === 0 ? 'block' : 'none';
    }
}

function handleSort(header) {
    const table = header.closest('table');
    if (!table) return;

    const field = header.getAttribute('data-sort');
    const sortState = getTableSortState(table);

    if (sortState.field === field) {
        // Toggle direction
        sortState.direction = sortState.direction === 'asc' ? 'desc' : 'asc';
    } else {
        sortState.field = field;
        // Default direction based on field type
        const textFields = ['model', 'task', 'difficulty', 'org'];
        sortState.direction = textFields.includes(field) ? 'asc' : 'desc';
    }

    tableSortStates.set(table, sortState);
    sortTable(table, sortState);
    updateSortIndicators(table);
}

function initializeTableSortStates() {
    const tables = document.querySelectorAll('.table');
    tables.forEach(table => {
        const sortedHeader = table.querySelector('th.sortable.sorted-asc, th.sortable.sorted-desc');
        if (!sortedHeader) return;

        const field = sortedHeader.getAttribute('data-sort');
        const direction = sortedHeader.classList.contains('sorted-asc') ? 'asc' : 'desc';
        const sortState = { field, direction };

        tableSortStates.set(table, sortState);
        sortTable(table, sortState);
        updateSortIndicators(table);
    });
}

function getTableSortState(table) {
    const existingState = tableSortStates.get(table);
    if (existingState) {
        return existingState;
    }
    const defaultState = { field: '', direction: 'asc' };
    tableSortStates.set(table, defaultState);
    return defaultState;
}

function sortTable(table, sortState) {
    const tableBody = table.querySelector('tbody');
    if (!tableBody) return;

    const rows = Array.from(tableBody.querySelectorAll('tr'));

    rows.sort((a, b) => {
        const aValue = getSortValue(a, sortState.field);
        const bValue = getSortValue(b, sortState.field);
        return compareSortValues(aValue, bValue, sortState.direction);
    });

    // Re-append rows in sorted order
    rows.forEach(row => tableBody.appendChild(row));
}

function getSortValue(row, field) {
    switch (field) {
        case 'model':
            return getCellText(row, '.model-cell .model-name') || row.getAttribute('data-model') || '';
        case 'org':
            return getCellText(row, '.org-cell');
        case 'task':
            return row.getAttribute('data-task') || getCellText(row, '.task-cell .task-name');
        case 'difficulty':
            const diff = row.getAttribute('data-difficulty') || getCellText(row, '.difficulty-cell');
            // Sort order: easy, medium, hard
            return { 'easy': 0, 'medium': 1, 'hard': 2 }[diff] || 3;
        case 'passed':
            const passedCell = row.querySelector('.passed-cell .status-badge');
            return passedCell && passedCell.classList.contains('status-passed') ? 1 : 0;
        case 'tasks':
            return parseTasksPassed(getCellText(row, '.tasks-cell'));
        case 'pass_rate':
            return parseFloat(row.getAttribute('data-pass-rate')) ||
                parsePercent(getCellText(row, '.pass-rate-cell .pass-rate-value'));
        case 'duration':
            return parseDurationHours(getCellText(row, '.duration-cell'));
        case 'time':
            return parseDurationHours(getCellText(row, '.time-cell'));
        case 'loc':
            return parseInteger(getCellText(row, '.loc-cell'));
        case 'cost':
            return parseCurrency(getCellText(row, '.cost-cell'));
        case 'actions_total':
            return parseInteger(getCellText(row, '.actions-total-cell'));
        case 'behavior_spec_understanding':
            return parsePercent(getCellText(row, '.behavior-spec-understanding-cell'));
        case 'behavior_planning':
            return parsePercent(getCellText(row, '.behavior-planning-cell'));
        case 'behavior_code_understanding':
            return parsePercent(getCellText(row, '.behavior-code-understanding-cell'));
        case 'behavior_code_writing':
            return parsePercent(getCellText(row, '.behavior-code-writing-cell'));
        case 'behavior_debugging':
            return parsePercent(getCellText(row, '.behavior-debugging-cell'));
        case 'behavior_hygiene':
            return parsePercent(getCellText(row, '.behavior-hygiene-cell'));
        case 'behavior_external_search':
            return parsePercent(getCellText(row, '.behavior-external-search-cell'));
        case 'behavior_other':
            return parsePercent(getCellText(row, '.behavior-other-cell'));
        default:
            return '';
    }
}

function getCellText(row, selector) {
    const cell = row.querySelector(selector);
    return cell ? cell.textContent.trim() : '';
}

function parseTasksPassed(text) {
    if (!text || text === 'N/A') return null;
    const match = text.match(/(\d+)\s*\/\s*(\d+)/);
    if (!match) return null;
    return parseInt(match[1], 10);
}

function parsePercent(text) {
    if (!text || text === 'N/A') return null;
    const numeric = parseFloat(text.replace('%', ''));
    return Number.isNaN(numeric) ? null : numeric;
}

function parseDurationHours(text) {
    if (!text || text === 'N/A') return null;
    const numeric = parseFloat(text.replace('h', ''));
    return Number.isNaN(numeric) ? null : numeric;
}

function parseInteger(text) {
    if (!text || text === 'N/A') return null;
    const numeric = parseInt(text, 10);
    return Number.isNaN(numeric) ? null : numeric;
}

function parseCurrency(text) {
    if (!text || text === 'N/A') return null;
    const numeric = parseFloat(text.replace(/[^0-9.-]/g, ''));
    return Number.isNaN(numeric) ? null : numeric;
}

function isMissingValue(value) {
    return value === null || value === undefined || (typeof value === 'number' && Number.isNaN(value));
}

function compareSortValues(aValue, bValue, direction) {
    const aMissing = isMissingValue(aValue);
    const bMissing = isMissingValue(bValue);

    // Always place missing values at the bottom.
    if (aMissing && bMissing) return 0;
    if (aMissing) return 1;
    if (bMissing) return -1;

    if (typeof aValue === 'number' && typeof bValue === 'number') {
        return direction === 'asc' ? aValue - bValue : bValue - aValue;
    }

    const result = String(aValue).localeCompare(String(bValue), undefined, {
        numeric: true,
        sensitivity: 'base'
    });
    return direction === 'asc' ? result : -result;
}

function updateSortIndicators(table) {
    const headers = table.querySelectorAll('th.sortable');
    headers.forEach(header => {
        header.classList.remove('sorted-asc', 'sorted-desc');

        const field = header.getAttribute('data-sort');
        const sortState = getTableSortState(table);
        if (field === sortState.field) {
            header.classList.add(sortState.direction === 'asc' ? 'sorted-asc' : 'sorted-desc');
        }
    });
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initLeaderboard);
