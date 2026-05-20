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

from system_configuration import DATABASE_FILE_PATH, DATA_DIRECTORY


class KnowledgeGraphDatabase:
    """知识图谱SQLite数据库管理器 - 线程安全版本"""

    def __init__(self, database_path=None):
        self.database_path = database_path or DATABASE_FILE_PATH
        os.makedirs(os.path.dirname(self.database_path), exist_ok=True)
        self._lock = threading.RLock()  # 可重入锁
        self._connection = None
        self._initialize_database()

    def _get_connection(self):
        """获取数据库连接（线程安全）"""
        if self._connection is None:
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
        return self._connection

    def _execute(self, query, parameters=None, fetch=False):
        """执行SQL查询（线程安全）"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                if parameters:
                    cursor.execute(query, parameters)
                else:
                    cursor.execute(query)
                
                if fetch:
                    result = cursor.fetchall()
                    return [dict(row) for row in result]
                else:
                    result = cursor.lastrowid
                    conn.commit()  # 立即提交
                    return result
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e):
                    # 重试一次
                    import time
                    time.sleep(0.1)
                    return self._execute(query, parameters, fetch)
                raise

    def _executemany(self, query, parameters_list):
        """批量执行SQL"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.executemany(query, parameters_list)
            conn.commit()

    def _initialize_database(self):
        """初始化数据库表结构"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 实体表
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

            # 关系表
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

            # 分析会话表
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

            # 代码元素表
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

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_name ON graph_entities(entity_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_type ON graph_entities(entity_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relation_source ON graph_relations(source_entity_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relation_target ON graph_relations(target_entity_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relation_type ON graph_relations(relation_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_code_session ON code_elements(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_code_file ON code_elements(file_path)")
            
            conn.commit()

    # ============================================================
    # 实体操作
    # ============================================================

    def insert_entity(self, name, entity_type, properties=None, source_file="", source_line=0):
        """插入新实体"""
        props = json.dumps(properties or {}, ensure_ascii=False)
        query = """
            INSERT INTO graph_entities 
            (entity_name, entity_type, entity_properties, source_file, source_line) 
            VALUES (?, ?, ?, ?, ?)
        """
        return self._execute(query, (name, entity_type, props, source_file, source_line))

    def find_or_create_entity(self, name, entity_type, properties=None, source_file="", source_line=0):
        """查找或创建实体"""
        query = "SELECT entity_id FROM graph_entities WHERE entity_name = ? AND entity_type = ?"
        result = self._execute(query, (name, entity_type), fetch=True)
        
        if result:
            return result[0]["entity_id"]
        
        return self.insert_entity(name, entity_type, properties, source_file, source_line)

    def get_all_entities(self):
        """获取所有实体"""
        return self._execute("SELECT * FROM graph_entities ORDER BY entity_id", fetch=True)

    def get_entities_by_type(self, entity_type):
        """按类型获取实体"""
        return self._execute(
            "SELECT * FROM graph_entities WHERE entity_type = ?", 
            (entity_type,), fetch=True
        )

    def get_entity_statistics(self):
        """获取实体类型统计"""
        query = """
            SELECT entity_type, COUNT(*) as count 
            FROM graph_entities 
            GROUP BY entity_type 
            ORDER BY count DESC
        """
        return self._execute(query, fetch=True)

    # ============================================================
    # 关系操作
    # ============================================================

    def insert_relation(self, source_id, target_id, relation_type, properties=None, confidence=1.0):
        """插入新关系"""
        props = json.dumps(properties or {}, ensure_ascii=False)
        query = """
            INSERT INTO graph_relations 
            (source_entity_id, target_entity_id, relation_type, relation_properties, confidence_score) 
            VALUES (?, ?, ?, ?, ?)
        """
        return self._execute(query, (source_id, target_id, relation_type, props, confidence))

    def get_all_relations(self):
        """获取所有关系"""
        query = """
            SELECT r.*, se.entity_name as source_name, te.entity_name as target_name
            FROM graph_relations r
            JOIN graph_entities se ON r.source_entity_id = se.entity_id
            JOIN graph_entities te ON r.target_entity_id = te.entity_id
        """
        return self._execute(query, fetch=True)

    def get_relations_by_type(self, relation_type):
        """按类型获取关系"""
        query = """
            SELECT r.*, se.entity_name as source_name, te.entity_name as target_name
            FROM graph_relations r
            JOIN graph_entities se ON r.source_entity_id = se.entity_id
            JOIN graph_entities te ON r.target_entity_id = te.entity_id
            WHERE r.relation_type = ?
        """
        return self._execute(query, (relation_type,), fetch=True)

    def get_relation_statistics(self):
        """获取关系类型统计"""
        query = """
            SELECT relation_type, COUNT(*) as count 
            FROM graph_relations 
            GROUP BY relation_type 
            ORDER BY count DESC
        """
        return self._execute(query, fetch=True)

    # ============================================================
    # 图谱数据导出
    # ============================================================

    def export_graph_data(self):
        """导出完整的图谱数据"""
        entities = self.get_all_entities()
        relations = self.get_all_relations()

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

        return {"nodes": nodes, "edges": edges}

    # ============================================================
    # 分析会话操作
    # ============================================================

    def create_analysis_session(self, session_name, target_directory=""):
        """创建新的分析会话"""
        query = """
            INSERT INTO analysis_sessions (session_name, target_directory) 
            VALUES (?, ?)
        """
        return self._execute(query, (session_name, target_directory))

    def update_session_status(self, session_id, status, total_entities=0, total_relations=0):
        """更新分析会话状态"""
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

    def get_recent_sessions(self, limit=10):
        """获取最近的分析会话"""
        return self._execute(
            "SELECT * FROM analysis_sessions ORDER BY session_id DESC LIMIT ?",
            (limit,), fetch=True
        )

    # ============================================================
    # 代码元素操作
    # ============================================================

    def insert_code_element(self, session_id, name, kind, file_path, parent="", start_line=0, end_line=0, signature="", docstring="", metadata=None):
        """插入代码元素"""
        meta = json.dumps(metadata or {}, ensure_ascii=False)
        query = """
            INSERT INTO code_elements 
            (session_id, element_name, element_kind, parent_element, file_path, start_line, end_line, element_signature, element_docstring, element_metadata) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        return self._execute(query, (session_id, name, kind, parent, file_path, start_line, end_line, signature, docstring, meta))

    def get_code_elements_by_session(self, session_id):
        """获取指定会话的代码元素"""
        return self._execute(
            "SELECT * FROM code_elements WHERE session_id = ? ORDER BY file_path, start_line",
            (session_id,), fetch=True
        )

    # ============================================================
    # 数据清理
    # ============================================================

    def clear_all_graph_data(self):
        """清空所有图谱数据"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM graph_relations")
            cursor.execute("DELETE FROM graph_entities")
            cursor.execute("DELETE FROM code_elements")
            cursor.execute("DELETE FROM analysis_sessions")
            conn.commit()

    def get_graph_summary(self):
        """获取图谱摘要信息"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as count FROM graph_entities")
            entity_count = cursor.fetchone()["count"]
            
            cursor.execute("SELECT COUNT(*) as count FROM graph_relations")
            relation_count = cursor.fetchone()["count"]
            
            cursor.execute("SELECT COUNT(*) as count FROM analysis_sessions")
            session_count = cursor.fetchone()["count"]
            
            cursor.execute("SELECT COUNT(DISTINCT source_file) as count FROM graph_entities WHERE source_file != ''")
            file_count = cursor.fetchone()["count"]
            
            return {
                "totalEntities": entity_count,
                "totalRelations": relation_count,
                "totalSessions": session_count,
                "totalFiles": file_count
            }

    def close(self):
        """关闭数据库连接"""
        with self._lock:
            if self._connection:
                self._connection.close()
                self._connection = None
