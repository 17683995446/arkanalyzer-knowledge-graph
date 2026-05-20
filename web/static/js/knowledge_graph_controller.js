/**
 * Arkanalyzer Knowledge Graph System - Knowledge Graph Controller
 * ================================================================
 * 知识图谱可视化控制器，使用ECharts力导向图展示实体关系。
 */

// ============================================================
// 全局状态
// ============================================================
let graphChart = null;
let graphData = { nodes: [], edges: [] };
let currentLayout = 'force';
let filteredNodeType = 'all';
let filteredRelationType = 'all';
let showLabels = true;

// 节点类型颜色映射
const TYPE_COLORS = {
    'Class': '#3b82f6',
    'Function': '#10b981',
    'Method': '#8b5cf6',
    'Variable': '#f59e0b',
    'Module': '#06b6d4',
    'Interface': '#ec4899',
    'Enum': '#f97316',
    'Unknown': '#64748b'
};

// 节点类型大小映射
const TYPE_SIZES = {
    'Class': 40,
    'Function': 30,
    'Method': 25,
    'Variable': 15,
    'Module': 35,
    'Interface': 35,
    'Enum': 25,
    'Unknown': 20
};

// ============================================================
// 页面初始化
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
    initGraphChart();
    loadGraphData();
});

// ============================================================
// 图表初始化
// ============================================================
function initGraphChart() {
    const container = document.getElementById('knowledge_graph_chart');
    if (!container) return;

    graphChart = echarts.init(container, 'dark');

    graphChart.on('click', function(params) {
        if (params.dataType === 'node') {
            showNodeDetail(params.data);
        }
    });

    window.addEventListener('resize', function() {
        if (graphChart) graphChart.resize();
    });
}

// ============================================================
// 数据加载
// ============================================================
async function loadGraphData() {
    try {
        const response = await fetch('/api/graph_data');
        const data = await response.json();

        graphData = data.graphData || { nodes: [], edges: [] };
        populateFilters();
        renderGraph();
    } catch (error) {
        console.error('加载图谱数据失败:', error);
    }
}

// ============================================================
// 过滤器填充
// ============================================================
function populateFilters() {
    const typeFilter = document.getElementById('type_filter');
    const relationFilter = document.getElementById('relation_filter');
    const legendContainer = document.getElementById('legend_items');

    if (!typeFilter || !relationFilter) return;

    // 收集所有类型
    const entityTypes = new Set();
    const relationTypes = new Set();

    graphData.nodes.forEach(function(node) { entityTypes.add(node.type); });
    graphData.edges.forEach(function(edge) { relationTypes.add(edge.type); });

    // 填充实体类型过滤器
    typeFilter.innerHTML = '<option value="all">全部类型</option>';
    entityTypes.forEach(function(type) {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = type;
        typeFilter.appendChild(option);
    });

    // 填充关系类型过滤器
    relationFilter.innerHTML = '<option value="all">全部关系</option>';
    relationTypes.forEach(function(type) {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = type;
        relationFilter.appendChild(option);
    });

    // 渲染图例
    if (legendContainer) {
        legendContainer.innerHTML = '';
        entityTypes.forEach(function(type) {
            const color = TYPE_COLORS[type] || '#64748b';
            const count = graphData.nodes.filter(function(n) { return n.type === type; }).length;
            legendContainer.innerHTML += '<div class="legend_item">' +
                '<span class="legend_color" style="background:' + color + '"></span>' +
                '<span>' + type + ' (' + count + ')</span>' +
                '</div>';
        });
    }
}

// ============================================================
// 图谱渲染
// ============================================================
function renderGraph() {
    if (!graphChart) return;

    let filteredNodes = graphData.nodes;
    let filteredEdges = graphData.edges;

    // 按节点类型过滤
    if (filteredNodeType !== 'all') {
        const nodeIds = new Set();
        filteredNodes = filteredNodes.filter(function(n) {
            if (n.type === filteredNodeType) { nodeIds.add(n.id); return true; }
            return false;
        });
        filteredEdges = filteredEdges.filter(function(e) {
            return nodeIds.has(e.source) && nodeIds.has(e.target);
        });
    }

    // 按关系类型过滤
    if (filteredRelationType !== 'all') {
        filteredEdges = filteredEdges.filter(function(e) { return e.type === filteredRelationType; });
        const edgeNodeIds = new Set();
        filteredEdges.forEach(function(e) { edgeNodeIds.add(e.source); edgeNodeIds.add(e.target); });
        filteredNodes = filteredNodes.filter(function(n) { return edgeNodeIds.has(n.id); });
    }

    // 构建ECharts数据
    const nodes = filteredNodes.map(function(node) {
        return {
            id: node.id,
            name: node.name,
            symbolSize: TYPE_SIZES[node.type] || 20,
            itemStyle: { color: TYPE_COLORS[node.type] || '#64748b' },
            category: node.type,
            label: {
                show: showLabels,
                fontSize: 11,
                color: '#f1f5f9'
            },
            value: node,
            draggable: true
        };
    });

    const edges = filteredEdges.map(function(edge) {
        return {
            source: edge.source,
            target: edge.target,
            lineStyle: {
                color: 'rgba(148, 163, 184, 0.3)',
                width: 1.5,
                curveness: 0.15
            },
            label: {
                show: showLabels && filteredNodes.length < 50,
                formatter: edge.type,
                fontSize: 9,
                color: '#64748b'
            },
            value: edge
        };
    });

    // 布局配置
    let layoutOption = {};
    if (currentLayout === 'force') {
        layoutOption = {
            layout: 'force',
            force: {
                repulsion: 300,
                edgeLength: [80, 200],
                gravity: 0.1,
                friction: 0.6
            }
        };
    } else if (currentLayout === 'circular') {
        layoutOption = {
            layout: 'circular',
            circular: { rotateLabel: true }
        };
    } else if (currentLayout === 'radial') {
        layoutOption = {
            layout: 'force',
            force: {
                repulsion: 200,
                edgeLength: [60, 150],
                gravity: 0.2,
                friction: 0.6
            }
        };
    }

    const option = Object.assign({
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'item',
            backgroundColor: '#1e293b',
            borderColor: '#334155',
            textStyle: { color: '#f1f5f9', fontSize: 12 },
            formatter: function(params) {
                if (params.dataType === 'node') {
                    return '<strong>' + params.data.name + '</strong><br/>' +
                        '类型: ' + params.data.category + '<br/>' +
                        '文件: ' + (params.data.value.sourceFile || '--');
                } else if (params.dataType === 'edge') {
                    return params.data.value.sourceName + ' → ' + params.data.value.targetName +
                        '<br/>关系: ' + params.data.value.type;
                }
                return '';
            }
        },
        animationDuration: 1000,
        animationEasingUpdate: 'quinticInOut',
        series: [{
            type: 'graph',
            data: nodes,
            links: edges,
            roam: true,
            draggable: true,
            emphasis: {
                focus: 'adjacency',
                lineStyle: { width: 3 }
            },
            categories: Object.keys(TYPE_COLORS).map(function(type) {
                return { name: type };
            })
        }]
    }, layoutOption);

    graphChart.setOption(option, true);
}

// ============================================================
// 用户交互
// ============================================================
function changeLayout() {
    currentLayout = document.getElementById('layout_selector').value;
    renderGraph();
}

function filterByType() {
    filteredNodeType = document.getElementById('type_filter').value;
    renderGraph();
}

function filterByRelation() {
    filteredRelationType = document.getElementById('relation_filter').value;
    renderGraph();
}

function toggleLabels() {
    showLabels = document.getElementById('show_labels').checked;
    renderGraph();
}

function refreshGraph() {
    loadGraphData();
}

function showNodeDetail(nodeData) {
    const infoContainer = document.getElementById('node_info');
    if (!infoContainer || !nodeData) return;

    const value = nodeData.value || {};
    const properties = value.properties || {};

    infoContainer.innerHTML =
        '<div class="info_name">' + escapeHtml(value.name || nodeData.name) + '</div>' +
        '<span class="info_type">' + escapeHtml(value.type || nodeData.category) + '</span>' +
        '<p>文件: ' + escapeHtml(value.sourceFile || '--') + '</p>' +
        '<p>行号: ' + (value.sourceLine || '--') + '</p>' +
        (properties.docstring ? '<p style="margin-top:8px;font-style:italic;color:#94a3b8">' + escapeHtml(properties.docstring).substring(0, 200) + '</p>' : '');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}
