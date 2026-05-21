"""
Arkanalyzer Knowledge Graph System - Knowledge Graph Builder
=============================================================
基于第一性原理：知识图谱构建的本质是「从代码到实体-关系的映射」。
整合代码分析引擎和LLM，构建完整的知识图谱。
"""

import os
import json
from datetime import datetime

from system_configuration import logger
from knowledge_graph_database import KnowledgeGraphDatabase
from code_analysis_engine import ProjectCodeScanner
from siliconflow_language_model import SiliconFlowLanguageModel


class KnowledgeGraphBuilder:
    """知识图谱构建器"""

    def __init__(self, database=None):
        logger.info("[KnowledgeGraphBuilder] 初始化知识图谱构建器")
        self.database = database or KnowledgeGraphDatabase()
        self.scanner = ProjectCodeScanner()
        self.llm_client = SiliconFlowLanguageModel()
        logger.debug("[KnowledgeGraphBuilder] 初始化完成")

    def analyze_and_build(self, target_path, session_name="", use_llm=True):
        """分析目标路径并构建知识图谱"""
        logger.info(f"[analyze_and_build] 开始分析: path={target_path}, session={session_name}, use_llm={use_llm}")
        
        if not os.path.exists(target_path):
            logger.error(f"[analyze_and_build] 路径不存在: {target_path}")
            return {"status": "error", "message": "路径不存在"}

        session_id = self.database.create_analysis_session(
            session_name or f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            target_path
        )
        logger.info(f"[analyze_and_build] 创建会话，ID={session_id}")

        try:
            logger.info(f"[analyze_and_build] 扫描目录: {target_path}")
            analysis_results, scanned_files = self.scanner.scan_directory(target_path)
            logger.info(f"[analyze_and_build] 扫描完成: {len(scanned_files)}个文件")

            if not analysis_results:
                logger.warning("[analyze_and_build] 未找到可分析的文件")
                self.database.update_session_status(session_id, "completed", 0, 0)
                return {"status": "success", "sessionId": session_id, "totalEntities": 0, "totalRelations": 0}

            logger.info("[analyze_and_build] 提取实体和关系")
            entities = self.scanner.extract_all_entities(analysis_results)
            relations = self.scanner.extract_all_relations(analysis_results)
            logger.info(f"[analyze_and_build] 提取: {len(entities)}实体, {len(relations)}关系")

            logger.info("[analyze_and_build] 存储代码元素")
            for result in analysis_results:
                self._store_code_elements(session_id, result)

            logger.info("[analyze_and_build] 存储实体到数据库")
            entity_id_map = {}
            for entity in entities:
                entity_id = self.database.find_or_create_entity(
                    entity["name"],
                    entity["type"],
                    {"docstring": entity.get("docstring", "")},
                    entity.get("file", ""),
                    entity.get("line", 0)
                )
                entity_id_map[(entity["name"], entity["type"])] = entity_id
                logger.debug(f"[analyze_and_build] 实体 {entity['name']} -> ID {entity_id}")

            logger.info("[analyze_and_build] 存储关系到数据库")
            relation_count = 0
            for relation in relations:
                source_id = entity_id_map.get((relation["source"], "Class")) or \
                           entity_id_map.get((relation["source"], "Function")) or \
                           entity_id_map.get((relation["source"], "Method"))
                target_id = entity_id_map.get((relation["target"], "Class")) or \
                           entity_id_map.get((relation["target"], "Function")) or \
                           entity_id_map.get((relation["target"], "Module"))

                if source_id and target_id:
                    self.database.insert_relation(
                        source_id, target_id, relation["type"],
                        {"file": relation.get("file", ""), "line": relation.get("line", 0)}
                    )
                    relation_count += 1
                    logger.debug(f"[analyze_and_build] 关系: {relation['source']} -> {relation['target']}")

            if use_llm:
                logger.info("[analyze_and_build] 使用LLM增强分析")
                important_files = self._select_important_files(analysis_results)
                logger.info(f"[analyze_and_build] 选择{len(important_files)}个重要文件进行LLM分析")
                for file_path in important_files[:5]:
                    try:
                        self._analyze_with_llm(file_path)
                    except Exception as e:
                        logger.error(f"[analyze_and_build] LLM分析失败 {file_path}: {e}")

            summary = self.database.get_graph_summary()
            logger.info(f"[analyze_and_build] 更新会话状态: {summary}")
            self.database.update_session_status(
                session_id, "completed",
                summary["totalEntities"],
                summary["totalRelations"]
            )

            logger.info("[analyze_and_build] 分析完成")
            return {
                "status": "success",
                "sessionId": session_id,
                "totalEntities": summary["totalEntities"],
                "totalRelations": summary["totalRelations"],
                "totalFiles": len(scanned_files)
            }

        except Exception as e:
            logger.error(f"[analyze_and_build] 分析失败: {e}", exc_info=True)
            self.database.update_session_status(session_id, "failed")
            return {"status": "error", "message": str(e)}

    def analyze_single_file(self, file_path, use_llm=False):
        """分析单个文件"""
        logger.info(f"[analyze_single_file] 分析单文件: {file_path}")
        try:
            result = self.scanner.scan_single_file(file_path)
            entities = self.scanner.extract_all_entities([result])
            relations = self.scanner.extract_all_relations([result])

            logger.debug(f"[analyze_single_file] 提取: {len(entities)}实体, {len(relations)}关系")

            for entity in entities:
                self.database.find_or_create_entity(
                    entity["name"],
                    entity["type"],
                    {"docstring": entity.get("docstring", "")},
                    entity.get("file", ""),
                    entity.get("line", 0)
                )

            logger.info("[analyze_single_file] 单文件分析完成")
            return {"status": "success", "entities": len(entities), "relations": len(relations)}
        except Exception as e:
            logger.error(f"[analyze_single_file] 分析失败: {e}")
            return {"status": "error", "message": str(e)}

    def _store_code_elements(self, session_id, analysis_result):
        """存储代码元素到数据库"""
        logger.debug(f"[_store_code_elements] 存储代码元素: session={session_id}, file={analysis_result.file_path}")
        
        for cls in analysis_result.classes:
            self.database.insert_code_element(
                session_id, cls["name"], "Class",
                analysis_result.file_path, "",
                cls["line"], cls["endLine"],
                "", cls["docstring"],
                {"bases": cls["bases"], "methods": cls["methods"]}
            )

        for func in analysis_result.functions:
            parent = func.get("parentClass", "")
            kind = "Method" if parent else "Function"
            self.database.insert_code_element(
                session_id, func["name"], kind,
                analysis_result.file_path, parent,
                func["line"], func["endLine"],
                f"({', '.join(func['arguments'])})",
                func["docstring"],
                {"decorators": func.get("decorators", [])}
            )

        logger.debug(f"[_store_code_elements] 存储完成: {len(analysis_result.classes)}类, {len(analysis_result.functions)}函数")

    def _select_important_files(self, analysis_results):
        """选择重要文件进行LLM分析"""
        logger.debug("[_select_important_files] 选择重要文件")
        scored_files = []
        for result in analysis_results:
            score = len(result.classes) * 3 + len(result.functions) * 2 + len(result.imports)
            scored_files.append((result.file_path, score))
            logger.debug(f"[_select_important_files] {result.file_path}: score={score}")

        scored_files.sort(key=lambda x: x[1], reverse=True)
        selected = [f[0] for f in scored_files[:10]]
        logger.info(f"[_select_important_files] 选择{len(selected)}个重要文件")
        return selected

    def _analyze_with_llm(self, file_path):
        """使用LLM分析文件"""
        logger.info(f"[_analyze_with_llm] LLM分析: {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                source_code = f.read()
        except Exception as e:
            logger.error(f"[_analyze_with_llm] 读取文件失败: {e}")
            return

        if len(source_code) < 50:
            logger.debug(f"[_analyze_with_llm] 代码太短，跳过: {len(source_code)}字符")
            return

        logger.debug(f"[_analyze_with_llm] 调用LLM API")
        llm_result = self.llm_client.extract_entities_and_relations(source_code, file_path)
        logger.debug(f"[_analyze_with_llm] LLM返回: {llm_result}")

        if isinstance(llm_result, dict):
            entities = llm_result.get("entities", [])
            relations = llm_result.get("relations", [])
            logger.info(f"[_analyze_with_llm] LLM发现: {len(entities)}实体, {len(relations)}关系")

            for entity in entities:
                self.database.find_or_create_entity(
                    entity.get("name", "unknown"),
                    entity.get("type", "Unknown"),
                    entity.get("properties", {}),
                    file_path,
                    entity.get("line", 0)
                )

            for relation in relations:
                source = relation.get("source", "")
                target = relation.get("target", "")
                rel_type = relation.get("type", "relates_to")
                if source and target:
                    source_id = self.database.find_or_create_entity(source, "Unknown")
                    target_id = self.database.find_or_create_entity(target, "Unknown")
                    self.database.insert_relation(
                        source_id, target_id, rel_type,
                        {"llm_enhanced": True},
                        confidence=0.7
                    )

    def get_visualization_data(self):
        """获取可视化数据"""
        logger.info("[get_visualization_data] 获取可视化数据")
        return self.database.export_graph_data()
