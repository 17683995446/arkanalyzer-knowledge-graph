"""
Arkanalyzer Knowledge Graph System - Web Visualization Server
================================================================
基于第一性原理：可视化的本质是「数据到图形的映射」，
Web服务将知识图谱数据转化为交互式图表展示。
"""

import json
import os
import sys
import logging
from datetime import datetime

from flask import Flask, render_template, jsonify, request

# 添加核心模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "core"))

from system_configuration import (
    WEB_SERVER_HOST,
    WEB_SERVER_PORT,
    WEB_DEBUG_MODE,
    TEMPLATE_DIRECTORY,
    STATIC_DIRECTORY,
    PROJECT_ROOT,
)

from knowledge_graph_database import KnowledgeGraphDatabase
from knowledge_graph_builder import KnowledgeGraphBuilder
from file_change_watcher import FileChangeWatcher

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ============================================================
# Flask 应用初始化
# ============================================================
application = Flask(
    __name__,
    template_folder=TEMPLATE_DIRECTORY,
    static_folder=STATIC_DIRECTORY
)
application.config["JSON_AS_ASCII"] = False

# ============================================================
# 全局组件
# ============================================================
graph_database = KnowledgeGraphDatabase()
graph_builder = KnowledgeGraphBuilder(database=graph_database)
file_watcher = None
last_update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
# 路由：页面渲染
# ============================================================

@application.route("/")
def render_dashboard():
    """渲染主仪表盘页面"""
    return render_template("dashboard.html")


@application.route("/knowledge_graph")
def render_knowledge_graph():
    """渲染知识图谱可视化页面"""
    return render_template("knowledge_graph.html")


@application.route("/architecture_diagram")
def render_architecture():
    """渲染系统架构图页面"""
    return render_template("architecture_diagram.html")


@application.route("/flow_diagram")
def render_flow_diagram():
    """渲染流程图页面"""
    return render_template("flow_diagram.html")


@application.route("/sequence_diagram")
def render_sequence_diagram():
    """渲染时序图页面"""
    return render_template("sequence_diagram.html")


@application.route("/analysis_detail")
def render_analysis_detail():
    """渲染分析详情页面"""
    return render_template("analysis_detail.html")


# ============================================================
# 路由：API 数据接口
# ============================================================

@application.route("/api/graph_summary")
def api_graph_summary():
    """获取图谱摘要"""
    summary = graph_database.get_graph_summary()
    summary["lastUpdate"] = last_update_time
    return jsonify(summary)


@application.route("/api/graph_data")
def api_graph_data():
    """获取完整图谱数据"""
    data = graph_builder.get_visualization_data()
    return jsonify(data)


@application.route("/api/entity_statistics")
def api_entity_statistics():
    """获取实体统计"""
    stats = graph_database.get_entity_statistics()
    return jsonify(stats)


@application.route("/api/relation_statistics")
def api_relation_statistics():
    """获取关系统计"""
    stats = graph_database.get_relation_statistics()
    return jsonify(stats)


@application.route("/api/recent_sessions")
def api_recent_sessions():
    """获取最近分析会话"""
    sessions = graph_database.get_recent_sessions(20)
    return jsonify(sessions)


@application.route("/api/analysis_sessions")
def api_analysis_sessions():
    """获取分析会话列表"""
    session_id = request.args.get("session_id", type=int)
    if session_id:
        elements = graph_database.get_code_elements_by_session(session_id)
        return jsonify(elements)
    sessions = graph_database.get_recent_sessions(20)
    return jsonify(sessions)


@application.route("/api/trigger_analysis", methods=["POST"])
def api_trigger_analysis():
    """触发代码分析"""
    data = request.get_json() or {}
    target_path = data.get("targetPath", PROJECT_ROOT)
    session_name = data.get("sessionName", "")
    use_llm = data.get("useLLM", True)

    if not os.path.isdir(target_path):
        return jsonify({"status": "error", "message": "目标路径不存在"})

    result = graph_builder.analyze_and_build(target_path, session_name, use_llm)
    global last_update_time
    last_update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return jsonify(result)


@application.route("/api/watcher_status")
def api_watcher_status():
    """获取文件监听状态"""
    if file_watcher:
        return jsonify(file_watcher.get_status())
    return jsonify({"running": False})


@application.route("/api/system_info")
def api_system_info():
    """获取系统信息"""
    return jsonify({
        "systemName": "Arkanalyzer Knowledge Graph System",
        "version": "1.0.0",
        "technology": "ArkAnalyzer → SQLite",
        "llmProvider": "SiliconFlow (Qwen/Qwen2.5-7B-Instruct)",
        "projectRoot": PROJECT_ROOT,
        "lastUpdate": last_update_time
    })


# ============================================================
# 文件变化回调
# ============================================================

def on_file_changed(changed_files, deleted_files, change_count):
    """文件变化回调函数"""
    global last_update_time
    logger.info(f"文件变化回调触发，变更文件数: {len(changed_files)}")

    for file_path in changed_files[:3]:  # 限制每次最多处理3个文件
        try:
            graph_builder.analyze_single_file(file_path, use_llm=False)
        except Exception as exception:
            logger.error(f"分析文件失败 {file_path}: {exception}")

    last_update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
# 启动入口
# ============================================================

def start_web_server(watch_path=None):
    """启动Web服务器"""
    global file_watcher

    # 启动文件监听
    watch_target = watch_path or PROJECT_ROOT
    if os.path.isdir(watch_target):
        file_watcher = FileChangeWatcher(watch_target, callback=on_file_changed)
        file_watcher.start_watching()
        logger.info(f"文件监听已启动: {watch_target}")

    # 初始分析
    logger.info("执行初始代码分析...")
    try:
        graph_builder.analyze_and_build(PROJECT_ROOT, "initial_analysis", use_llm=True)
        global last_update_time
        last_update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info("初始分析完成")
    except Exception as exception:
        logger.error(f"初始分析失败: {exception}")

    # 启动Flask
    logger.info(f"Web服务器启动: http://{WEB_SERVER_HOST}:{WEB_SERVER_PORT}")
    application.run(
        host=WEB_SERVER_HOST,
        port=WEB_SERVER_PORT,
        debug=WEB_DEBUG_MODE,
        use_reloader=False
    )


if __name__ == "__main__":
    start_web_server()
