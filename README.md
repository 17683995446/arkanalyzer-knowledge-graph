# Arkanalyzer Knowledge Graph System

基于第一性原理设计的知识图谱可视化系统，使用 ArkAnalyzer → SQLite 技术栈，集成硅基流动免费LLM模型进行智能分析。

## 功能特性

- **代码分析引擎**: 模拟ArkAnalyzer核心功能，支持AST解析、控制流分析、调用图生成
- **知识图谱构建**: 自动从源代码中提取实体和关系，构建知识图谱
- **LLM增强分析**: 集成硅基流动免费模型(Qwen/Qwen2.5-7B-Instruct)，智能提取深层关系
- **可视化Web界面**: 
  - 知识图谱力导向图 (ECharts)
  - 系统架构图 (Mermaid)
  - 流程图和时序图
- **文件监听与热更新**: 自动检测文件变化，增量更新知识图谱

## 技术栈

- **后端**: Python 3.x + Flask
- **数据库**: SQLite (WAL模式)
- **前端**: HTML5 + CSS3 + JavaScript
- **可视化**: ECharts 5.5 + Mermaid 10
- **LLM**: SiliconFlow API (Qwen/Qwen2.5-7B-Instruct)

## 项目结构

```
arkanalyzer_knowledge_graph/
├── core/                           # 核心模块
│   ├── system_configuration.py     # 系统配置
│   ├── knowledge_graph_database.py # 数据库模型
│   ├── siliconflow_language_model.py # LLM客户端
│   ├── code_analysis_engine.py     # 代码分析引擎
│   ├── knowledge_graph_builder.py  # 知识图谱构建器
│   └── file_change_watcher.py      # 文件监听器
├── web/                            # Web服务
│   ├── web_visualization_server.py # Flask服务器
│   ├── templates/                  # HTML模板
│   └── static/                     # 静态资源
├── tests/                          # 测试套件
├── data/                           # 数据存储
└── logs/                           # 日志文件
```

## 快速开始

```bash
# 安装依赖
pip install flask requests

# 启动系统
python main_application_entry.py

# 访问Web界面
open http://localhost:5000
```

## API接口

- `GET /api/graph_summary` - 获取图谱摘要
- `GET /api/graph_data` - 获取完整图谱数据
- `GET /api/entity_statistics` - 获取实体统计
- `GET /api/relation_statistics` - 获取关系统计
- `POST /api/trigger_analysis` - 触发代码分析

## 测试

```bash
# 运行全面测试套件
python tests/comprehensive_test_suite.py

# 运行混乱工程测试
python tests/chaos_engineering_test.py

# 运行稳定性测试
python tests/long_running_stability.py
```

## 许可证

MIT License
