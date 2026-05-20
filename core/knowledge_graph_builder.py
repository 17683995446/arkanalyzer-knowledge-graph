"""
Arkanalyzer Knowledge Graph System - Knowledge Graph Builder
==============================================================
基于第一性原理：知识图谱的本质是「结构化的知识表示」，
构建器将代码分析结果与LLM推理能力结合，生成丰富的知识图谱。
"""

import os
import json
from datetime import datetime

from knowledge_graph_database import KnowledgeGraphDatabase
from siliconflow_language_model import SiliconFlowLanguageModel
from code_analysis_engine import ProjectCodeScanner


class KnowledgeGraphBuilder:
    """知识图谱构建器：整合代码分析与LLM推理"""

    def __init__(self, database=None, language_model=None):
        self.database = database or KnowledgeGraphDatabase()
        self.language_model = language_model or SiliconFlowLanguageModel()
        self.code_scanner = ProjectCodeScanner()
        self.current_session_id = None

    def analyze_and_build(self, target_directory, session_name=None, use_llm=True):
        """分析目标目录并构建知识图谱"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_name = session_name or f"analysis_{timestamp}"

        self.current_session_id = self.database.create_analysis_session(
            session_name, target_directory
        )
        self.database.update_session_status(self.current_session_id, "running")

        try:
            # 第一步：静态代码分析
            analysis_results, scanned_files = self.code_scanner.scan_directory(target_directory)

            # 第二步：提取实体和关系
            static_entities = self.code_scanner.extract_all_entities(analysis_results)
            static_relations = self.code_scanner.extract_all_relations(analysis_results)

            # 第三步：存储静态分析结果到数据库
            entity_id_map = {}
            for entity in static_entities:
                entity_id = self.database.find_or_create_entity(
                    name=entity["name"],
                    entity_type=entity["type"],
                    properties={
                        "file": entity.get("file", ""),
                        "docstring": entity.get("docstring", ""),
                        "parentClass": entity.get("parentClass", "")
                    },
                    source_file=entity.get("file", ""),
                    source_line=entity.get("line", 0)
                )
                entity_id_map[entity["name"]] = entity_id

                # 存储代码元素
                self.database.insert_code_element(
                    session_id=self.current_session_id,
                    name=entity["name"],
                    kind=entity["type"],
                    file_path=entity.get("file", ""),
                    parent=entity.get("parentClass", ""),
                    start_line=entity.get("line", 0),
                    end_line=entity.get("endLine", entity.get("line", 0)),
                    docstring=entity.get("docstring", "")
                )

            # 第四步：存储关系
            for relation in static_relations:
                source_id = entity_id_map.get(relation["source"])
                target_id = entity_id_map.get(relation["target"])
                if source_id and target_id:
                    self.database.insert_relation(
                        source_id, target_id,
                        relation["type"],
                        properties={"file": relation.get("file", "")},
                        confidence=1.0
                    )

            # 第五步：LLM增强分析（可选）
            if use_llm:
                self._llm_enhanced_analysis(target_directory, analysis_results, entity_id_map)

            # 更新会话状态
            summary = self.database.get_graph_summary()
            self.database.update_session_status(
                self.current_session_id, "completed",
                total_entities=summary["totalEntities"],
                total_relations=summary["totalRelations"]
            )

            return {
                "status": "success",
                "sessionId": self.current_session_id,
                "scannedFiles": len(scanned_files),
                "totalEntities": summary["totalEntities"],
                "totalRelations": summary["totalRelations"]
            }

        except Exception as exception:
            self.database.update_session_status(self.current_session_id, "failed")
            return {"status": "error", "message": str(exception)}

    def _llm_enhanced_analysis(self, target_directory, analysis_results, entity_id_map):
        """使用LLM增强分析"""
        # 对关键文件进行LLM分析
        important_files = self._select_important_files(analysis_results, max_files=5)

        for result in important_files:
            file_full_path = os.path.join(target_directory, result.file_path)
            if not os.path.exists(file_full_path):
                continue

            try:
                with open(file_full_path, "r", encoding="utf-8", errors="ignore") as fh:
                    source_code = fh.read()

                if len(source_code) < 50:
                    continue

                # LLM提取实体和关系
                llm_result = self.language_model.extract_entities_and_relations(
                    source_code, result.file_path
                )

                # 合并LLM发现的实体
                for entity in llm_result.get("entities", []):
                    entity_id = self.database.find_or_create_entity(
                        name=entity["name"],
                        entity_type=entity.get("type", "Unknown"),
                        properties={"source": "llm", "file": result.file_path},
                        source_file=result.file_path
                    )
                    entity_id_map[entity["name"]] = entity_id

                # 合并LLM发现的关系
                for relation in llm_result.get("relations", []):
                    source_id = entity_id_map.get(relation["source"])
                    target_id = entity_id_map.get(relation["target"])
                    if source_id and target_id:
                        self.database.insert_relation(
                            source_id, target_id,
                            relation.get("type", "related"),
                            properties={"source": "llm", "file": result.file_path},
                            confidence=0.7
                        )

            except Exception:
                continue

    def _select_important_files(self, analysis_results, max_files=5):
        """选择重要的文件进行LLM分析"""
        scored_files = []
        for result in analysis_results:
            score = len(result.classes) * 10 + len(result.functions) * 3 + len(result.calls)
            scored_files.append((score, result))

        scored_files.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_files[:max_files]]

    def analyze_single_file(self, file_path, use_llm=True):
        """分析单个文件并更新知识图谱"""
        result = self.code_scanner.scan_single_file(file_path)

        if not result.classes and not result.functions:
            return {"status": "skipped", "message": "文件中没有发现代码元素"}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = os.path.basename(file_path)
        self.current_session_id = self.database.create_analysis_session(
            f"single_{file_name}_{timestamp}", os.path.dirname(file_path)
        )

        entities = self.code_scanner.extract_all_entities([result])
        relations = self.code_scanner.extract_all_relations([result])
        entity_id_map = {}

        for entity in entities:
            entity_id = self.database.find_or_create_entity(
                name=entity["name"],
                entity_type=entity["type"],
                properties={
                    "file": entity.get("file", ""),
                    "docstring": entity.get("docstring", ""),
                    "parentClass": entity.get("parentClass", "")
                },
                source_file=entity.get("file", ""),
                source_line=entity.get("line", 0)
            )
            entity_id_map[entity["name"]] = entity_id

        for relation in relations:
            source_id = entity_id_map.get(relation["source"])
            target_id = entity_id_map.get(relation["target"])
            if source_id and target_id:
                self.database.insert_relation(
                    source_id, target_id,
                    relation["type"],
                    properties={"file": relation.get("file", "")},
                    confidence=1.0
                )

        if use_llm:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                    source_code = fh.read()
                if len(source_code) >= 50:
                    llm_result = self.language_model.extract_entities_and_relations(
                        source_code, file_name
                    )
                    for entity in llm_result.get("entities", []):
                        entity_id = self.database.find_or_create_entity(
                            name=entity["name"],
                            entity_type=entity.get("type", "Unknown"),
                            properties={"source": "llm", "file": file_name},
                            source_file=file_name
                        )
                        entity_id_map[entity["name"]] = entity_id
                    for relation in llm_result.get("relations", []):
                        source_id = entity_id_map.get(relation["source"])
                        target_id = entity_id_map.get(relation["target"])
                        if source_id and target_id:
                            self.database.insert_relation(
                                source_id, target_id,
                                relation.get("type", "related"),
                                properties={"source": "llm", "file": file_name},
                                confidence=0.7
                            )
            except Exception:
                pass

        summary = self.database.get_graph_summary()
        self.database.update_session_status(
            self.current_session_id, "completed",
            total_entities=summary["totalEntities"],
            total_relations=summary["totalRelations"]
        )

        return {
            "status": "success",
            "sessionId": self.current_session_id,
            "entitiesFound": len(entities),
            "relationsFound": len(relations)
        }

    def get_visualization_data(self):
        """获取可视化数据"""
        graph_data = self.database.export_graph_data()
        summary = self.database.get_graph_summary()
        entity_stats = self.database.get_entity_statistics()
        relation_stats = self.database.get_relation_statistics()
        recent_sessions = self.database.get_recent_sessions(10)

        return {
            "graphData": graph_data,
            "summary": summary,
            "entityStatistics": entity_stats,
            "relationStatistics": relation_stats,
            "recentSessions": recent_sessions
        }
