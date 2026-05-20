"""
Arkanalyzer Knowledge Graph System - Comprehensive Test Suite
===============================================================
全面测试套件：压力测试、边界测试、异常测试、性能测试
"""

import os
import sys
import time
import random
import string
import tempfile
import shutil
import threading
import psutil
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "core"))

from knowledge_graph_database import KnowledgeGraphDatabase
from code_analysis_engine import PythonSourceAnalyzer, ProjectCodeScanner
from siliconflow_language_model import SiliconFlowLanguageModel
from knowledge_graph_builder import KnowledgeGraphBuilder
from file_change_watcher import FileChangeWatcher


class TestResultCollector:
    """测试结果收集器"""
    
    def __init__(self):
        self.results = []
        self.errors = []
        
    def log(self, test_name, status, message="", duration=0):
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "duration": duration,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.results.append(result)
        if status == "FAIL":
            self.errors.append(result)
        print(f"[{status}] {test_name}: {message} ({duration:.2f}s)")
        
    def summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        print(f"\n{'='*60}")
        print(f"测试总结: 总计={total}, 通过={passed}, 失败={failed}")
        print(f"{'='*60}")
        if self.errors:
            print("\n失败详情:")
            for err in self.errors:
                print(f"  - {err['test']}: {err['message']}")
        return failed == 0


# ============================================================
# 测试1: 数据库压力测试
# ============================================================

def test_database_pressure(collector):
    """测试数据库在高负载下的表现"""
    start_time = time.time()
    
    # 创建临时数据库
    temp_db_path = tempfile.mktemp(suffix=".db")
    
    try:
        db = KnowledgeGraphDatabase(temp_db_path)
        
        # 压力测试1: 插入大量实体
        entity_count = 5000
        entity_ids = []
        for i in range(entity_count):
            entity_id = db.insert_entity(
                name=f"Entity_{i}_{random_string(10)}",
                entity_type=random.choice(["Class", "Function", "Method", "Variable"]),
                properties={"index": i, "data": random_string(100)},
                source_file=f"/path/to/file_{i % 100}.py",
                source_line=i
            )
            entity_ids.append(entity_id)
            
            if i % 1000 == 0:
                print(f"  已插入 {i} 个实体...")
        
        # 压力测试2: 插入大量关系
        relation_count = 10000
        for i in range(relation_count):
            source = random.choice(entity_ids)
            target = random.choice(entity_ids)
            if source != target:
                db.insert_relation(
                    source, target,
                    random.choice(["calls", "imports", "inherits", "uses"]),
                    properties={"weight": random.random()},
                    confidence=random.random()
                )
            
            if i % 2000 == 0:
                print(f"  已插入 {i} 个关系...")
        
        # 压力测试3: 复杂查询
        query_start = time.time()
        summary = db.get_graph_summary()
        query_time = time.time() - query_start
        
        # 压力测试4: 数据导出
        export_start = time.time()
        graph_data = db.export_graph_data()
        export_time = time.time() - export_start
        
        # 验证结果
        assert summary["totalEntities"] == entity_count, f"实体数量不匹配: {summary['totalEntities']} != {entity_count}"
        
        collector.log(
            "database_pressure_test", "PASS",
            f"插入{entity_count}实体/{relation_count}关系, 查询{query_time:.2f}s, 导出{export_time:.2f}s",
            time.time() - start_time
        )
        
        db.close()
        
    except Exception as e:
        collector.log("database_pressure_test", "FAIL", str(e), time.time() - start_time)
    finally:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)


# ============================================================
# 测试2: 大文件分析测试
# ============================================================

def test_large_file_analysis(collector):
    """测试分析超大文件"""
    start_time = time.time()
    
    # 创建临时大文件
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 生成一个包含大量代码的文件 (约5000行)
        large_file = os.path.join(temp_dir, "large_module.py")
        with open(large_file, "w") as f:
            f.write("\"\"\"Large test module\"\"\"\n\n")
            
            # 生成100个类，每个类有20个方法
            for i in range(100):
                f.write(f"\nclass LargeClass{i}:\n")
                f.write(f'    \"\"\"Class {i} documentation\"\"\"\n\n')
                
                for j in range(20):
                    f.write(f"    def method_{j}(self, param1, param2):\n")
                    f.write(f"        \"\"\"Method {j} docs\"\"\"\n")
                    f.write(f"        result = param1 + param2\n")
                    f.write(f"        return self._process_result(result)\n\n")
                
                f.write(f"    def _process_result(self, data):\n")
                f.write(f"        return data * 2\n\n")
        
        # 分析大文件
        analyzer = PythonSourceAnalyzer()
        result = analyzer.analyze_file(large_file)
        
        duration = time.time() - start_time
        
        # 验证结果
        expected_classes = 100
        expected_methods = 100 * 21  # 100类 * (20方法 + 1私有方法)
        
        actual_classes = len(result.classes)
        actual_methods = len([f for f in result.functions if f["type"] == "Method"])
        
        if actual_classes < expected_classes * 0.9:  # 允许10%误差
            collector.log("large_file_analysis", "FAIL", 
                f"类数量不足: {actual_classes} < {expected_classes * 0.9}", duration)
        else:
            collector.log("large_file_analysis", "PASS",
                f"分析{actual_classes}个类/{actual_methods}个方法, 耗时{duration:.2f}s",
                duration)
        
    except Exception as e:
        collector.log("large_file_analysis", "FAIL", str(e), time.time() - start_time)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================
# 测试3: 文件监听压力测试
# ============================================================

def test_file_watcher_pressure(collector):
    """测试文件监听器在大量文件变化时的表现"""
    start_time = time.time()
    
    temp_dir = tempfile.mkdtemp()
    change_count = [0]
    error_count = [0]
    
    def callback(changed, deleted, count):
        try:
            change_count[0] += len(changed) + len(deleted)
        except Exception as e:
            error_count[0] += 1
            print(f"  回调错误: {e}")
    
    try:
        # 创建监听器
        watcher = FileChangeWatcher(temp_dir, callback=callback)
        watcher.start_watching()
        
        # 创建大量文件
        file_count = 100
        for i in range(file_count):
            with open(os.path.join(temp_dir, f"test_{i}.py"), "w") as f:
                f.write(f"# Test file {i}\n")
        
        # 等待监听检测
        time.sleep(3)
        
        # 修改大量文件
        for i in range(file_count):
            with open(os.path.join(temp_dir, f"test_{i}.py"), "a") as f:
                f.write(f"\n# Modified at {time.time()}\n")
        
        # 等待处理
        time.sleep(3)
        
        watcher.stop_watching()
        
        duration = time.time() - start_time
        
        if error_count[0] > 0:
            collector.log("file_watcher_pressure", "FAIL",
                f"发生{error_count[0]}个回调错误", duration)
        else:
            collector.log("file_watcher_pressure", "PASS",
                f"处理{file_count}个文件变化, 检测到{change_count[0]}次变更", duration)
        
    except Exception as e:
        collector.log("file_watcher_pressure", "FAIL", str(e), time.time() - start_time)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================
# 测试4: 并发测试
# ============================================================

def test_concurrent_access(collector):
    """测试并发访问数据库 - 使用单实例多线程（模拟实际Web服务器场景）"""
    start_time = time.time()
    
    temp_db_path = tempfile.mktemp(suffix=".db")
    errors = []
    success_count = [0]
    
    # 单实例数据库（模拟Flask应用中的全局数据库实例）
    db = KnowledgeGraphDatabase(temp_db_path)
    
    def worker(worker_id):
        try:
            for i in range(50):
                db.insert_entity(
                    name=f"Worker{worker_id}_Entity{i}",
                    entity_type="Test",
                    properties={"worker": worker_id}
                )
                success_count[0] += 1
            return True
        except Exception as e:
            errors.append(f"Worker {worker_id}: {e}")
            return False
    
    try:
        # 5个并发线程（单实例多线程）
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, i) for i in range(5)]
            results = [f.result() for f in as_completed(futures)]
        
        db.close()
        
        duration = time.time() - start_time
        
        if errors:
            collector.log("concurrent_access", "FAIL",
                f"{len(errors)}个错误: {errors[0]}", duration)
        else:
            collector.log("concurrent_access", "PASS",
                f"单实例5线程共插入{success_count[0]}实体, 全部成功", duration)
        
    except Exception as e:
        collector.log("concurrent_access", "FAIL", str(e), time.time() - start_time)
    finally:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)


# ============================================================
# 测试5: 内存泄漏测试
# ============================================================

def test_memory_leak(collector):
    """测试长时间运行是否存在内存泄漏"""
    start_time = time.time()
    
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    try:
        temp_db_path = tempfile.mktemp(suffix=".db")
        db = KnowledgeGraphDatabase(temp_db_path)
        
        # 执行大量操作
        for batch in range(10):
            for i in range(500):
                entity_id = db.insert_entity(
                    name=f"Batch{batch}_Entity{i}",
                    entity_type="Test",
                    properties={"batch": batch}
                )
            
            # 强制清理
            import gc
            gc.collect()
            
            current_memory = process.memory_info().rss / 1024 / 1024
            print(f"  Batch {batch}: 内存使用 {current_memory:.1f} MB")
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        db.close()
        
        duration = time.time() - start_time
        
        # 如果内存增长超过100MB，认为可能存在泄漏
        if memory_increase > 100:
            collector.log("memory_leak", "FAIL",
                f"内存增长{memory_increase:.1f}MB, 可能存在泄漏", duration)
        else:
            collector.log("memory_leak", "PASS",
                f"内存增长{memory_increase:.1f}MB, 在合理范围内", duration)
        
        os.remove(temp_db_path)
        
    except Exception as e:
        collector.log("memory_leak", "FAIL", str(e), time.time() - start_time)


# ============================================================
# 测试6: 异常处理测试
# ============================================================

def test_error_handling(collector):
    """测试各种异常情况的处理"""
    start_time = time.time()
    errors_found = []
    
    # 测试1: 分析不存在的文件
    try:
        analyzer = PythonSourceAnalyzer()
        result = analyzer.analyze_file("/nonexistent/file.py")
        if result.classes or result.functions:
            errors_found.append("分析不存在文件应返回空结果")
    except Exception as e:
        errors_found.append(f"分析不存在文件抛出异常: {e}")
    
    # 测试2: 分析损坏的Python文件
    temp_dir = tempfile.mkdtemp()
    try:
        bad_file = os.path.join(temp_dir, "bad.py")
        with open(bad_file, "w") as f:
            f.write("def broken(:\n    pass\n")  # 语法错误
        
        analyzer = PythonSourceAnalyzer()
        result = analyzer.analyze_file(bad_file)
        # 应该返回空结果而不是崩溃
    except Exception as e:
        errors_found.append(f"分析损坏文件抛出异常: {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    # 测试3: 数据库操作异常
    try:
        temp_db_path = tempfile.mktemp(suffix=".db")
        db = KnowledgeGraphDatabase(temp_db_path)
        # 尝试插入无效数据
        db.insert_entity(None, "Test")  # name为None
        errors_found.append("插入None名称应失败")
    except Exception as e:
        pass  # 预期会抛出异常
    finally:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
    
    duration = time.time() - start_time
    
    if errors_found:
        collector.log("error_handling", "FAIL", errors_found[0], duration)
    else:
        collector.log("error_handling", "PASS", "所有异常情况处理正确", duration)


# ============================================================
# 测试7: LLM API测试
# ============================================================

def test_llm_integration(collector):
    """测试LLM集成的稳定性和错误处理"""
    start_time = time.time()
    
    try:
        llm = SiliconFlowLanguageModel()
        
        # 测试1: 正常调用
        code = """
def hello_world():
    print("Hello, World!")
    return 42
"""
        result = llm.extract_entities_and_relations(code, "test.py")
        
        if "error" in result:
            collector.log("llm_integration", "FAIL",
                f"LLM调用失败: {result.get('error')}", time.time() - start_time)
            return
        
        # 测试2: 超长代码
        long_code = "\n".join([f"def func_{i}(): pass" for i in range(100)])
        result2 = llm.extract_entities_and_relations(long_code, "long.py")
        
        duration = time.time() - start_time
        
        collector.log("llm_integration", "PASS",
            f"LLM API调用成功, 耗时{duration:.2f}s", duration)
        
    except Exception as e:
        collector.log("llm_integration", "FAIL", str(e), time.time() - start_time)


# ============================================================
# 辅助函数
# ============================================================

def random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


# ============================================================
# 主函数
# ============================================================

def run_all_tests():
    print("=" * 60)
    print("Arkanalyzer 知识图谱系统 - 全面测试套件")
    print("=" * 60)
    
    collector = TestResultCollector()
    
    # 运行所有测试
    tests = [
        ("数据库压力测试", test_database_pressure),
        ("大文件分析测试", test_large_file_analysis),
        ("文件监听压力测试", test_file_watcher_pressure),
        ("并发访问测试", test_concurrent_access),
        ("内存泄漏测试", test_memory_leak),
        ("异常处理测试", test_error_handling),
        ("LLM集成测试", test_llm_integration),
    ]
    
    for test_name, test_func in tests:
        print(f"\n>>> 开始: {test_name}")
        test_func(collector)
    
    # 输出总结
    success = collector.summary()
    return success


if __name__ == "__main__":
    run_all_tests()
