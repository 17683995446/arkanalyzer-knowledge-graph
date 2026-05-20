"""
Arkanalyzer Knowledge Graph System - Chaos Engineering Test Suite
===================================================================
混乱工程测试套件：模拟极端场景、网络故障、文件损坏、并发冲突等
"""

import os
import sys
import time
import random
import string
import tempfile
import shutil
import threading
import signal
import json
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "core"))

from knowledge_graph_database import KnowledgeGraphDatabase
from code_analysis_engine import PythonSourceAnalyzer, ProjectCodeScanner
from knowledge_graph_builder import KnowledgeGraphBuilder
from siliconflow_language_model import SiliconFlowLanguageModel


class ChaosTestResult:
    """混乱测试结果"""
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
        
    def add_pass(self, test_name, message=""):
        self.passed.append({"test": test_name, "message": message})
        print(f"[PASS] {test_name}: {message}")
        
    def add_fail(self, test_name, message=""):
        self.failed.append({"test": test_name, "message": message})
        print(f"[FAIL] {test_name}: {message}")
        
    def add_warning(self, test_name, message=""):
        self.warnings.append({"test": test_name, "message": message})
        print(f"[WARN] {test_name}: {message}")
        
    def summary(self):
        print("\n" + "=" * 60)
        print(f"混乱测试总结: 通过={len(self.passed)}, 失败={len(self.failed)}, 警告={len(self.warnings)}")
        print("=" * 60)
        if self.failed:
            print("\n失败详情:")
            for f in self.failed:
                print(f"  - {f['test']}: {f['message']}")
        return len(self.failed) == 0


# ============================================================
# 测试1: 损坏文件处理测试
# ============================================================

def test_corrupted_files(result):
    """测试系统处理损坏文件的能力"""
    print("\n>>> 测试: 损坏文件处理")
    
    temp_dir = tempfile.mkdtemp()
    analyzer = PythonSourceAnalyzer()
    
    try:
        # 创建各种损坏的Python文件
        corrupted_files = [
            # 语法错误
            ("syntax_error.py", "def broken(:\n    pass\n"),
            # 编码错误
            ("encoding_error.py", b"\xff\xfe\x00\x00\x01\x02"),
            # 空文件
            ("empty.py", ""),
            # 只有注释
            ("comments_only.py", "# Just a comment\n# Another comment\n"),
            # 超长行
            ("long_line.py", "x = '" + "a" * 100000 + "'\n"),
            # 无效Unicode
            ("invalid_unicode.py", "# \xff\xfe\nprint('hello')\n"),
            # 混合缩进
            ("mixed_indent.py", "def foo():\n  pass\n\treturn 1\n"),
            # 未闭合括号
            ("unclosed_bracket.py", "def foo():\n    x = [1, 2, 3\n    return x\n"),
        ]
        
        errors = []
        for filename, content in corrupted_files:
            filepath = os.path.join(temp_dir, filename)
            if isinstance(content, bytes):
                with open(filepath, "wb") as f:
                    f.write(content)
            else:
                with open(filepath, "w", encoding="utf-8", errors="ignore") as f:
                    f.write(content)
            
            try:
                analysis = analyzer.analyze_file(filepath)
                # 应该返回空结果而不是崩溃
            except Exception as e:
                errors.append(f"{filename}: {str(e)[:100]}")
        
        if errors:
            result.add_fail("corrupted_files", f"崩溃: {errors[0]}")
        else:
            result.add_pass("corrupted_files", "所有损坏文件处理正常，无崩溃")
            
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================
# 测试2: 极端数据测试
# ============================================================

def test_extreme_data(result):
    """测试极端数据处理"""
    print("\n>>> 测试: 极端数据")
    
    temp_db = tempfile.mktemp(suffix=".db")
    
    try:
        db = KnowledgeGraphDatabase(temp_db)
        
        # 测试1: 超长名称
        long_name = "A" * 10000
        try:
            entity_id = db.insert_entity(long_name, "Test")
            result.add_pass("extreme_long_name", f"成功处理{len(long_name)}字符名称")
        except Exception as e:
            result.add_warning("extreme_long_name", f"超长名称处理: {str(e)[:50]}")
        
        # 测试2: 特殊字符
        special_chars = ["<script>alert(1)</script>", "'; DROP TABLE--", "\x00\x01\x02", 
                        "中文日本語한국어", "emoji 🎉🎊🎁", "null\x00byte"]
        for chars in special_chars:
            try:
                entity_id = db.insert_entity(chars, "Test")
            except Exception as e:
                result.add_warning("extreme_special_chars", f"特殊字符处理失败: {str(e)[:50]}")
                break
        else:
            result.add_pass("extreme_special_chars", "所有特殊字符处理正常")
        
        # 测试3: 空值和None
        try:
            # 测试空字符串
            db.insert_entity("", "Test")
            # 测试None (应该抛出异常或处理)
            try:
                db.insert_entity(None, "Test")
            except:
                pass  # 预期会失败
            result.add_pass("extreme_null_values", "空值处理正常")
        except Exception as e:
            result.add_warning("extreme_null_values", f"空值处理: {str(e)[:50]}")
        
        # 测试4: 大量数据快速插入
        start = time.time()
        for i in range(1000):
            db.insert_entity(f"Batch_Entity_{i}", "Test", 
                           properties={"data": "x" * 100, "index": i})
        duration = time.time() - start
        result.add_pass("extreme_bulk_insert", f"1000条记录插入耗时{duration:.2f}秒")
        
        db.close()
        
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)


# ============================================================
# 测试3: 并发冲突测试
# ============================================================

def test_concurrent_conflicts(result):
    """测试并发冲突场景"""
    print("\n>>> 测试: 并发冲突")
    
    temp_db = tempfile.mktemp(suffix=".db")
    
    try:
        db = KnowledgeGraphDatabase(temp_db)
        
        # 场景1: 同名实体并发创建
        conflicts = []
        success_count = [0]
        
        def create_same_entity(thread_id):
            try:
                for i in range(10):
                    entity_id = db.find_or_create_entity(
                        f"SharedEntity_{i}", "Test"
                    )
                    success_count[0] += 1
            except Exception as e:
                conflicts.append(f"Thread {thread_id}: {str(e)[:50]}")
        
        threads = [threading.Thread(target=create_same_entity, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        if conflicts:
            result.add_warning("concurrent_same_entity", f"并发冲突: {conflicts[0]}")
        else:
            result.add_pass("concurrent_same_entity", f"并发创建同名实体成功，共{success_count[0]}次操作")
        
        # 场景2: 读写并发
        read_errors = []
        write_errors = []
        
        def reader():
            try:
                for _ in range(50):
                    db.get_all_entities()
                    time.sleep(0.001)
            except Exception as e:
                read_errors.append(str(e)[:50])
        
        def writer():
            try:
                for i in range(50):
                    db.insert_entity(f"WriterEntity_{i}", "Test")
                    time.sleep(0.001)
            except Exception as e:
                write_errors.append(str(e)[:50])
        
        threads = [threading.Thread(target=reader) for _ in range(3)]
        threads += [threading.Thread(target=writer) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        if read_errors or write_errors:
            result.add_warning("concurrent_read_write", 
                f"读写并发错误: read={len(read_errors)}, write={len(write_errors)}")
        else:
            result.add_pass("concurrent_read_write", "读写并发无错误")
        
        db.close()
        
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)


# ============================================================
# 测试4: 资源耗尽测试
# ============================================================

def test_resource_exhaustion(result):
    """测试资源耗尽场景"""
    print("\n>>> 测试: 资源耗尽")
    
    # 测试1: 大量文件描述符
    temp_dir = tempfile.mkdtemp()
    try:
        scanner = ProjectCodeScanner()
        
        # 创建大量小文件
        for i in range(500):
            filepath = os.path.join(temp_dir, f"file_{i}.py")
            with open(filepath, "w") as f:
                f.write(f"# File {i}\nclass Class{i}: pass\n")
        
        start = time.time()
        results, files = scanner.scan_directory(temp_dir)
        duration = time.time() - start
        
        result.add_pass("resource_many_files", f"扫描{len(files)}个文件，耗时{duration:.2f}秒")
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    # 测试2: 深层嵌套目录
    temp_dir = tempfile.mkdtemp()
    try:
        # 创建深层目录结构
        deep_path = temp_dir
        for i in range(20):
            deep_path = os.path.join(deep_path, f"level_{i}")
            os.makedirs(deep_path, exist_ok=True)
            with open(os.path.join(deep_path, "module.py"), "w") as f:
                f.write(f"# Level {i}\nclass Deep{i}: pass\n")
        
        scanner = ProjectCodeScanner()
        start = time.time()
        results, files = scanner.scan_directory(temp_dir)
        duration = time.time() - start
        
        result.add_pass("resource_deep_nesting", f"扫描深层目录{len(files)}个文件，耗时{duration:.2f}秒")
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================
# 测试5: LLM故障模拟
# ============================================================

def test_llm_failure_handling(result):
    """测试LLM故障处理"""
    print("\n>>> 测试: LLM故障处理")
    
    # 测试1: 无效API Key
    try:
        llm = SiliconFlowLanguageModel(api_key="invalid_key_12345")
        response = llm.chat_completion("test", "hello")
        if "error" in response.lower() or "error" in response:
            result.add_pass("llm_invalid_key", "正确处理无效API Key")
        else:
            result.add_warning("llm_invalid_key", "无效API Key未返回错误")
    except Exception as e:
        result.add_pass("llm_invalid_key", f"正确抛出异常: {str(e)[:50]}")
    
    # 测试2: 超长输入
    try:
        llm = SiliconFlowLanguageModel()
        long_code = "def test():\n    pass\n" * 10000
        response = llm.extract_entities_and_relations(long_code, "large.py")
        result.add_pass("llm_long_input", "超长输入处理正常")
    except Exception as e:
        result.add_warning("llm_long_input", f"超长输入处理: {str(e)[:50]}")
    
    # 测试3: 特殊字符输入
    try:
        llm = SiliconFlowLanguageModel()
        special_code = "# \x00\x01\x02\ndef test(): pass"
        response = llm.extract_entities_and_relations(special_code, "special.py")
        result.add_pass("llm_special_chars", "特殊字符输入处理正常")
    except Exception as e:
        result.add_warning("llm_special_chars", f"特殊字符处理: {str(e)[:50]}")


# ============================================================
# 测试6: 数据一致性测试
# ============================================================

def test_data_consistency(result):
    """测试数据一致性"""
    print("\n>>> 测试: 数据一致性")
    
    temp_db = tempfile.mktemp(suffix=".db")
    
    try:
        db = KnowledgeGraphDatabase(temp_db)
        
        # 创建测试数据
        entity1 = db.insert_entity("Entity1", "Class")
        entity2 = db.insert_entity("Entity2", "Class")
        relation = db.insert_relation(entity1, entity2, "calls")
        
        # 测试1: 外键约束
        try:
            # 尝试创建指向不存在实体的关系
            db.insert_relation(99999, 88888, "invalid")
            result.add_warning("data_foreign_key", "外键约束未生效")
        except:
            result.add_pass("data_foreign_key", "外键约束正常")
        
        # 测试2: 数据完整性
        summary1 = db.get_graph_summary()
        
        # 模拟异常中断（不正常关闭）
        conn = db._get_connection()
        conn.execute("INSERT INTO graph_entities (entity_name, entity_type) VALUES ('orphan', 'Test')")
        # 不提交
        
        summary2 = db.get_graph_summary()
        
        if summary2["totalEntities"] == summary1["totalEntities"]:
            result.add_pass("data_integrity", "未提交事务正确回滚")
        else:
            result.add_warning("data_integrity", "事务处理可能存在问题")
        
        db.close()
        
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)


# ============================================================
# 测试7: 混合场景压力测试
# ============================================================

def test_mixed_chaos(result):
    """混合混乱场景测试"""
    print("\n>>> 测试: 混合混乱场景")
    
    temp_dir = tempfile.mkdtemp()
    temp_db = tempfile.mktemp(suffix=".db")
    
    try:
        db = KnowledgeGraphDatabase(temp_db)
        builder = KnowledgeGraphBuilder(database=db)
        
        # 创建混合文件
        files_created = 0
        for i in range(50):
            # 正常文件
            filepath = os.path.join(temp_dir, f"normal_{i}.py")
            with open(filepath, "w") as f:
                f.write(f"""
class NormalClass{i}:
    def method_{i}(self):
        return {i}
""")
            files_created += 1
            
            # 损坏文件
            if i % 5 == 0:
                filepath = os.path.join(temp_dir, f"broken_{i}.py")
                with open(filepath, "w") as f:
                    f.write("def broken(:\n")
                files_created += 1
        
        # 执行分析
        analysis_result = builder.analyze_and_build(temp_dir, "chaos_test", use_llm=False)
        
        if analysis_result["status"] == "success":
            result.add_pass("mixed_chaos", 
                f"分析完成: {analysis_result['totalEntities']}实体, {analysis_result['totalRelations']}关系")
        else:
            result.add_fail("mixed_chaos", f"分析失败: {analysis_result.get('message', 'unknown')}")
        
        db.close()
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        if os.path.exists(temp_db):
            os.remove(temp_db)


# ============================================================
# 主函数
# ============================================================

def run_chaos_tests():
    print("=" * 60)
    print("Arkanalyzer 知识图谱系统 - 混乱工程测试")
    print("=" * 60)
    
    result = ChaosTestResult()
    
    # 运行所有测试
    test_corrupted_files(result)
    test_extreme_data(result)
    test_concurrent_conflicts(result)
    test_resource_exhaustion(result)
    test_llm_failure_handling(result)
    test_data_consistency(result)
    test_mixed_chaos(result)
    
    return result.summary()


if __name__ == "__main__":
    success = run_chaos_tests()
    sys.exit(0 if success else 1)
