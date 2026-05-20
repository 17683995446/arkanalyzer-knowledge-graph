"""
Arkanalyzer Knowledge Graph System - Real World Simulation
============================================================
真实场景模拟测试：模拟长时间运行、多用户访问、文件频繁变化
"""

import os
import sys
import time
import random
import threading
import tempfile
import shutil
import requests
import subprocess
import signal

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "core"))


class RealWorldSimulator:
    """真实场景模拟器"""
    
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.errors = []
        self.stats = {
            "api_calls": 0,
            "errors": 0,
            "file_changes": 0
        }
        self.running = True
        
    def simulate_api_load(self, duration_seconds=60):
        """模拟API负载"""
        print(f"[API负载测试] 持续{duration_seconds}秒...")
        start_time = time.time()
        
        endpoints = [
            "/api/graph_summary",
            "/api/graph_data",
            "/api/entity_statistics",
            "/api/relation_statistics",
            "/api/system_info"
        ]
        
        while time.time() - start_time < duration_seconds and self.running:
            endpoint = random.choice(endpoints)
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                self.stats["api_calls"] += 1
                if response.status_code != 200:
                    self.stats["errors"] += 1
                    self.errors.append(f"{endpoint}: HTTP {response.status_code}")
            except Exception as e:
                self.stats["errors"] += 1
                self.errors.append(f"{endpoint}: {str(e)}")
            
            time.sleep(random.uniform(0.1, 0.5))
        
        print(f"[API负载测试] 完成: {self.stats['api_calls']}次调用, {self.stats['errors']}个错误")
    
    def simulate_file_changes(self, temp_dir, duration_seconds=60):
        """模拟文件频繁变化"""
        print(f"[文件变化测试] 持续{duration_seconds}秒...")
        start_time = time.time()
        
        file_count = 0
        while time.time() - start_time < duration_seconds and self.running:
            # 创建新文件
            if random.random() < 0.3:
                file_path = os.path.join(temp_dir, f"dynamic_{file_count}.py")
                with open(file_path, "w") as f:
                    f.write(f"""
class DynamicClass{file_count}:
    def method_{random.randint(1, 100)}(self):
        return {random.randint(1, 1000)}
""")
                file_count += 1
                self.stats["file_changes"] += 1
            
            # 修改现有文件
            existing_files = [f for f in os.listdir(temp_dir) if f.startswith("dynamic_")]
            if existing_files and random.random() < 0.5:
                file_path = os.path.join(temp_dir, random.choice(existing_files))
                try:
                    with open(file_path, "a") as f:
                        f.write(f"\n# Modified at {time.time()}\n")
                    self.stats["file_changes"] += 1
                except:
                    pass
            
            # 删除文件
            if existing_files and random.random() < 0.1:
                file_path = os.path.join(temp_dir, random.choice(existing_files))
                try:
                    os.remove(file_path)
                    self.stats["file_changes"] += 1
                except:
                    pass
            
            time.sleep(random.uniform(0.2, 1.0))
        
        print(f"[文件变化测试] 完成: {self.stats['file_changes']}次文件变化")
    
    def run_simulation(self, duration_seconds=120):
        """运行完整模拟"""
        print("=" * 60)
        print("真实场景模拟测试")
        print("=" * 60)
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        print(f"临时目录: {temp_dir}")
        
        try:
            # 启动多个并发线程
            threads = [
                threading.Thread(target=self.simulate_api_load, args=(duration_seconds,)),
                threading.Thread(target=self.simulate_file_changes, args=(temp_dir, duration_seconds))
            ]
            
            for t in threads:
                t.start()
            
            # 等待完成
            for t in threads:
                t.join()
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        # 输出结果
        print("\n" + "=" * 60)
        print("模拟结果:")
        print(f"  API调用: {self.stats['api_calls']}")
        print(f"  API错误: {self.stats['errors']}")
        print(f"  文件变化: {self.stats['file_changes']}")
        if self.errors:
            print(f"\n错误详情 (前5个):")
            for err in self.errors[:5]:
                print(f"  - {err}")
        print("=" * 60)
        
        return self.stats["errors"] == 0


def test_database_connection_pool():
    """测试数据库连接池在高并发下的表现"""
    print("\n[数据库连接池测试]")
    
    from knowledge_graph_database import KnowledgeGraphDatabase
    import tempfile
    
    temp_db = tempfile.mktemp(suffix=".db")
    errors = []
    
    def worker(worker_id):
        try:
            db = KnowledgeGraphDatabase(temp_db)
            for i in range(50):
                db.insert_entity(f"Worker{worker_id}_Entity{i}", "Test")
            db.close()
            return True
        except Exception as e:
            errors.append(f"Worker {worker_id}: {e}")
            return False
    
    # 20个并发线程
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    if os.path.exists(temp_db):
        os.remove(temp_db)
    
    if errors:
        print(f"  FAIL: {len(errors)}个错误")
        for e in errors[:3]:
            print(f"    - {e}")
        return False
    else:
        print("  PASS: 20个线程并发访问无错误")
        return True


def test_large_project_analysis():
    """测试分析大型项目"""
    print("\n[大型项目分析测试]")
    
    from code_analysis_engine import ProjectCodeScanner
    import tempfile
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 创建100个Python文件，每个包含多个类
        for i in range(100):
            file_path = os.path.join(temp_dir, f"module_{i}.py")
            with open(file_path, "w") as f:
                f.write(f"\"\"\"Module {i}\"\"\"\n\n")
                # 每个文件5个类，每个类10个方法
                for j in range(5):
                    f.write(f"class Class{i}_{j}:\n")
                    f.write(f'    \"\"\"Class {i}_{j}\"\"\"\n\n')
                    for k in range(10):
                        f.write(f"    def method_{k}(self, x):\n")
                        f.write(f"        return x * {k}\n\n")
        
        start_time = time.time()
        scanner = ProjectCodeScanner()
        results, files = scanner.scan_directory(temp_dir)
        duration = time.time() - start_time
        
        total_classes = sum(len(r.classes) for r in results)
        total_methods = sum(len([f for f in r.functions if f["type"] == "Method"]) for r in results)
        
        print(f"  扫描了{len(files)}个文件")
        print(f"  发现{total_classes}个类, {total_methods}个方法")
        print(f"  耗时: {duration:.2f}秒")
        
        expected_classes = 100 * 5  # 100文件 * 5类
        expected_methods = 100 * 5 * 10  # 100文件 * 5类 * 10方法
        
        if total_classes >= expected_classes * 0.95 and total_methods >= expected_methods * 0.95:
            print("  PASS: 大型项目分析正确")
            return True
        else:
            print(f"  FAIL: 预期{expected_classes}类/{expected_methods}方法")
            return False
            
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    # 运行测试
    results = []
    
    # 测试1: 数据库连接池
    results.append(("数据库连接池", test_database_connection_pool()))
    
    # 测试2: 大型项目分析
    results.append(("大型项目分析", test_large_project_analysis()))
    
    # 测试3: 真实场景模拟（如果服务器在运行）
    try:
        response = requests.get("http://localhost:5000/api/system_info", timeout=2)
        if response.status_code == 200:
            print("\n检测到服务器运行，执行真实场景模拟...")
            simulator = RealWorldSimulator()
            results.append(("真实场景模拟", simulator.run_simulation(duration_seconds=60)))
        else:
            print("\n服务器未运行，跳过真实场景模拟")
    except:
        print("\n服务器未运行，跳过真实场景模拟")
    
    # 总结
    print("\n" + "=" * 60)
    print("测试结果总结:")
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
    print("=" * 60)
