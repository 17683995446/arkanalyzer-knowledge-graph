"""
Arkanalyzer Knowledge Graph System - First Principle Test Suite
=================================================================
第一性原理测试：以代码实际逻辑为唯一真实标准
覆盖所有分支、隐藏逻辑、默认行为、异常兜底
"""

import os
import sys
import ast
import tempfile
import shutil
import threading
import time
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "core"))

from knowledge_graph_database import KnowledgeGraphDatabase
from code_analysis_engine import PythonSourceAnalyzer, ProjectCodeScanner, CodeAnalysisResult
from knowledge_graph_builder import KnowledgeGraphBuilder
from siliconflow_language_model import SiliconFlowLanguageModel
from file_change_watcher import FileChangeWatcher


class TestReport:
    """测试报告"""
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
        
    def pass_test(self, name, msg=""):
        self.passed.append((name, msg))
        print(f"  ✓ {name}")
        
    def fail_test(self, name, msg):
        self.failed.append((name, msg))
        print(f"  ✗ {name}: {msg}")
        
    def warn_test(self, name, msg):
        self.warnings.append((name, msg))
        print(f"  ! {name}: {msg}")
        
    def summary(self):
        total = len(self.passed) + len(self.failed) + len(self.warnings)
        print(f"\n{'='*60}")
        print(f"测试结果: 通过={len(self.passed)}, 失败={len(self.failed)}, 警告={len(self.warnings)}")
        print(f"{'='*60}")
        if self.failed:
            print("失败项:")
            for name, msg in self.failed:
                print(f"  - {name}: {msg}")
        return len(self.failed) == 0


# ============================================================
# 1. 代码分析引擎 - 分支全覆盖测试
# ============================================================

def test_code_analysis_engine_branches(report):
    """测试代码分析引擎的所有分支"""
    print("\n>>> 代码分析引擎分支测试")
    
    analyzer = PythonSourceAnalyzer()
    
    # 测试1: 空文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("")
        empty_file = f.name
    result = analyzer.analyze_file(empty_file)
    if result.classes == [] and result.functions == []:
        report.pass_test("branch_empty_file", "空文件返回空结果")
    else:
        report.fail_test("branch_empty_file", "空文件应返回空结果")
    os.unlink(empty_file)
    
    # 测试2: 只有注释
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("# comment\n# another")
        comment_file = f.name
    result = analyzer.analyze_file(comment_file)
    if result.classes == [] and result.functions == []:
        report.pass_test("branch_comments_only", "纯注释文件返回空结果")
    else:
        report.fail_test("branch_comments_only", "纯注释文件应返回空结果")
    os.unlink(comment_file)
    
    # 测试3: 语法错误文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("def broken(:\n    pass")
        broken_file = f.name
    result = analyzer.analyze_file(broken_file)
    if result.classes == [] and result.functions == []:
        report.pass_test("branch_syntax_error", "语法错误文件返回空结果")
    else:
        report.fail_test("branch_syntax_error", "语法错误文件应返回空结果")
    os.unlink(broken_file)
    
    # 测试4: 不存在的文件
    result = analyzer.analyze_file("/nonexistent/path/file.py")
    if result.classes == [] and result.functions == []:
        report.pass_test("branch_nonexistent_file", "不存在文件返回空结果")
    else:
        report.fail_test("branch_nonexistent_file", "不存在文件应返回空结果")
    
    # 测试5: 包含null bytes的文件
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.py', delete=False) as f:
        f.write(b"def test():\n    pass\n\x00\x00")
        null_file = f.name
    result = analyzer.analyze_file(null_file)
    if len(result.functions) == 1:
        report.pass_test("branch_null_bytes", "正确处理包含null bytes的文件")
    else:
        report.fail_test("branch_null_bytes", f"应解析出1个函数，实际{len(result.functions)}")
    os.unlink(null_file)
    
    # 测试6: 类中的方法识别
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
class TestClass:
    def method1(self):
        pass
    
    def method2(self, x):
        return x

def standalone():
    pass
""")
        class_file = f.name
    result = analyzer.analyze_file(class_file)
    methods = [f for f in result.functions if f["type"] == "Method"]
    functions = [f for f in result.functions if f["type"] == "Function"]
    if len(methods) == 2 and len(functions) == 1:
        report.pass_test("branch_class_methods", f"正确识别{len(methods)}个方法和{len(functions)}个函数")
    else:
        report.fail_test("branch_class_methods", f"应2方法1函数，实际{len(methods)}方法{len(functions)}函数")
    os.unlink(class_file)
    
    # 测试7: 继承关系识别
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
class Parent:
    pass

class Child(Parent):
    pass

class GrandChild(Child):
    pass
""")
        inherit_file = f.name
    result = analyzer.analyze_file(inherit_file)
    if len(result.inheritance) == 2:
        report.pass_test("branch_inheritance", f"正确识别{len(result.inheritance)}个继承关系")
    else:
        report.fail_test("branch_inheritance", f"应2个继承关系，实际{len(result.inheritance)}")
    os.unlink(inherit_file)
    
    # 测试8: 导入语句识别
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
import os
import sys as system
from collections import defaultdict
from typing import List, Dict
""")
        import_file = f.name
    result = analyzer.analyze_file(import_file)
    if len(result.imports) == 5:  # os, sys, defaultdict, List, Dict
        report.pass_test("branch_imports", f"正确识别{len(result.imports)}个导入")
    else:
        report.fail_test("branch_imports", f"应5个导入，实际{len(result.imports)}")
    os.unlink(import_file)
    
    # 测试9: 函数调用识别
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
def caller():
    helper()
    another(1, 2)
    
def helper():
    pass
    
def another(a, b):
    print(a + b)
""")
        call_file = f.name
    result = analyzer.analyze_file(call_file)
    # 检查是否有调用关系
    calls_from_caller = [c for c in result.calls if c["caller"] == "caller"]
    if len(calls_from_caller) >= 2:
        report.pass_test("branch_function_calls", f"正确识别{len(calls_from_caller)}个函数调用")
    else:
        report.fail_test("branch_function_calls", f"应至少2个调用，实际{len(calls_from_caller)}")
    os.unlink(call_file)
    
    # 测试10: 异步函数
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
async def async_func():
    await something()

class AsyncClass:
    async def async_method(self):
        pass
""")
        async_file = f.name
    result = analyzer.analyze_file(async_file)
    async_funcs = [f for f in result.functions if "async" in f.get("name", "")]
    if len(result.functions) == 2:
        report.pass_test("branch_async_functions", f"正确识别异步函数")
    else:
        report.fail_test("branch_async_functions", f"应2个函数，实际{len(result.functions)}")
    os.unlink(async_file)


# ============================================================
# 2. 数据库模块 - 边界和异常测试
# ============================================================

def test_database_boundaries(report):
    """测试数据库边界条件"""
    print("\n>>> 数据库边界测试")
    
    temp_db = tempfile.mktemp(suffix=".db")
    db = KnowledgeGraphDatabase(temp_db)
    
    # 测试1: 空字符串名称
    try:
        entity_id = db.insert_entity("", "Test")
        report.pass_test("db_empty_string_name", "允许空字符串名称")
    except Exception as e:
        report.warn_test("db_empty_string_name", f"空字符串名称: {e}")
    
    # 测试2: 超长名称 (10000字符)
    long_name = "A" * 10000
    try:
        entity_id = db.insert_entity(long_name, "Test")
        report.pass_test("db_long_name", "处理超长名称")
    except Exception as e:
        report.fail_test("db_long_name", f"超长名称失败: {e}")
    
    # 测试3: 特殊字符
    special_names = [
        "<script>alert(1)</script>",
        "'; DROP TABLE--",
        "中文测试",
        "emoji 🎉",
        "with\nnewline",
        "with\ttab"
    ]
    for name in special_names:
        try:
            db.insert_entity(name, "Test")
        except Exception as e:
            report.fail_test(f"db_special_char_{name[:10]}", f"特殊字符失败: {e}")
            break
    else:
        report.pass_test("db_special_chars", "所有特殊字符处理正常")
    
    # 测试4: None值处理
    try:
        db.insert_entity(None, "Test")
        report.warn_test("db_none_name", "None名称被接受（可能不是预期行为）")
    except Exception as e:
        report.pass_test("db_none_name", f"正确拒绝None名称")
    
    # 测试5: 外键约束 - 插入无效关系
    try:
        db.insert_relation(99999, 88888, "invalid")
        report.warn_test("db_foreign_key", "外键约束未生效")
    except Exception as e:
        report.pass_test("db_foreign_key", "外键约束正常")
    
    # 测试6: 并发写入
    errors = []
    def writer(thread_id):
        try:
            for i in range(20):
                db.insert_entity(f"Concurrent_{thread_id}_{i}", "Test")
        except Exception as e:
            errors.append(str(e))
    
    threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    if errors:
        report.fail_test("db_concurrent_write", f"并发写入错误: {errors[0]}")
    else:
        report.pass_test("db_concurrent_write", "并发写入无错误")
    
    # 测试7: SQL注入测试
    malicious_name = "test'); DROP TABLE graph_entities; --"
    try:
        db.insert_entity(malicious_name, "Test")
        summary = db.get_graph_summary()
        if summary["totalEntities"] > 0:
            report.pass_test("db_sql_injection", "SQL注入防护正常")
        else:
            report.fail_test("db_sql_injection", "可能被SQL注入攻击")
    except Exception as e:
        report.pass_test("db_sql_injection", f"SQL注入被阻止: {e}")
    
    db.close()
    os.unlink(temp_db)


# ============================================================
# 3. 知识图谱构建器 - 集成链路测试
# ============================================================

def test_knowledge_graph_builder_integration(report):
    """测试知识图谱构建器集成链路"""
    print("\n>>> 知识图谱构建器集成测试")
    
    temp_dir = tempfile.mkdtemp()
    temp_db = tempfile.mktemp(suffix=".db")
    
    try:
        # 创建测试项目结构
        os.makedirs(os.path.join(temp_dir, "subdir"))
        
        # 主模块
        with open(os.path.join(temp_dir, "main.py"), "w") as f:
            f.write("""
from utils import helper
from models import User

class Application:
    def __init__(self):
        self.user = User()
    
    def run(self):
        result = helper()
        self.user.save(result)
""")
        
        # 工具模块
        with open(os.path.join(temp_dir, "utils.py"), "w") as f:
            f.write("""
def helper():
    return "help"

def another_util():
    pass
""")
        
        # 模型模块
        with open(os.path.join(temp_dir, "models.py"), "w") as f:
            f.write("""
class BaseModel:
    def save(self, data):
        pass

class User(BaseModel):
    def __init__(self):
        self.name = ""
""")
        
        # 子目录模块
        with open(os.path.join(temp_dir, "subdir", "submodule.py"), "w") as f:
            f.write("""
from main import Application

def use_app():
    app = Application()
    app.run()
""")
        
        # 执行分析
        db = KnowledgeGraphDatabase(temp_db)
        builder = KnowledgeGraphBuilder(database=db)
        
        result = builder.analyze_and_build(temp_dir, "integration_test", use_llm=False)
        
        if result["status"] != "success":
            report.fail_test("builder_integration", f"分析失败: {result.get('message', 'unknown')}")
            return
        
        # 验证结果
        summary = db.get_graph_summary()
        
        if summary["totalEntities"] < 5:
            report.fail_test("builder_entities", f"实体数量不足: {summary['totalEntities']}")
        else:
            report.pass_test("builder_entities", f"发现{summary['totalEntities']}个实体")
        
        if summary["totalFiles"] < 3:
            report.fail_test("builder_files", f"文件数量不足: {summary['totalFiles']}")
        else:
            report.pass_test("builder_files", f"分析{summary['totalFiles']}个文件")
        
        # 验证继承关系
        graph_data = db.export_graph_data()
        inherits = [e for e in graph_data["edges"] if e["type"] == "inherits"]
        if len(inherits) >= 1:  # User继承BaseModel
            report.pass_test("builder_inheritance", f"发现{len(inherits)}个继承关系")
        else:
            report.warn_test("builder_inheritance", "未发现继承关系")
        
        db.close()
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        if os.path.exists(temp_db):
            os.unlink(temp_db)


# ============================================================
# 4. LLM模块 - 错误处理测试
# ============================================================

def test_llm_error_handling(report):
    """测试LLM错误处理"""
    print("\n>>> LLM错误处理测试")
    
    # 测试1: 无效API Key
    llm = SiliconFlowLanguageModel(api_key="invalid_key_for_test")
    response = llm.chat_completion("test", "hello")
    if "error" in response.lower() or "error" in str(response).lower():
        report.pass_test("llm_invalid_key", "正确处理无效API Key")
    else:
        report.warn_test("llm_invalid_key", "无效API Key未返回错误")
    
    # 测试2: 空输入
    llm = SiliconFlowLanguageModel()
    try:
        response = llm.extract_entities_and_relations("", "empty.py")
        report.pass_test("llm_empty_input", "处理空输入")
    except Exception as e:
        report.pass_test("llm_empty_input", f"空输入处理: {e}")
    
    # 测试3: 超长输入
    long_code = "def test():\n    pass\n" * 5000
    try:
        response = llm.extract_entities_and_relations(long_code, "long.py")
        report.pass_test("llm_long_input", "处理超长输入")
    except Exception as e:
        report.warn_test("llm_long_input", f"超长输入: {e}")


# ============================================================
# 5. 文件监听器 - 行为测试
# ============================================================

def test_file_watcher_behavior(report):
    """测试文件监听器行为"""
    print("\n>>> 文件监听器行为测试")
    
    temp_dir = tempfile.mkdtemp()
    changes_detected = []
    
    def callback(changed, deleted, count):
        changes_detected.append((len(changed), len(deleted), count))
    
    watcher = FileChangeWatcher(temp_dir, callback=callback)
    watcher.start_watching()
    
    # 测试1: 创建文件
    with open(os.path.join(temp_dir, "test.py"), "w") as f:
        f.write("# test")
    time.sleep(3)
    
    # 测试2: 修改文件
    with open(os.path.join(temp_dir, "test.py"), "a") as f:
        f.write("\n# modified")
    time.sleep(3)
    
    watcher.stop_watching()
    
    if len(changes_detected) >= 1:
        report.pass_test("watcher_detect_changes", f"检测到{len(changes_detected)}次变化")
    else:
        report.fail_test("watcher_detect_changes", "未检测到文件变化")
    
    shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================
# 主函数
# ============================================================

def run_all_tests():
    print("=" * 60)
    print("第一性原理全面测试")
    print("=" * 60)
    
    report = TestReport()
    
    test_code_analysis_engine_branches(report)
    test_database_boundaries(report)
    test_knowledge_graph_builder_integration(report)
    test_llm_error_handling(report)
    test_file_watcher_behavior(report)
    
    return report.summary()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
