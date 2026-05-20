#!/usr/bin/env python3
"""
Arkanalyzer Knowledge Graph System - Main Entry Point
=======================================================
系统启动入口脚本。
用法: python main_application_entry.py [--no-llm] [--port PORT]
"""

import os
import sys
import argparse

# 确保项目根目录在Python路径中
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "core"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "web"))

from system_configuration import WEB_SERVER_PORT, PROJECT_ROOT as CONFIG_ROOT


def parse_command_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Arkanalyzer 知识图谱可视化系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main_application_entry.py              # 默认启动，端口5000
  python main_application_entry.py --no-llm     # 禁用LLM分析
  python main_application_entry.py --port 8080  # 使用8080端口
        """
    )
    parser.add_argument("--port", type=int, default=WEB_SERVER_PORT, help="Web服务端口 (默认: 5000)")
    parser.add_argument("--no-llm", action="store_true", help="禁用LLM增强分析")
    parser.add_argument("--target", type=str, default="", help="指定分析目标目录")
    return parser.parse_args()


def check_dependencies():
    """检查依赖是否安装"""
    missing = []
    try:
        import flask
    except ImportError:
        missing.append("flask")
    try:
        import requests
    except ImportError:
        missing.append("requests")
    try:
        import echarts  # 仅检查，实际使用CDN
    except ImportError:
        pass  # ECharts通过CDN加载，不需要本地安装

    if missing:
        print("=" * 50)
        print("缺少依赖包，正在自动安装...")
        print("=" * 50)
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--break-system-packages"] + missing
        )
        print("依赖安装完成！")


def main():
    """主函数"""
    arguments = parse_command_arguments()

    print("=" * 60)
    print("  Arkanalyzer 知识图谱可视化系统")
    print("  技术栈: ArkAnalyzer → SQLite")
    print("  LLM: SiliconFlow (Qwen/Qwen2.5-7B-Instruct)")
    print("=" * 60)

    check_dependencies()

    # 导入并启动Web服务器
    from web_visualization_server import application, start_web_server

    target_path = arguments.target or CONFIG_ROOT
    print(f"\n分析目标: {target_path}")
    print(f"LLM分析: {'禁用' if arguments.no_llm else '启用'}")
    print(f"服务端口: {arguments.port}")
    print(f"访问地址: http://localhost:{arguments.port}")
    print("\n正在启动系统...\n")

    # 更新端口配置
    from system_configuration import WEB_SERVER_HOST, WEB_DEBUG_MODE
    start_web_server(watch_path=target_path)


if __name__ == "__main__":
    main()
