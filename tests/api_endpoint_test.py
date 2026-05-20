"""
Arkanalyzer Knowledge Graph System - API Endpoint Test
========================================================
API接口测试：遍历所有请求，验证接口行为
"""

import os
import sys
import json
import tempfile
import shutil
import time
import threading

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "core"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "web"))

from web_visualization_server import application


class APITestClient:
    """API测试客户端"""
    
    def __init__(self):
        self.app = application
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.results = []
        
    def test_get(self, endpoint, description=""):
        """测试GET请求"""
        try:
            response = self.client.get(endpoint)
            status = "PASS" if response.status_code == 200 else "FAIL"
            self.results.append({
                "method": "GET",
                "endpoint": endpoint,
                "status": status,
                "code": response.status_code,
                "description": description
            })
            return response
        except Exception as e:
            self.results.append({
                "method": "GET",
                "endpoint": endpoint,
                "status": "ERROR",
                "error": str(e),
                "description": description
            })
            return None
    
    def test_post(self, endpoint, data, description=""):
        """测试POST请求"""
        try:
            response = self.client.post(
                endpoint,
                data=json.dumps(data),
                content_type='application/json'
            )
            status = "PASS" if response.status_code in [200, 201] else "FAIL"
            self.results.append({
                "method": "POST",
                "endpoint": endpoint,
                "status": status,
                "code": response.status_code,
                "description": description
            })
            return response
        except Exception as e:
            self.results.append({
                "method": "POST",
                "endpoint": endpoint,
                "status": "ERROR",
                "error": str(e),
                "description": description
            })
            return None
    
    def print_results(self):
        """打印结果"""
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] in ["FAIL", "ERROR"])
        
        print(f"\n{'='*60}")
        print(f"API测试结果: 通过={passed}, 失败={failed}")
        print(f"{'='*60}")
        
        for r in self.results:
            status_symbol = "✓" if r["status"] == "PASS" else "✗"
            print(f"  {status_symbol} {r['method']} {r['endpoint']} - {r['status']} ({r.get('code', 'N/A')})")
        
        return failed == 0


def test_all_endpoints():
    """测试所有API端点"""
    print("=" * 60)
    print("API端点全面测试")
    print("=" * 60)
    
    client = APITestClient()
    
    # 页面路由测试
    print("\n>>> 页面路由测试")
    pages = [
        ("/", "仪表盘页面"),
        ("/knowledge_graph", "知识图谱页面"),
        ("/architecture_diagram", "架构图页面"),
        ("/flow_diagram", "流程图页面"),
        ("/sequence_diagram", "时序图页面"),
        ("/analysis_detail", "分析详情页面"),
    ]
    for endpoint, desc in pages:
        client.test_get(endpoint, desc)
    
    # API路由测试
    print("\n>>> API路由测试")
    apis = [
        ("/api/graph_summary", "图谱摘要"),
        ("/api/graph_data", "图谱数据"),
        ("/api/entity_statistics", "实体统计"),
        ("/api/relation_statistics", "关系统计"),
        ("/api/recent_sessions", "最近会话"),
        ("/api/system_info", "系统信息"),
        ("/api/watcher_status", "监听状态"),
    ]
    for endpoint, desc in apis:
        client.test_get(endpoint, desc)
    
    # POST API测试
    print("\n>>> POST API测试")
    client.test_post("/api/trigger_analysis", {
        "targetPath": PROJECT_ROOT,
        "useLLM": False
    }, "触发分析")
    
    # 带参数的API测试
    print("\n>>> 参数化API测试")
    client.test_get("/api/analysis_sessions?limit=5", "会话列表(带limit)")
    client.test_get("/api/analysis_sessions?session_id=1", "代码元素(无效session_id)")
    
    return client.print_results()


if __name__ == "__main__":
    success = test_all_endpoints()
    sys.exit(0 if success else 1)
