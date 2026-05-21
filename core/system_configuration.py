"""
Arkanalyzer Knowledge Graph System - Configuration Module
==========================================================
系统全局配置，遵循第一性原理：所有配置集中管理，单一数据源。
"""

import os
import logging

# ============================================================
# 日志配置 - 详细追踪模式
# ============================================================
LOG_LEVEL = "DEBUG"  # 改为DEBUG级别以获取详细日志
LOG_FORMAT = "%(asctime)s - [%(name)s] - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"

def setup_logging():
    """设置详细日志"""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(os.path.dirname(__file__), "..", "logs", "system.log"), mode='a')
        ]
    )
    return logging.getLogger("Arkanalyzer")

# ============================================================
# 基础路径配置
# ============================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIRECTORY = os.path.join(PROJECT_ROOT, "data")
LOG_DIRECTORY = os.path.join(PROJECT_ROOT, "logs")
TEMPLATE_DIRECTORY = os.path.join(PROJECT_ROOT, "web", "templates")
STATIC_DIRECTORY = os.path.join(PROJECT_ROOT, "web", "static")

# 确保日志目录存在
os.makedirs(LOG_DIRECTORY, exist_ok=True)

# ============================================================
# SQLite 数据库配置
# ============================================================
DATABASE_FILE_PATH = os.path.join(DATA_DIRECTORY, "knowledge_graph.db")

# ============================================================
# 硅基流动 LLM API 配置
# ============================================================
SILICONFLOW_API_ENDPOINT = "https://api.siliconflow.cn/v1/chat/completions"
SILICONFLOW_API_KEY = "sk-uqelhavcdhfxjzjesdenxpbtqombamjniazzjtbssmdcwdvg"
SILICONFLOW_DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"
SILICONFLOW_MAX_TOKENS = 4096
SILICONFLOW_TEMPERATURE = 0.3

# ============================================================
# Web 服务配置
# ============================================================
WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = 5000
WEB_DEBUG_MODE = True

# ============================================================
# 文件监听配置
# ============================================================
FILE_WATCH_INTERVAL_SECONDS = 2
SUPPORTED_SOURCE_EXTENSIONS = {".py", ".js", ".ts", ".java", ".ets", ".arkts"}

# ============================================================
# 知识图谱配置
# ============================================================
GRAPH_MAX_NODES_DISPLAY = 200
GRAPH_MAX_EDGES_DISPLAY = 500
GRAPH_LAYOUT_ALGORITHM = "force"

# 初始化全局logger
logger = setup_logging()
logger.info("[CONFIG] 系统配置加载完成")
