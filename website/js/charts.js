// Chart.js visualizations for SWE-AGI leaderboard

let passRateChart = null;
let modelRadarChart = null;
let behaviorCompositionChart = null;

const RADAR_MODEL_IDS = [
    'gpt-5.3-codex-xhigh',
    'claude-opus-4.6',
    'gpt-5.2-codex-high',
    'claude-opus-4.5',
];

const RADAR_AXIS_SCALE_MODE = {
    LINEAR: 'linear',
    RECIPROCAL: 'reciprocal',
};

const RADAR_INVERSE_EPSILON = 1e-9;

const RADAR_AXIS_CONFIG = [
    { key: 'task_passed', label: 'Task Passed', scaleMode: RADAR_AXIS_SCALE_MODE.LINEAR },
    { key: 'avg_cost', label: '1 / (Avg. Cost)', scaleMode: RADAR_AXIS_SCALE_MODE.RECIPROCAL },
    { key: 'avg_duration', label: '1 / (Avg. Duration)', scaleMode: RADAR_AXIS_SCALE_MODE.RECIPROCAL },
    { key: 'avg_core_loc', label: '1 / (Avg. Core LOC)', scaleMode: RADAR_AXIS_SCALE_MODE.RECIPROCAL },
    { key: 'avg_actions', label: '1 / (Avg. Actions)', scaleMode: RADAR_AXIS_SCALE_MODE.RECIPROCAL },
    { key: 'test_pass_rate', label: 'Test Pass Rate', scaleMode: RADAR_AXIS_SCALE_MODE.LINEAR },
];

const RADAR_MODEL_COLORS = {
    'gpt-5.3-codex-xhigh': {
        stroke: 'rgba(37, 99, 235, 1)',
        fill: 'rgba(37, 99, 235, 0.20)',
    },
    'claude-opus-4.6': {
        stroke: 'rgba(5, 150, 105, 1)',
        fill: 'rgba(5, 150, 105, 0.20)',
    },
    'gpt-5.2-codex-high': {
        stroke: 'rgba(234, 88, 12, 1)',
        fill: 'rgba(234, 88, 12, 0.20)',
    },
    'claude-opus-4.5': {
        stroke: 'rgba(147, 51, 234, 1)',
        fill: 'rgba(147, 51, 234, 0.20)',
    },
};

const BEHAVIOR_CATEGORY_ORDER = [
    'spec_understanding',
    'planning',
    'code_understanding',
    'code_writing',
    'debugging',
    'hygiene',
    'external_search',
    'other',
];

const BEHAVIOR_CATEGORY_COLORS = {
    spec_understanding: 'rgba(59, 130, 246, 0.9)',
    planning: 'rgba(245, 158, 11, 0.9)',
    code_understanding: 'rgba(20, 184, 166, 0.9)',
    code_writing: 'rgba(99, 102, 241, 0.9)',
    debugging: 'rgba(239, 68, 68, 0.9)',
    hygiene: 'rgba(16, 185, 129, 0.9)',
    external_search: 'rgba(168, 85, 247, 0.9)',
    other: 'rgba(107, 114, 128, 0.9)',
};

const radarModelVisibility = new Map(RADAR_MODEL_IDS.map((modelId) => [modelId, true]));
let radarToggleInitialized = false;
let radarDefaultEmptyMessage = null;
let behaviorCompositionDefaultEmptyMessage = null;

function initCharts() {
    if (typeof loadLeaderboardData !== 'function') return;

    const data = loadLeaderboardData();
    if (!data) return;

    initModelRadarToggles(data);

    if (data.summaries && Array.isArray(data.summaries.by_model)) {
        renderPassRateChart(data.summaries.by_model, data.models || []);
    }
    renderModelComparisonRadar(data);
    renderBehaviorCompositionChart(data);
}

function renderPassRateChart(summaries, models) {
    const canvas = document.getElementById('pass-rate-chart');
    if (!canvas || typeof Chart === 'undefined') return;

    const ctx = canvas.getContext('2d');

    // Sort by pass rate descending
    const sortedSummaries = [...summaries].sort((a, b) => b.pass_rate - a.pass_rate);

    const labels = sortedSummaries.map((summary) => {
        const model = models.find((item) => item.id === summary.model_id);
        return model ? model.display_name : summary.model_id;
    });

    const passRates = sortedSummaries.map((summary) => summary.pass_rate);

    // Destroy existing chart if present
    if (passRateChart) {
        passRateChart.destroy();
    }

    const isDarkMode = document.body.classList.contains('dark-mode');

    passRateChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Pass Rate (%)',
                data: passRates,
                backgroundColor: 'rgba(59, 130, 246, 0.8)',
                borderColor: 'rgba(59, 130, 246, 1)',
                borderWidth: 1,
                borderRadius: 4,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false,
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            return `Pass Rate: ${context.raw.toFixed(1)}%`;
                        },
                    },
                },
            },
            scales: {
                x: {
                    beginAtZero: true,
                    max: 100,
                    grid: {
                        color: isDarkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
                    },
                    ticks: {
                        color: isDarkMode ? '#9ca3af' : '#4b5563',
                        callback: function (value) {
                            return `${value}%`;
                        },
                    },
                },
                y: {
                    grid: {
                        display: false,
                    },
                    ticks: {
                        color: isDarkMode ? '#9ca3af' : '#4b5563',
                    },
                },
            },
        },
    });
}

function renderDifficultyComparison(summaries, models) {
    const canvas = document.getElementById('difficulty-chart');
    if (!canvas || typeof Chart === 'undefined') return;

    const ctx = canvas.getContext('2d');

    // Group by difficulty
    const difficulties = ['easy', 'medium', 'hard'];
    const modelIds = [...new Set(summaries.map((summary) => summary.model_id))];

    const datasets = modelIds.map((modelId, index) => {
        const model = models.find((item) => item.id === modelId);
        const data = difficulties.map((difficulty) => {
            const summary = summaries.find((item) => item.model_id === modelId && item.difficulty === difficulty);
            return summary ? summary.pass_rate : 0;
        });

        // Generate distinct colors
        const hue = (index * 137.5) % 360;
        const color = `hsl(${hue}, 70%, 50%)`;

        return {
            label: model ? model.display_name : modelId,
            data: data,
            backgroundColor: color.replace('50%)', '50%, 0.7)'),
            borderColor: color,
            borderWidth: 1,
        };
    });

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Easy', 'Medium', 'Hard'],
            datasets: datasets,
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function (value) {
                            return `${value}%`;
                        },
                    },
                },
            },
        },
    });
}

function numberOrNull(value) {
    return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function averageNumbers(values) {
    const numbers = values.filter((value) => typeof value === 'number' && Number.isFinite(value));
    if (numbers.length === 0) return null;
    const total = numbers.reduce((sum, value) => sum + value, 0);
    return total / numbers.length;
}

function getRadarColor(modelId, index) {
    if (RADAR_MODEL_COLORS[modelId]) {
        return RADAR_MODEL_COLORS[modelId];
    }

    const hue = (index * 137.5) % 360;
    return {
        stroke: `hsl(${hue}, 70%, 45%)`,
        fill: `hsla(${hue}, 70%, 45%, 0.20)`,
    };
}

function setModelToggleButtonState(button, isVisible) {
    button.classList.toggle('active', isVisible);
    button.setAttribute('aria-pressed', String(isVisible));
}

function initModelRadarToggles(data) {
    const container = document.getElementById('model-radar-toggles');
    if (!container || radarToggleInitialized) return;

    const models = Array.isArray(data.models) ? data.models : [];

    RADAR_MODEL_IDS.forEach((modelId, index) => {
        const model = models.find((item) => item.id === modelId);
        const colors = getRadarColor(modelId, index);
        const button = document.createElement('button');
        const isVisible = radarModelVisibility.get(modelId) !== false;

        button.type = 'button';
        button.className = 'filter-btn model-toggle-btn';
        button.dataset.modelId = modelId;
        button.textContent = model ? model.display_name : modelId;
        button.style.setProperty('--model-color', colors.stroke);
        setModelToggleButtonState(button, isVisible);

        button.addEventListener('click', () => {
            const currentlyVisible = radarModelVisibility.get(modelId) !== false;
            const nextVisible = !currentlyVisible;
            radarModelVisibility.set(modelId, nextVisible);
            setModelToggleButtonState(button, nextVisible);

            const latestData = typeof loadLeaderboardData === 'function' ? loadLeaderboardData() : data;
            renderModelComparisonRadar(latestData || data);
            renderBehaviorCompositionChart(latestData || data);
        });

        container.appendChild(button);
    });

    radarToggleInitialized = true;
}

function getVisibleRadarModelIds() {
    return RADAR_MODEL_IDS.filter((modelId) => radarModelVisibility.get(modelId) !== false);
}

function getModelComparisonStats(data, modelIds) {
    if (!Array.isArray(data.results) || !Array.isArray(data.models) || !Array.isArray(modelIds) || modelIds.length === 0) {
        return [];
    }

    const modelIdSet = new Set(modelIds);

    const resultBuckets = new Map();
    data.results.forEach((result) => {
        if (!modelIdSet.has(result.model_id)) return;
        if (!resultBuckets.has(result.model_id)) {
            resultBuckets.set(result.model_id, []);
        }
        resultBuckets.get(result.model_id).push(result);
    });

    const summaries = data.summaries && Array.isArray(data.summaries.by_model) ? data.summaries.by_model : [];
    const summaryByModelId = new Map(summaries.map((summary) => [summary.model_id, summary]));

    return modelIds.map((modelId) => {
        const model = data.models.find((item) => item.id === modelId);
        const modelResults = resultBuckets.get(modelId) || [];
        const summary = summaryByModelId.get(modelId);

        if (!model && !summary && modelResults.length === 0) {
            return null;
        }

        const taskPassedFromSummary = numberOrNull(summary && summary.tasks_passed);
        const taskPassedFromResults = modelResults.filter((result) => result.task_passed === true).length;

        const raw = {
            task_passed: taskPassedFromSummary ?? taskPassedFromResults,
            test_pass_rate: averageNumbers(modelResults.map((result) => numberOrNull(result.tests && result.tests.pass_rate))),
            avg_cost: averageNumbers(modelResults.map((result) => numberOrNull(result.metrics && result.metrics.cost_usd))),
            avg_duration: averageNumbers(modelResults.map((result) => numberOrNull(result.metrics && result.metrics.elapsed_ms))),
            avg_core_loc: averageNumbers(modelResults.map((result) => numberOrNull(result.metrics && result.metrics.code_loc))),
            avg_actions: averageNumbers(modelResults.map((result) => numberOrNull(result.metrics && result.metrics.actions))),
        };

        return {
            modelId: modelId,
            displayName: model ? model.display_name : modelId,
            raw: raw,
        };
    }).filter(Boolean);
}

function getBehaviorCategoryLabel(data, categoryKey) {
    const metadata = data && data.metadata ? data.metadata : null;
    const behaviorCategories = metadata && metadata.behavior_categories ? metadata.behavior_categories : null;
    if (behaviorCategories && typeof behaviorCategories[categoryKey] === 'string') {
        return behaviorCategories[categoryKey];
    }

    return categoryKey
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (char) => char.toUpperCase());
}

function getModelDisplayName(data, modelId) {
    if (!Array.isArray(data.models)) return modelId;
    const model = data.models.find((item) => item.id === modelId);
    return model ? model.display_name : modelId;
}

function getBehaviorCompositionStats(data, modelIds) {
    if (!Array.isArray(data.results) || !Array.isArray(modelIds) || modelIds.length === 0) {
        return [];
    }

    const modelIdSet = new Set(modelIds);
    const bucketsByModelId = new Map();

    modelIds.forEach((modelId) => {
        const counts = {};
        BEHAVIOR_CATEGORY_ORDER.forEach((categoryKey) => {
            counts[categoryKey] = 0;
        });

        bucketsByModelId.set(modelId, {
            modelId: modelId,
            displayName: getModelDisplayName(data, modelId),
            counts: counts,
            total: 0,
        });
    });

    data.results.forEach((result) => {
        if (!result || !modelIdSet.has(result.model_id)) return;

        const bucket = bucketsByModelId.get(result.model_id);
        if (!bucket) return;

        const behavior = result.metrics && result.metrics.behavior ? result.metrics.behavior : null;
        if (!behavior) return;

        let rowTotal = 0;

        BEHAVIOR_CATEGORY_ORDER.forEach((categoryKey) => {
            const count = numberOrNull(behavior[categoryKey]);
            if (count === null || count < 0) return;

            bucket.counts[categoryKey] += count;
            rowTotal += count;
        });

        const behaviorTotal = numberOrNull(behavior.total);
        if (behaviorTotal !== null && behaviorTotal > rowTotal) {
            const unassignedCount = behaviorTotal - rowTotal;
            bucket.counts.other += unassignedCount;
            rowTotal += unassignedCount;
        }

        bucket.total += rowTotal;
    });

    return modelIds
        .map((modelId) => bucketsByModelId.get(modelId))
        .filter((bucket) => bucket && bucket.total > 0);
}

function getTotalTaskCount(data) {
    if (Array.isArray(data.tasks) && data.tasks.length > 0) {
        return data.tasks.length;
    }

    if (Array.isArray(data.results)) {
        const taskIds = new Set(data.results.map((result) => result.task_id).filter(Boolean));
        return taskIds.size;
    }

    return 0;
}

function transformRadarAxisValue(axis, rawValue) {
    const value = numberOrNull(rawValue);
    if (value === null) return null;

    if (axis.scaleMode === RADAR_AXIS_SCALE_MODE.RECIPROCAL) {
        const safeValue = Math.max(value, RADAR_INVERSE_EPSILON);
        return 1 / safeValue;
    }

    return value;
}

function scaleRadarMetrics(modelStats) {
    const axisMaxByKey = new Map();

    RADAR_AXIS_CONFIG.forEach((axis) => {
        const transformedValues = modelStats
            .map((item) => transformRadarAxisValue(axis, item.raw[axis.key]))
            .filter((value) => value !== null);

        if (transformedValues.length === 0) {
            axisMaxByKey.set(axis.key, null);
            return;
        }

        axisMaxByKey.set(axis.key, Math.max(...transformedValues));
    });

    return modelStats.map((stat) => {
        const scaled = {};

        RADAR_AXIS_CONFIG.forEach((axis) => {
            const transformedValue = transformRadarAxisValue(axis, stat.raw[axis.key]);
            const max = axisMaxByKey.get(axis.key);

            if (transformedValue === null || max === null) {
                scaled[axis.key] = null;
                return;
            }

            if (max <= 0) {
                scaled[axis.key] = 0;
                return;
            }

            scaled[axis.key] = (transformedValue / max) * 100;
        });

        return {
            ...stat,
            scaled: scaled,
        };
    });
}

function formatDurationValue(value) {
    if (typeof formatDuration === 'function') {
        return formatDuration(value);
    }
    if (value === null || value === undefined) return 'N/A';
    const hours = value / (1000 * 60 * 60);
    if (hours < 1) return `${hours.toFixed(2)}h`;
    return `${hours.toFixed(1)}h`;
}

function formatCostValue(value) {
    if (typeof formatCost === 'function') {
        return formatCost(value);
    }
    if (value === null || value === undefined) return 'N/A';
    return `$${value.toFixed(2)}`;
}

function formatTokenValue(value) {
    if (typeof formatTokens === 'function') {
        return formatTokens(value);
    }
    if (value === null || value === undefined) return 'N/A';
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
    if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
    return String(Math.round(value));
}

function formatActionsValue(value) {
    if (value === null || value === undefined) return 'N/A';
    return (Math.round(value * 10) / 10).toFixed(1);
}

function formatBehaviorActionCount(value) {
    if (value === null || value === undefined || Number.isNaN(value)) return 'N/A';
    return Math.round(value).toLocaleString();
}

function formatRawMetric(metricKey, rawValue, totalTasks) {
    if (rawValue === null || rawValue === undefined || Number.isNaN(rawValue)) {
        return 'N/A';
    }

    switch (metricKey) {
        case 'task_passed':
            return `${Math.round(rawValue)}/${totalTasks}`;
        case 'test_pass_rate':
            return `${rawValue.toFixed(1)}%`;
        case 'avg_cost':
            return formatCostValue(rawValue);
        case 'avg_duration':
            return formatDurationValue(rawValue);
        case 'avg_core_loc':
            return Math.round(rawValue).toLocaleString();
        case 'avg_actions':
            return formatActionsValue(rawValue);
        default:
            return String(rawValue);
    }
}

function setRadarEmptyState(isVisible, message = null) {
    const emptyState = document.getElementById('model-radar-empty');
    if (!emptyState) return;

    if (radarDefaultEmptyMessage === null) {
        radarDefaultEmptyMessage = emptyState.textContent.trim();
    }

    emptyState.textContent = message || radarDefaultEmptyMessage;
    emptyState.hidden = !isVisible;
}

function setBehaviorCompositionEmptyState(isVisible, message = null) {
    const emptyState = document.getElementById('behavior-composition-empty');
    if (!emptyState) return;

    if (behaviorCompositionDefaultEmptyMessage === null) {
        behaviorCompositionDefaultEmptyMessage = emptyState.textContent.trim();
    }

    emptyState.textContent = message || behaviorCompositionDefaultEmptyMessage;
    emptyState.hidden = !isVisible;
}

function renderModelComparisonRadar(data) {
    const canvas = document.getElementById('model-radar-chart');
    if (!canvas || typeof Chart === 'undefined') return;

    const visibleModelIds = getVisibleRadarModelIds();
    if (visibleModelIds.length === 0) {
        setRadarEmptyState(true, 'All models are hidden. Toggle at least one model to render the radar.');
        if (modelRadarChart) {
            modelRadarChart.destroy();
            modelRadarChart = null;
        }
        return;
    }

    const modelStats = getModelComparisonStats(data, visibleModelIds);
    const totalTasks = getTotalTaskCount(data);

    if (modelStats.length === 0) {
        setRadarEmptyState(true);
        if (modelRadarChart) {
            modelRadarChart.destroy();
            modelRadarChart = null;
        }
        return;
    }

    const scaledStats = scaleRadarMetrics(modelStats);
    const isDarkMode = document.body.classList.contains('dark-mode');

    const datasets = scaledStats.map((stat, index) => {
        const colors = getRadarColor(stat.modelId, index);

        return {
            label: stat.displayName,
            data: RADAR_AXIS_CONFIG.map((axis) => stat.scaled[axis.key]),
            borderColor: colors.stroke,
            backgroundColor: colors.fill,
            borderWidth: 2,
            pointRadius: 3,
            pointHoverRadius: 5,
            pointBackgroundColor: colors.stroke,
            pointBorderColor: isDarkMode ? '#111827' : '#ffffff',
            pointBorderWidth: 1,
            rawValues: RADAR_AXIS_CONFIG.map((axis) => stat.raw[axis.key]),
            metricKeys: RADAR_AXIS_CONFIG.map((axis) => axis.key),
        };
    });

    const hasRenderableData = datasets.some((dataset) =>
        dataset.data.some((value) => typeof value === 'number' && Number.isFinite(value))
    );

    if (!hasRenderableData) {
        setRadarEmptyState(true);
        if (modelRadarChart) {
            modelRadarChart.destroy();
            modelRadarChart = null;
        }
        return;
    }

    setRadarEmptyState(false);

    if (modelRadarChart) {
        modelRadarChart.destroy();
    }

    const ctx = canvas.getContext('2d');
    modelRadarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: RADAR_AXIS_CONFIG.map((axis) => axis.label),
            datasets: datasets,
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            elements: {
                line: {
                    tension: 0.2,
                },
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: isDarkMode ? '#d1d5db' : '#374151',
                    },
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const dataset = context.dataset;
                            const dataIndex = context.dataIndex;
                            const axisLabel = context.label || '';
                            const metricKey = dataset.metricKeys ? dataset.metricKeys[dataIndex] : '';
                            const rawValue = dataset.rawValues ? dataset.rawValues[dataIndex] : null;
                            const rawDisplay = formatRawMetric(metricKey, rawValue, totalTasks);
                            const scaledValue = numberOrNull(context.raw);
                            const scaledDisplay = scaledValue === null ? 'N/A' : scaledValue.toFixed(1);
                            return `${dataset.label} · ${axisLabel}: ${rawDisplay} (score ${scaledDisplay})`;
                        },
                    },
                },
            },
            scales: {
                r: {
                    beginAtZero: true,
                    min: 0,
                    max: 100,
                    ticks: {
                        stepSize: 20,
                        color: isDarkMode ? '#9ca3af' : '#4b5563',
                        backdropColor: 'transparent',
                    },
                    pointLabels: {
                        color: isDarkMode ? '#e5e7eb' : '#111827',
                        font: {
                            size: 12,
                        },
                    },
                    angleLines: {
                        color: isDarkMode ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.12)',
                    },
                    grid: {
                        color: isDarkMode ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.12)',
                    },
                },
            },
        },
    });
}

function renderBehaviorCompositionChart(data) {
    const canvas = document.getElementById('behavior-composition-chart');
    if (!canvas || typeof Chart === 'undefined') return;

    const visibleModelIds = getVisibleRadarModelIds();
    if (visibleModelIds.length === 0) {
        setBehaviorCompositionEmptyState(true, 'All models are hidden. Toggle at least one model to render behavior composition.');
        if (behaviorCompositionChart) {
            behaviorCompositionChart.destroy();
            behaviorCompositionChart = null;
        }
        return;
    }

    const modelProfiles = getBehaviorCompositionStats(data, visibleModelIds);
    if (modelProfiles.length === 0) {
        setBehaviorCompositionEmptyState(true);
        if (behaviorCompositionChart) {
            behaviorCompositionChart.destroy();
            behaviorCompositionChart = null;
        }
        return;
    }

    const isDarkMode = document.body.classList.contains('dark-mode');
    const profileTotals = modelProfiles.map((profile) => profile.total);

    const datasets = BEHAVIOR_CATEGORY_ORDER.map((categoryKey) => {
        const rawCounts = modelProfiles.map((profile) => profile.counts[categoryKey] || 0);
        const percentages = modelProfiles.map((profile, index) => {
            const total = profile.total;
            if (total <= 0) return 0;
            return (rawCounts[index] / total) * 100;
        });

        return {
            label: getBehaviorCategoryLabel(data, categoryKey),
            data: percentages,
            rawCounts: rawCounts,
            totals: profileTotals,
            backgroundColor: BEHAVIOR_CATEGORY_COLORS[categoryKey] || 'rgba(107, 114, 128, 0.9)',
            borderColor: isDarkMode ? 'rgba(17, 24, 39, 0.95)' : 'rgba(255, 255, 255, 0.95)',
            borderWidth: 1,
            borderSkipped: false,
        };
    }).filter((dataset) => dataset.data.some((value) => value > 0));

    if (datasets.length === 0) {
        setBehaviorCompositionEmptyState(true);
        if (behaviorCompositionChart) {
            behaviorCompositionChart.destroy();
            behaviorCompositionChart = null;
        }
        return;
    }

    setBehaviorCompositionEmptyState(false);

    if (behaviorCompositionChart) {
        behaviorCompositionChart.destroy();
    }

    const ctx = canvas.getContext('2d');
    behaviorCompositionChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: modelProfiles.map((profile) => profile.displayName),
            datasets: datasets,
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: isDarkMode ? '#d1d5db' : '#374151',
                        boxWidth: 14,
                        boxHeight: 14,
                    },
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const dataset = context.dataset;
                            const dataIndex = context.dataIndex;
                            const percent = numberOrNull(context.raw) ?? 0;
                            const rawCount = dataset.rawCounts ? numberOrNull(dataset.rawCounts[dataIndex]) : null;
                            const rawDisplay = formatBehaviorActionCount(rawCount);
                            return `${dataset.label}: ${percent.toFixed(1)}% (${rawDisplay} actions)`;
                        },
                        footer: function (items) {
                            if (!items || items.length === 0) return '';
                            const firstItem = items[0];
                            const dataIndex = firstItem.dataIndex;
                            const totals = firstItem.dataset && firstItem.dataset.totals ? firstItem.dataset.totals : null;
                            const totalCount = totals ? numberOrNull(totals[dataIndex]) : null;
                            if (totalCount === null) return '';
                            return `Total categorized actions: ${formatBehaviorActionCount(totalCount)}`;
                        },
                    },
                },
            },
            scales: {
                x: {
                    stacked: true,
                    beginAtZero: true,
                    min: 0,
                    max: 100,
                    ticks: {
                        stepSize: 20,
                        color: isDarkMode ? '#9ca3af' : '#4b5563',
                        callback: function (value) {
                            return `${value}%`;
                        },
                    },
                    grid: {
                        color: isDarkMode ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.10)',
                    },
                    title: {
                        display: true,
                        text: 'Share of tool actions',
                        color: isDarkMode ? '#9ca3af' : '#4b5563',
                    },
                },
                y: {
                    stacked: true,
                    ticks: {
                        color: isDarkMode ? '#d1d5db' : '#374151',
                    },
                    grid: {
                        display: false,
                    },
                },
            },
        },
    });
}

// Re-render charts when theme changes
function onThemeChange() {
    if (typeof loadLeaderboardData !== 'function') return;

    const data = loadLeaderboardData();
    if (!data) return;

    if (data.summaries && Array.isArray(data.summaries.by_model)) {
        renderPassRateChart(data.summaries.by_model, data.models || []);
    }
    renderModelComparisonRadar(data);
    renderBehaviorCompositionChart(data);
}

// Watch for theme changes
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.attributeName === 'class') {
            onThemeChange();
        }
    });
});

document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    observer.observe(document.body, { attributes: true });
});
