"""
Arkanalyzer Knowledge Graph System - Long Running Stability Test
==================================================================
长时间稳定性测试：模拟持续运行场景
"""

import os
import sys
import time
import random
import threading
import tempfile
import shutil
import psutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "core"))

from knowledge_graph_database import KnowledgeGraphDatabase
from knowledge_graph_builder import KnowledgeGraphBuilder


def run_stability_test(duration_minutes=5):
    """运行稳定性测试"""
    print("=" * 60)
    print(f"长时间稳定性测试 - 持续{duration_minutes}分钟")
    print("=" * 60)
    
    temp_dir = tempfile.mkdtemp()
    temp_db = tempfile.mktemp(suffix=".db")
    
    db = KnowledgeGraphDatabase(temp_db)
    builder = KnowledgeGraphBuilder(database=db)
    
    # 统计
    stats = {
        "operations": 0,
        "errors": 0,
        "memory_samples": [],
        "start_time": time.time()
    }
    
    process = psutil.Process()
    
    def memory_monitor():
        """内存监控线程"""
        while time.time() - stats["start_time"] < duration_minutes * 60:
            mem = process.memory_info().rss / 1024 / 1024
            stats["memory_samples"].append(mem)
            time.sleep(5)
    
    def continuous_operations():
        """持续操作"""
        iteration = 0
        while time.time() - stats["start_time"] < duration_minutes * 60:
            try:
                # 随机操作
                op = random.choice(["insert", "query", "analyze"])
                
                if op == "insert":
                    for i in range(10):
                        db.insert_entity(f"Entity_{iteration}_{i}", "Test")
                    stats["operations"] += 10
                    
                elif op == "query":
                    db.get_all_entities()
                    db.get_entity_statistics()
                    stats["operations"] += 2
                    
                elif op == "analyze":
                    # 创建临时文件并分析
                    test_file = os.path.join(temp_dir, f"test_{iteration}.py")
                    with open(test_file, "w") as f:
                        f.write(f"class Test{iteration}:\n    def method(self): pass\n")
                    builder.analyze_single_file(test_file, use_llm=False)
                    stats["operations"] += 1
                
                iteration += 1
                time.sleep(0.1)
                
            except Exception as e:
                stats["errors"] += 1
                print(f"错误: {e}")
    
    # 启动线程
    mem_thread = threading.Thread(target=memory_monitor, daemon=True)
    op_thread = threading.Thread(target=continuous_operations, daemon=True)
    
    mem_thread.start()
    op_thread.start()
    
    # 等待完成
    op_thread.join()
    mem_thread.join()
    
    # 结果
    duration = time.time() - stats["start_time"]
    avg_memory = sum(stats["memory_samples"]) / len(stats["memory_samples"]) if stats["memory_samples"] else 0
    max_memory = max(stats["memory_samples"]) if stats["memory_samples"] else 0
    min_memory = min(stats["memory_samples"]) if stats["memory_samples"] else 0
    
    print("\n" + "=" * 60)
    print("稳定性测试结果:")
    print(f"  运行时间: {duration:.1f}秒")
    print(f"  操作次数: {stats['operations']}")
    print(f"  错误次数: {stats['errors']}")
    print(f"  内存使用: 平均{avg_memory:.1f}MB, 最小{min_memory:.1f}MB, 最大{max_memory:.1f}MB")
    print("=" * 60)
    
    # 清理
    db.close()
    shutil.rmtree(temp_dir, ignore_errors=True)
    if os.path.exists(temp_db):
        os.remove(temp_db)
    
    return stats["errors"] == 0


if __name__ == "__main__":
    success = run_stability_test(duration_minutes=2)  # 测试环境缩短为2分钟
    sys.exit(0 if success else 1)
