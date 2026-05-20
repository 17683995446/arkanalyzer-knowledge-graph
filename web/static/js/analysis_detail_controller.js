/**
 * Arkanalyzer Knowledge Graph System - Analysis Detail Controller
 * =================================================================
 * 分析详情页面的JavaScript控制器。
 */

// ============================================================
// 全局状态
// ============================================================
let detailChart = null;
let allElements = [];
let allSessions = [];

// ============================================================
// 页面初始化
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
    loadSessions();
});

// ============================================================
// 会话加载
// ============================================================
async function loadSessions() {
    try {
        const response = await fetch('/api/recent_sessions');
        allSessions = await response.json();
        populateSessionSelector();
    } catch (error) {
        console.error('加载会话列表失败:', error);
    }
}

function populateSessionSelector() {
    const selector = document.getElementById('session_selector');
    if (!selector) return;

    selector.innerHTML = '<option value="">-- 请选择会话 --</option>';
    allSessions.forEach(function(session) {
        const option = document.createElement('option');
        option.value = session.session_id;
        option.textContent = session.session_name + ' (' + (session.analysis_status || 'pending') + ')';
        selector.appendChild(option);
    });
}

function refreshSessions() {
    loadSessions();
}

// ============================================================
// 会话详情加载
// ============================================================
async function loadSessionDetail() {
    const sessionId = document.getElementById('session_selector').value;
    if (!sessionId) return;

    // 更新会话统计
    const session = allSessions.find(function(s) { return s.session_id == sessionId; });
    if (session) {
        document.getElementById('session_stats').style.display = 'grid';
        document.getElementById('stat_session_name').textContent = session.session_name || '--';
        document.getElementById('stat_target_dir').textContent = session.target_directory || '--';
        document.getElementById('stat_status').textContent = session.analysis_status || '--';
        document.getElementById('stat_entities').textContent = session.total_entities || 0;
        document.getElementById('stat_relations').textContent = session.total_relations || 0;
        document.getElementById('stat_started').textContent = session.started_at || '--';
        document.getElementById('stat_completed').textContent = session.completed_at || '--';
    }

    // 加载代码元素
    try {
        const response = await fetch('/api/analysis_sessions?session_id=' + sessionId);
        allElements = await response.json();
        renderElementsTable(allElements);
        renderRelationNetwork(allElements);
    } catch (error) {
        console.error('加载代码元素失败:', error);
    }
}

// ============================================================
// 元素表格渲染
// ============================================================
function renderElementsTable(elements) {
    const tbody = document.getElementById('elements_tbody');
    if (!tbody) return;

    if (!elements || elements.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="placeholder_text">此会话没有代码元素</td></tr>';
        return;
    }

    tbody.innerHTML = elements.map(function(elem) {
        return '<tr>' +
            '<td title="' + escapeHtml(elem.element_name) + '">' + escapeHtml(elem.element_name) + '</td>' +
            '<td><span style="color:' + getTypeColor(elem.element_kind) + '">' + escapeHtml(elem.element_kind) + '</span></td>' +
            '<td title="' + escapeHtml(elem.file_path) + '">' + escapeHtml(elem.file_path) + '</td>' +
            '<td>' + (elem.start_line || '--') + '</td>' +
            '<td>' + escapeHtml(elem.parent_element || '--') + '</td>' +
            '<td title="' + escapeHtml(elem.element_docstring || '') + '">' + escapeHtml(truncate(elem.element_docstring, 60)) + '</td>' +
            '</tr>';
    }).join('');
}

function filterElements() {
    const searchText = document.getElementById('search_input').value.toLowerCase();
    const kindFilter = document.getElementById('kind_filter').value;

    let filtered = allElements;

    if (searchText) {
        filtered = filtered.filter(function(elem) {
            return elem.element_name.toLowerCase().indexOf(searchText) !== -1;
        });
    }

    if (kindFilter !== 'all') {
        filtered = filtered.filter(function(elem) {
            return elem.element_kind === kindFilter;
        });
    }

    renderElementsTable(filtered);
}

// ============================================================
// 关系网络渲染
// ============================================================
function renderRelationNetwork(elements) {
    const container = document.getElementById('detail_relation_chart');
    if (!container) return;

    if (detailChart) detailChart.dispose();
    detailChart = echarts.init(container, 'dark');

    // 构建节点和边
    const nodeMap = {};
    const links = [];

    elements.forEach(function(elem) {
        if (!nodeMap[elem.element_name]) {
            nodeMap[elem.element_name] = {
                name: elem.element_name,
                kind: elem.element_kind,
                file: elem.file_path
            };
        }

        if (elem.parent_element) {
            links.push({
                source: elem.parent_element,
                target: elem.element_name,
                type: 'contains'
            });
        }
    });

    const nodes = Object.values(nodeMap).map(function(node) {
        return {
            name: node.name,
            symbolSize: node.kind === 'Class' ? 35 : 20,
            itemStyle: { color: getTypeColor(node.kind) },
            label: { show: true, fontSize: 10, color: '#f1f5f9' }
        };
    });

    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            backgroundColor: '#1e293b',
            borderColor: '#334155',
            textStyle: { color: '#f1f5f9' }
        },
        series: [{
            type: 'graph',
            layout: 'force',
            data: nodes,
            links: links.map(function(link) {
                return {
                    source: link.source,
                    target: link.target,
                    lineStyle: { color: 'rgba(148,163,184,0.3)', width: 1 }
                };
            }),
            roam: true,
            force: { repulsion: 200, edgeLength: [50, 150] },
            emphasis: { focus: 'adjacency' }
        }]
    };

    detailChart.setOption(option);

    window.addEventListener('resize', function() {
        if (detailChart) detailChart.resize();
    });
}

// ============================================================
// 工具函数
// ============================================================
function getTypeColor(kind) {
    var colors = {
        'Class': '#3b82f6',
        'Function': '#10b981',
        'Method': '#8b5cf6',
        'Module': '#06b6d4',
        'Variable': '#f59e0b',
        'Interface': '#ec4899'
    };
    return colors[kind] || '#64748b';
}

function truncate(text, maxLen) {
    if (!text) return '--';
    return text.length > maxLen ? text.substring(0, maxLen) + '...' : text;
}

function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}
