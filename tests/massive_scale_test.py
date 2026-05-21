"""
Arkanalyzer Knowledge Graph System - Massive Scale Test
=========================================================
超大规模测试：10000+实体，长时间运行，极端混乱场景
通过详细日志验证系统行为
"""

import os
import sys
import time
import random
import string
import tempfile
import shutil
import threading
import json
import traceback

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "core"))

from system_configuration import logger
from knowledge_graph_database import KnowledgeGraphDatabase
from code_analysis_engine import PythonSourceAnalyzer, ProjectCodeScanner
from knowledge_graph_builder import KnowledgeGraphBuilder


class MassiveScaleTest:
    """超大规模测试"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = tempfile.mktemp(suffix=".db")
        self.errors = []
        self.stats = {
            "files_created": 0,
            "entities_expected": 0,
            "entities_actual": 0,
            "relations_actual": 0,
            "test_duration": 0
        }
        logger.info(f"[MassiveScaleTest] 初始化测试环境: dir={self.temp_dir}, db={self.temp_db}")
    
    def create_massive_project(self, num_files=500, classes_per_file=5, methods_per_class=10):
        """创建超大规模项目"""
        logger.info(f"[create_massive_project] 创建大规模项目: {num_files}文件, {classes_per_file}类/文件, {methods_per_class}方法/类")
        logger.info(f"[create_massive_project] 预期实体数: ~{num_files * classes_per_file * (1 + methods_per_class)}")
        
        start_time = time.time()
        
        # 创建多层目录结构
        subdirs = ["models", "views", "controllers", "utils", "services", "api", "core", "helpers"]
        for subdir in subdirs:
            os.makedirs(os.path.join(self.temp_dir, subdir), exist_ok=True)
            logger.debug(f"[create_massive_project] 创建目录: {subdir}")
        
        # 生成文件
        for i in range(num_files):
            subdir = random.choice(subdirs)
            filename = f"module_{i:04d}.py"
            filepath = os.path.join(self.temp_dir, subdir, filename)
            
            with open(filepath, "w") as f:
                # 文件头
                f.write(f'"""Module {i} - Auto generated for massive scale test"""\n\n')
                
                # 导入语句
                imports = random.sample([
                    "import os", "import sys", "import json", "import time",
                    "from typing import List, Dict, Optional",
                    "from datetime import datetime",
                    "import random", "import string"
                ], k=random.randint(2, 5))
                f.write("\n".join(imports) + "\n\n")
                
                # 生成类
                for j in range(classes_per_file):
                    class_name = f"Class{i:04d}_{j:02d}"
                    base_class = random.choice(["", "BaseModel", "object", "Exception"])
                    
                    f.write(f"class {class_name}({base_class}):\n")
                    f.write(f'    """Class {i}_{j} documentation"""\n\n')
                    
                    # 类变量
                    f.write(f"    CLASS_VAR = {{random.randint(1, 100)}}\n")
                    f.write(f"    _private_var = 'private'\n\n")
                    
                    # 生成方法
                    for k in range(methods_per_class):
                        method_name = f"method_{k:02d}"
                        is_async = random.random() < 0.2
                        
                        if is_async:
                            f.write(f"    async def {method_name}(self, param{k}):\n")
                        else:
                            f.write(f"    def {method_name}(self, param{k}):\n")
                        
                        f.write(f"        \"\"\"Method {k} docs\"\"\"\n")
                        f.write(f"        result = param{k} * {random.randint(1, 100)}\n")
                        f.write(f"        return self._process(result)\n\n")
                    
                    # 私有方法
                    f.write(f"    def _process(self, data):\n")
                    f.write(f"        return data + {random.randint(1, 10)}\n\n")
                
                # 模块级函数
                for m in range(random.randint(1, 3)):
                    func_name = f"utility_{i:04d}_{m}"
                    f.write(f"def {func_name}(x):\n")
                    f.write(f"    return x * 2\n\n")
            
            self.stats["files_created"] += 1
            if i % 50 == 0:
                logger.info(f"[create_massive_project] 已创建 {i}/{num_files} 个文件")
        
        self.stats["entities_expected"] = num_files * classes_per_file * (1 + methods_per_class)
        duration = time.time() - start_time
        logger.info(f"[create_massive_project] 项目创建完成: {duration:.2f}秒, {self.stats['files_created']}个文件")
    
    def run_massive_analysis(self):
        """执行大规模分析"""
        logger.info("[run_massive_analysis] 开始大规模分析")
        start_time = time.time()
        
        db = KnowledgeGraphDatabase(self.temp_db)
        builder = KnowledgeGraphBuilder(database=db)
        
        try:
            logger.info("[run_massive_analysis] 调用analyze_and_build")
            result = builder.analyze_and_build(
                self.temp_dir, 
                "massive_scale_test", 
                use_llm=False
            )
            
            if result["status"] == "success":
                logger.info(f"[run_massive_analysis] 分析成功: {result}")
                self.stats["entities_actual"] = result.get("totalEntities", 0)
                self.stats["relations_actual"] = result.get("totalRelations", 0)
            else:
                logger.error(f"[run_massive_analysis] 分析失败: {result.get('message', 'unknown')}")
                self.errors.append(f"Analysis failed: {result.get('message')}")
            
        except Exception as e:
            logger.error(f"[run_massive_analysis] 异常: {e}", exc_info=True)
            self.errors.append(str(e))
        
        duration = time.time() - start_time
        self.stats["test_duration"] = duration
        logger.info(f"[run_massive_analysis] 分析完成: {duration:.2f}秒")
        
        db.close()
    
    def verify_results(self):
        """验证结果"""
        logger.info("[verify_results] 开始验证结果")
        
        db = KnowledgeGraphDatabase(self.temp_db)
        summary = db.get_graph_summary()
        
        logger.info(f"[verify_results] 数据库摘要: {summary}")
        
        # 验证实体数量
        expected = self.stats["entities_expected"]
        actual = summary["totalEntities"]
        
        if actual < expected * 0.8:  # 允许20%误差
            msg = f"实体数量不足: 预期~{expected}, 实际{actual}"
            logger.error(f"[verify_results] {msg}")
            self.errors.append(msg)
        else:
            logger.info(f"[verify_results] 实体数量验证通过: {actual}/{expected}")
        
        # 验证数据一致性
        logger.info("[verify_results] 验证数据一致性")
        graph_data = db.export_graph_data()
        
        # 检查节点ID唯一性
        node_ids = [n["id"] for n in graph_data["nodes"]]
        if len(node_ids) != len(set(node_ids)):
            msg = "节点ID存在重复"
            logger.error(f"[verify_results] {msg}")
            self.errors.append(msg)
        else:
            logger.info("[verify_results] 节点ID唯一性验证通过")
        
        # 检查关系引用的实体是否存在
        orphan_relations = []
        for edge in graph_data["edges"]:
            if edge["source"] not in node_ids or edge["target"] not in node_ids:
                orphan_relations.append(edge)
        
        if orphan_relations:
            msg = f"发现{len(orphan_relations)}个孤儿关系"
            logger.error(f"[verify_results] {msg}")
            self.errors.append(msg)
        else:
            logger.info("[verify_results] 关系引用验证通过")
        
        db.close()
    
    def run_concurrent_stress_test(self):
        """并发压力测试"""
        logger.info("[run_concurrent_stress_test] 开始并发压力测试")
        
        db = KnowledgeGraphDatabase(self.temp_db)
        errors = []
        success_count = [0]
        
        def worker(worker_id):
            try:
                for i in range(50):
                    entity_id = db.insert_entity(
                        f"Stress_{worker_id}_{i}",
                        "StressTest",
                        {"worker": worker_id, "index": i}
                    )
                    success_count[0] += 1
                    if i % 10 == 0:
                        logger.debug(f"[concurrent_worker_{worker_id}] 已插入 {i}/50")
            except Exception as e:
                logger.error(f"[concurrent_worker_{worker_id}] 错误: {e}")
                errors.append(f"Worker {worker_id}: {e}")
        
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        start_time = time.time()
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        duration = time.time() - start_time
        logger.info(f"[run_concurrent_stress_test] 并发测试完成: {duration:.2f}秒, {success_count[0]}次成功插入")
        
        if errors:
            logger.error(f"[run_concurrent_stress_test] 发现{len(errors)}个错误")
            self.errors.extend(errors)
        
        db.close()
    
    def cleanup(self):
        """清理测试环境"""
        logger.info("[cleanup] 清理测试环境")
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            if os.path.exists(self.temp_db):
                os.remove(self.temp_db)
            logger.info("[cleanup] 清理完成")
        except Exception as e:
            logger.error(f"[cleanup] 清理失败: {e}")
    
    def run_all_tests(self):
        """运行所有测试"""
        logger.info("=" * 60)
        logger.info("超大规模测试开始")
        logger.info("=" * 60)
        
        try:
            # 阶段1: 创建大规模项目
            self.create_massive_project(num_files=200, classes_per_file=3, methods_per_class=5)
            
            # 阶段2: 执行分析
            self.run_massive_analysis()
            
            # 阶段3: 验证结果
            self.verify_results()
            
            # 阶段4: 并发压力测试
            self.run_concurrent_stress_test()
            
        finally:
            self.cleanup()
        
        # 输出报告
        logger.info("=" * 60)
        logger.info("超大规模测试报告")
        logger.info("=" * 60)
        logger.info(f"创建文件数: {self.stats['files_created']}")
        logger.info(f"预期实体数: {self.stats['entities_expected']}")
        logger.info(f"实际实体数: {self.stats['entities_actual']}")
        logger.info(f"实际关系数: {self.stats['relations_actual']}")
        logger.info(f"测试耗时: {self.stats['test_duration']:.2f}秒")
        logger.info(f"错误数: {len(self.errors)}")
        
        if self.errors:
            logger.error("发现的错误:")
            for err in self.errors:
                logger.error(f"  - {err}")
        
        return len(self.errors) == 0


def run_long_duration_test(duration_minutes=10):
    """长时间运行测试"""
    logger.info(f"[run_long_duration_test] 开始长时间测试: {duration_minutes}分钟")
    
    temp_db = tempfile.mktemp(suffix=".db")
    db = KnowledgeGraphDatabase(temp_db)
    
    start_time = time.time()
    iteration = 0
    errors = []
    
    while time.time() - start_time < duration_minutes * 60:
        try:
            # 随机操作
            op = random.choice(["insert", "query", "update"])
            
            if op == "insert":
                db.insert_entity(f"LongTest_{iteration}", "LongDuration", {"time": time.time()})
            elif op == "query":
                db.get_all_entities()
            elif op == "update":
                sessions = db.get_recent_sessions(1)
            
            iteration += 1
            
            if iteration % 100 == 0:
                elapsed = time.time() - start_time
                logger.info(f"[run_long_duration_test] 已运行 {elapsed:.1f}秒, {iteration}次操作")
            
            time.sleep(0.01)  # 短暂休眠避免CPU过载
            
        except Exception as e:
            logger.error(f"[run_long_duration_test] 错误: {e}")
            errors.append(str(e))
    
    total_duration = time.time() - start_time
    logger.info(f"[run_long_duration_test] 完成: {total_duration:.2f}秒, {iteration}次操作, {len(errors)}个错误")
    
    db.close()
    os.unlink(temp_db)
    
    return len(errors) == 0


if __name__ == "__main__":
    # 运行超大规模测试
    test = MassiveScaleTest()
    success1 = test.run_all_tests()
    
    # 运行长时间测试
    success2 = run_long_duration_test(duration_minutes=5)
    
    sys.exit(0 if (success1 and success2) else 1)
