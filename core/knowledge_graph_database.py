"""
Arkanalyzer Knowledge Graph System - Database Model
=====================================================
基于第一性原理：知识图谱的本质是「实体-关系-实体」的三元组存储。
使用SQLite实现轻量级、零配置的图数据持久化。
"""

import sqlite3
import json
import os
import threading
from datetime import datetime

from system_configuration import DATABASE_FILE_PATH, DATA_DIRECTORY, logger


class KnowledgeGraphDatabase:
    """知识图谱SQLite数据库管理器 - 线程安全版本"""

    def __init__(self, database_path=None):
        logger.info("[DB_INIT] 开始初始化数据库")
        self.database_path = database_path or DATABASE_FILE_PATH
        logger.debug(f"[DB_INIT] 数据库路径: {self.database_path}")
        
        os.makedirs(os.path.dirname(self.database_path), exist_ok=True)
        logger.debug("[DB_INIT] 数据目录已确认")
        
        self._lock = threading.RLock()
        self._connection = None
        logger.debug("[DB_INIT] 锁和连接初始化完成")
        
        self._initialize_database()
        logger.info("[DB_INIT] 数据库初始化完成")

    def _get_connection(self):
        """获取数据库连接（线程安全）"""
        logger.debug("[_get_connection] 请求数据库连接")
        if self._connection is None:
            logger.debug("[_get_connection] 创建新连接")
            self._connection = sqlite3.connect(
                self.database_path,
                check_same_thread=False,
                timeout=60.0
            )
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
            self._connection.execute("PRAGMA busy_timeout=60000")
            self._connection.execute("PRAGMA synchronous=NORMAL")
            logger.debug("[_get_connection] 新连接创建完成，WAL模式已启用")
        else:
            logger.debug("[_get_connection] 使用现有连接")
        return self._connection

    def _execute(self, query, parameters=None, fetch=False):
        """执行SQL查询（线程安全）"""
        logger.debug(f"[_execute] 执行SQL: {query[:50]}...")
        logger.debug(f"[_execute] 参数: {parameters}")
        logger.debug(f"[_execute] fetch模式: {fetch}")
        
        with self._lock:
            logger.debug("[_execute] 获取锁成功")
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                if parameters:
                    logger.debug(f"[_execute] 执行参数化查询")
                    cursor.execute(query, parameters)
                else:
                    logger.debug(f"[_execute] 执行无参数查询")
                    cursor.execute(query)

                if fetch:
                    logger.debug("[_execute] 获取结果集")
                    result = cursor.fetchall()
                    result_list = [dict(row) for row in result]
                    logger.debug(f"[_execute] 获取到 {len(result_list)} 条记录")
                    return result_list
                else:
                    logger.debug("[_execute] 获取lastrowid")
                    result = cursor.lastrowid
                    conn.commit()
                    logger.debug(f"[_execute] 提交成功，lastrowid={result}")
                    return result
            except sqlite3.OperationalError as e:
                logger.error(f"[_execute] SQL执行错误: {e}")
                if "database is locked" in str(e):
                    logger.warning("[_execute] 数据库被锁，等待重试")
                    import time
                    time.sleep(0.1)
                    return self._execute(query, parameters, fetch)
                raise
            except Exception as e:
                logger.error(f"[_execute] 未预期错误: {e}")
                raise

    def _initialize_database(self):
        """初始化数据库表结构"""
        logger.info("[_initialize_database] 开始初始化表结构")
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            logger.debug("[_initialize_database] 创建实体表")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS graph_entities (
                    entity_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_properties TEXT DEFAULT '{}',
                    source_file TEXT DEFAULT '',
                    source_line INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.debug("[_initialize_database] 实体表创建完成")

            logger.debug("[_initialize_database] 创建关系表")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS graph_relations (
                    relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_entity_id INTEGER NOT NULL,
                    target_entity_id INTEGER NOT NULL,
                    relation_type TEXT NOT NULL,
                    relation_properties TEXT DEFAULT '{}',
                    confidence_score REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_entity_id) REFERENCES graph_entities(entity_id) ON DELETE CASCADE,
                    FOREIGN KEY (target_entity_id) REFERENCES graph_entities(entity_id) ON DELETE CASCADE
                )
            """)
            logger.debug("[_initialize_database] 关系表创建完成")

            logger.debug("[_initialize_database] 创建分析会话表")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_sessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_name TEXT NOT NULL,
                    target_directory TEXT DEFAULT '',
                    analysis_status TEXT DEFAULT 'pending',
                    total_entities INTEGER DEFAULT 0,
                    total_relations INTEGER DEFAULT 0,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP DEFAULT NULL,
                    analysis_metadata TEXT DEFAULT '{}'
                )
            """)
            logger.debug("[_initialize_database] 分析会话表创建完成")

            logger.debug("[_initialize_database] 创建代码元素表")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS code_elements (
                    element_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    element_name TEXT NOT NULL,
                    element_kind TEXT NOT NULL,
                    parent_element TEXT DEFAULT '',
                    file_path TEXT NOT NULL,
                    start_line INTEGER DEFAULT 0,
                    end_line INTEGER DEFAULT 0,
                    element_signature TEXT DEFAULT '',
                    element_docstring TEXT DEFAULT '',
                    element_metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (session_id) REFERENCES analysis_sessions(session_id) ON DELETE CASCADE
                )
            """)
            logger.debug("[_initialize_database] 代码元素表创建完成")

            logger.debug("[_initialize_database] 创建索引")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_name ON graph_entities(entity_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_type ON graph_entities(entity_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relation_source ON graph_relations(source_entity_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relation_target ON graph_relations(target_entity_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relation_type ON graph_relations(relation_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_code_session ON code_elements(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_code_file ON code_elements(file_path)")
            logger.debug("[_initialize_database] 索引创建完成")

            conn.commit()
            logger.info("[_initialize_database] 所有表结构初始化完成")

    # ============================================================
    # 实体操作
    # ============================================================

    def insert_entity(self, name, entity_type, properties=None, source_file="", source_line=0):
        """插入新实体"""
        logger.info(f"[insert_entity] 插入实体: name={name}, type={entity_type}")
        props = json.dumps(properties or {}, ensure_ascii=False)
        query = """
            INSERT INTO graph_entities 
            (entity_name, entity_type, entity_properties, source_file, source_line) 
            VALUES (?, ?, ?, ?, ?)
        """
        entity_id = self._execute(query, (name, entity_type, props, source_file, source_line))
        logger.info(f"[insert_entity] 实体插入成功，ID={entity_id}")
        return entity_id

    def find_or_create_entity(self, name, entity_type, properties=None, source_file="", source_line=0):
        """查找或创建实体"""
        logger.info(f"[find_or_create_entity] 查找或创建: name={name}, type={entity_type}")
        query = "SELECT entity_id FROM graph_entities WHERE entity_name = ? AND entity_type = ?"
        result = self._execute(query, (name, entity_type), fetch=True)
        
        if result:
            entity_id = result[0]["entity_id"]
            logger.info(f"[find_or_create_entity] 找到现有实体，ID={entity_id}")
            return entity_id
        
        logger.info("[find_or_create_entity] 未找到，创建新实体")
        return self.insert_entity(name, entity_type, properties, source_file, source_line)

    def get_all_entities(self):
        """获取所有实体"""
        logger.info("[get_all_entities] 获取所有实体")
        result = self._execute("SELECT * FROM graph_entities ORDER BY entity_id", fetch=True)
        logger.info(f"[get_all_entities] 返回 {len(result)} 个实体")
        return result

    def get_entities_by_type(self, entity_type):
        """按类型获取实体"""
        logger.info(f"[get_entities_by_type] 按类型获取: type={entity_type}")
        result = self._execute(
            "SELECT * FROM graph_entities WHERE entity_type = ?", 
            (entity_type,), fetch=True
        )
        logger.info(f"[get_entities_by_type] 返回 {len(result)} 个实体")
        return result

    def get_entity_statistics(self):
        """获取实体类型统计"""
        logger.info("[get_entity_statistics] 获取实体统计")
        query = """
            SELECT entity_type, COUNT(*) as count 
            FROM graph_entities 
            GROUP BY entity_type 
            ORDER BY count DESC
        """
        result = self._execute(query, fetch=True)
        logger.info(f"[get_entity_statistics] 返回 {len(result)} 种类型统计")
        return result

    # ============================================================
    # 关系操作
    # ============================================================

    def insert_relation(self, source_id, target_id, relation_type, properties=None, confidence=1.0):
        """插入新关系"""
        logger.info(f"[insert_relation] 插入关系: source={source_id}, target={target_id}, type={relation_type}")
        props = json.dumps(properties or {}, ensure_ascii=False)
        query = """
            INSERT INTO graph_relations 
            (source_entity_id, target_entity_id, relation_type, relation_properties, confidence_score) 
            VALUES (?, ?, ?, ?, ?)
        """
        relation_id = self._execute(query, (source_id, target_id, relation_type, props, confidence))
        logger.info(f"[insert_relation] 关系插入成功，ID={relation_id}")
        return relation_id

    def get_all_relations(self):
        """获取所有关系"""
        logger.info("[get_all_relations] 获取所有关系")
        query = """
            SELECT r.*, se.entity_name as source_name, te.entity_name as target_name
            FROM graph_relations r
            JOIN graph_entities se ON r.source_entity_id = se.entity_id
            JOIN graph_entities te ON r.target_entity_id = te.entity_id
        """
        result = self._execute(query, fetch=True)
        logger.info(f"[get_all_relations] 返回 {len(result)} 个关系")
        return result

    def get_relations_by_type(self, relation_type):
        """按类型获取关系"""
        logger.info(f"[get_relations_by_type] 按类型获取: type={relation_type}")
        query = """
            SELECT r.*, se.entity_name as source_name, te.entity_name as target_name
            FROM graph_relations r
            JOIN graph_entities se ON r.source_entity_id = se.entity_id
            JOIN graph_entities te ON r.target_entity_id = te.entity_id
            WHERE r.relation_type = ?
        """
        result = self._execute(query, (relation_type,), fetch=True)
        logger.info(f"[get_relations_by_type] 返回 {len(result)} 个关系")
        return result

    def get_relation_statistics(self):
        """获取关系类型统计"""
        logger.info("[get_relation_statistics] 获取关系统计")
        query = """
            SELECT relation_type, COUNT(*) as count 
            FROM graph_relations 
            GROUP BY relation_type 
            ORDER BY count DESC
        """
        result = self._execute(query, fetch=True)
        logger.info(f"[get_relation_statistics] 返回 {len(result)} 种类型统计")
        return result

    # ============================================================
    # 图谱数据导出
    # ============================================================

    def export_graph_data(self):
        """导出完整的图谱数据"""
        logger.info("[export_graph_data] 开始导出图谱数据")
        entities = self.get_all_entities()
        relations = self.get_all_relations()

        logger.debug("[export_graph_data] 构建节点数据")
        nodes = []
        for entity in entities:
            nodes.append({
                "id": entity["entity_id"],
                "name": entity["entity_name"],
                "type": entity["entity_type"],
                "properties": json.loads(entity["entity_properties"]),
                "sourceFile": entity["source_file"],
                "sourceLine": entity["source_line"]
            })
        logger.debug(f"[export_graph_data] 构建了 {len(nodes)} 个节点")

        logger.debug("[export_graph_data] 构建边数据")
        edges = []
        for relation in relations:
            edges.append({
                "source": relation["source_entity_id"],
                "target": relation["target_entity_id"],
                "type": relation["relation_type"],
                "confidence": relation["confidence_score"],
                "sourceName": relation["source_name"],
                "targetName": relation["target_name"]
            })
        logger.debug(f"[export_graph_data] 构建了 {len(edges)} 条边")

        logger.info("[export_graph_data] 图谱数据导出完成")
        return {"nodes": nodes, "edges": edges}

    # ============================================================
    # 分析会话操作
    # ============================================================

    def create_analysis_session(self, session_name, target_directory=""):
        """创建新的分析会话"""
        logger.info(f"[create_analysis_session] 创建会话: name={session_name}, dir={target_directory}")
        query = """
            INSERT INTO analysis_sessions (session_name, target_directory) 
            VALUES (?, ?)
        """
        session_id = self._execute(query, (session_name, target_directory))
        logger.info(f"[create_analysis_session] 会话创建成功，ID={session_id}")
        return session_id

    def update_session_status(self, session_id, status, total_entities=0, total_relations=0):
        """更新分析会话状态"""
        logger.info(f"[update_session_status] 更新会话状态: id={session_id}, status={status}")
        completed_time = "CURRENT_TIMESTAMP" if status in ("completed", "failed") else "NULL"
        query = f"""
            UPDATE analysis_sessions SET
                analysis_status = ?,
                total_entities = ?,
                total_relations = ?,
                completed_at = {completed_time}
            WHERE session_id = ?
        """
        self._execute(query, (status, total_entities, total_relations, session_id))
        logger.info("[update_session_status] 会话状态更新完成")

    def get_recent_sessions(self, limit=10):
        """获取最近的分析会话"""
        logger.info(f"[get_recent_sessions] 获取最近 {limit} 个会话")
        result = self._execute(
            "SELECT * FROM analysis_sessions ORDER BY session_id DESC LIMIT ?",
            (limit,), fetch=True
        )
        logger.info(f"[get_recent_sessions] 返回 {len(result)} 个会话")
        return result

    # ============================================================
    # 代码元素操作
    # ============================================================

    def insert_code_element(self, session_id, name, kind, file_path, parent="", start_line=0, end_line=0, signature="", docstring="", metadata=None):
        """插入代码元素"""
        logger.info(f"[insert_code_element] 插入代码元素: session={session_id}, name={name}, kind={kind}")
        meta = json.dumps(metadata or {}, ensure_ascii=False)
        query = """
            INSERT INTO code_elements 
            (session_id, element_name, element_kind, parent_element, file_path, start_line, end_line, element_signature, element_docstring, element_metadata) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        element_id = self._execute(query, (session_id, name, kind, parent, file_path, start_line, end_line, signature, docstring, meta))
        logger.info(f"[insert_code_element] 代码元素插入成功，ID={element_id}")
        return element_id

    def get_code_elements_by_session(self, session_id):
        """获取指定会话的代码元素"""
        logger.info(f"[get_code_elements_by_session] 获取会话 {session_id} 的代码元素")
        result = self._execute(
            "SELECT * FROM code_elements WHERE session_id = ? ORDER BY file_path, start_line",
            (session_id,), fetch=True
        )
        logger.info(f"[get_code_elements_by_session] 返回 {len(result)} 个代码元素")
        return result

    # ============================================================
    # 数据清理
    # ============================================================

    def clear_all_graph_data(self):
        """清空所有图谱数据"""
        logger.warning("[clear_all_graph_data] 清空所有图谱数据！")
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM graph_relations")
            cursor.execute("DELETE FROM graph_entities")
            cursor.execute("DELETE FROM code_elements")
            cursor.execute("DELETE FROM analysis_sessions")
            conn.commit()
        logger.info("[clear_all_graph_data] 所有数据已清空")

    def get_graph_summary(self):
        """获取图谱摘要信息"""
        logger.info("[get_graph_summary] 获取图谱摘要")
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as count FROM graph_entities")
            entity_count = cursor.fetchone()["count"]
            logger.debug(f"[get_graph_summary] 实体数量: {entity_count}")
            
            cursor.execute("SELECT COUNT(*) as count FROM graph_relations")
            relation_count = cursor.fetchone()["count"]
            logger.debug(f"[get_graph_summary] 关系数量: {relation_count}")
            
            cursor.execute("SELECT COUNT(*) as count FROM analysis_sessions")
            session_count = cursor.fetchone()["count"]
            logger.debug(f"[get_graph_summary] 会话数量: {session_count}")
            
            cursor.execute("SELECT COUNT(DISTINCT source_file) as count FROM graph_entities WHERE source_file != ''")
            file_count = cursor.fetchone()["count"]
            logger.debug(f"[get_graph_summary] 文件数量: {file_count}")
            
            summary = {
                "totalEntities": entity_count,
                "totalRelations": relation_count,
                "totalSessions": session_count,
                "totalFiles": file_count
            }
            logger.info(f"[get_graph_summary] 摘要: {summary}")
            return summary

    def close(self):
        """关闭数据库连接"""
        logger.info("[close] 关闭数据库连接")
        with self._lock:
            if self._connection:
                self._connection.close()
                self._connection = None
                logger.info("[close] 连接已关闭")
