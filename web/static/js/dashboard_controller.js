/**
 * Arkanalyzer Knowledge Graph System - Dashboard Controller
 * ==========================================================
 * 仪表盘页面的JavaScript控制器，负责数据加载和图表渲染。
 */

// ============================================================
// 全局状态
// ============================================================
let dashboardCharts = {};
let autoRefreshTimer = null;

// ============================================================
// 页面初始化
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
    loadDashboardData();
    startAutoRefresh();
});

// ============================================================
// 数据加载
// ============================================================
async function loadDashboardData() {
    await Promise.all([
        loadGraphSummary(),
        loadEntityStatistics(),
        loadRelationStatistics(),
        loadRecentSessions(),
        loadSystemInfo()
    ]);
}

async function loadGraphSummary() {
    try {
        const response = await fetch('/api/graph_summary');
        const data = await response.json();

        animateNumber('total_entities', data.totalEntities || 0);
        animateNumber('total_relations', data.totalRelations || 0);
        animateNumber('total_files', data.totalFiles || 0);
        animateNumber('total_sessions', data.totalSessions || 0);

        const updateTime = document.getElementById('last_update_time');
        if (updateTime && data.lastUpdate) {
            updateTime.textContent = '更新: ' + data.lastUpdate;
        }
    } catch (error) {
        console.error('加载图谱摘要失败:', error);
    }
}

async function loadEntityStatistics() {
    try {
        const response = await fetch('/api/entity_statistics');
        const data = await response.json();
        renderPieChart('entity_type_chart', data, '实体类型分布');
    } catch (error) {
        console.error('加载实体统计失败:', error);
    }
}

async function loadRelationStatistics() {
    try {
        const response = await fetch('/api/relation_statistics');
        const data = await response.json();
        renderPieChart('relation_type_chart', data, '关系类型分布');
    } catch (error) {
        console.error('加载关系统计失败:', error);
    }
}

async function loadRecentSessions() {
    try {
        const response = await fetch('/api/recent_sessions');
        const sessions = await response.json();
        renderSessionsList(sessions);
    } catch (error) {
        console.error('加载会话列表失败:', error);
    }
}

async function loadSystemInfo() {
    try {
        const response = await fetch('/api/system_info');
        const info = await response.json();

        const watcherStatus = document.getElementById('watcher_status');
        if (watcherStatus) {
            watcherStatus.textContent = info.projectRoot || '--';
        }
    } catch (error) {
        console.error('加载系统信息失败:', error);
    }
}

// ============================================================
// 图表渲染
// ============================================================
function renderPieChart(containerId, statistics, chartTitle) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (dashboardCharts[containerId]) {
        dashboardCharts[containerId].dispose();
    }

    const chart = echarts.init(container, 'dark');
    dashboardCharts[containerId] = chart;

    const colorPalette = [
        '#3b82f6', '#8b5cf6', '#10b981', '#f59e0b',
        '#ef4444', '#06b6d4', '#ec4899', '#84cc16',
        '#f97316', '#6366f1'
    ];

    const chartData = (statistics || []).map(function(item, index) {
        return {
            name: item.entity_type || item.relation_type || item.name || '未知',
            value: item.count || 0
        };
    });

    const option = {
        backgroundColor: 'transparent',
        title: {
            text: chartTitle,
            left: 'center',
            top: 10,
            textStyle: { color: '#94a3b8', fontSize: 14, fontWeight: 600 }
        },
        tooltip: {
            trigger: 'item',
            backgroundColor: '#1e293b',
            borderColor: '#334155',
            textStyle: { color: '#f1f5f9' },
            formatter: '{b}: {c} ({d}%)'
        },
        legend: {
            orient: 'vertical',
            right: 10,
            top: 'center',
            textStyle: { color: '#94a3b8', fontSize: 12 }
        },
        series: [{
            type: 'pie',
            radius: ['40%', '70%'],
            center: ['40%', '55%'],
            avoidLabelOverlap: true,
            itemStyle: {
                borderRadius: 6,
                borderColor: '#0f172a',
                borderWidth: 2
            },
            label: { show: false },
            emphasis: {
                label: { show: true, fontSize: 14, fontWeight: 'bold' },
                itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' }
            },
            data: chartData,
            color: colorPalette
        }]
    };

    chart.setOption(option);

    window.addEventListener('resize', function() {
        chart.resize();
    });
}

// ============================================================
// 会话列表渲染
// ============================================================
function renderSessionsList(sessions) {
    const container = document.getElementById('sessions_list');
    if (!container) return;

    if (!sessions || sessions.length === 0) {
        container.innerHTML = '<p class="placeholder_text">暂无分析记录</p>';
        return;
    }

    container.innerHTML = sessions.map(function(session) {
        const statusClass = 'session-status-' + (session.analysis_status || 'pending');
        const statusText = {
            'completed': '完成',
            'running': '运行中',
            'failed': '失败',
            'pending': '等待中'
        }[session.analysis_status] || session.analysis_status;

        return '<div class="session_item">' +
            '<span class="session_name">' + escapeHtml(session.session_name) + '</span>' +
            '<span class="session-status ' + statusClass + '">' + statusText + '</span>' +
            '</div>';
    }).join('');
}

// ============================================================
// 用户操作
// ============================================================
async function triggerAnalysis() {
    const button = event.target;
    button.disabled = true;
    button.textContent = '分析中...';

    try {
        const response = await fetch('/api/trigger_analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ useLLM: true })
        });
        const result = await response.json();

        if (result.status === 'success') {
            showNotification('分析完成! 实体: ' + result.totalEntities + ', 关系: ' + result.totalRelations);
            loadDashboardData();
        } else {
            showNotification('分析失败: ' + (result.message || '未知错误'), 'error');
        }
    } catch (error) {
        showNotification('请求失败: ' + error.message, 'error');
    }

    button.disabled = false;
    button.textContent = '重新分析';
}

function refreshData() {
    loadDashboardData();
    showNotification('数据已刷新');
}

// ============================================================
// 自动刷新
// ============================================================
function startAutoRefresh() {
    if (autoRefreshTimer) clearInterval(autoRefreshTimer);
    autoRefreshTimer = setInterval(loadGraphSummary, 10000);
}

// ============================================================
// 工具函数
// ============================================================
function animateNumber(elementId, targetValue) {
    const element = document.getElementById(elementId);
    if (!element) return;

    const startValue = parseInt(element.textContent) || 0;
    const duration = 800;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const currentValue = Math.round(startValue + (targetValue - startValue) * eased);
        element.textContent = currentValue;

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showNotification(message, type) {
    type = type || 'success';
    const notification = document.createElement('div');
    notification.style.cssText = 'position:fixed;top:70px;right:24px;padding:12px 20px;border-radius:8px;font-size:13px;z-index:9999;transition:opacity 0.3s;max-width:400px;';
    notification.style.background = type === 'error' ? '#ef4444' : '#10b981';
    notification.style.color = '#fff';
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(function() {
        notification.style.opacity = '0';
        setTimeout(function() { notification.remove(); }, 300);
    }, 3000);
}
