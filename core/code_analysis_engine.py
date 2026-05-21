"""
Arkanalyzer Knowledge Graph System - Code Analysis Engine
===========================================================
基于第一性原理：代码的本质是「结构化的文本」，
分析引擎通过AST解析和模式匹配提取代码结构信息。
模拟ArkAnalyzer的核心分析能力：控制流、数据流、调用图。
"""

import ast
import os
import re
from typing import List, Dict, Any, Optional

from system_configuration import SUPPORTED_SOURCE_EXTENSIONS, logger


class CodeAnalysisResult:
    """代码分析结果容器"""

    def __init__(self, file_path=""):
        logger.debug(f"[CodeAnalysisResult] 创建结果容器: {file_path}")
        self.file_path = file_path
        self.classes = []
        self.functions = []
        self.imports = []
        self.variables = []
        self.calls = []
        self.inheritance = []
        self.decorations = []

    def to_dict(self):
        return {
            "filePath": self.file_path,
            "classes": self.classes,
            "functions": self.functions,
            "imports": self.imports,
            "variables": self.variables,
            "calls": self.calls,
            "inheritance": self.inheritance,
            "decorations": self.decorations
        }


class PythonSourceAnalyzer:
    """Python源代码静态分析器（模拟ArkAnalyzer核心功能）"""

    def __init__(self):
        logger.debug("[PythonSourceAnalyzer] 初始化分析器")
        self.current_class = None
        self.current_function = None

    def analyze_file(self, file_path):
        """分析单个Python文件"""
        logger.info(f"[analyze_file] 开始分析文件: {file_path}")
        result = CodeAnalysisResult(file_path)

        try:
            logger.debug(f"[analyze_file] 读取文件内容: {file_path}")
            with open(file_path, "rb") as file_handle:
                raw_content = file_handle.read()
            logger.debug(f"[analyze_file] 读取到 {len(raw_content)} 字节")

            if b'\x00' in raw_content:
                logger.warning(f"[analyze_file] 检测到null bytes，正在清理")
                raw_content = raw_content.replace(b'\x00', b'')

            try:
                source_code = raw_content.decode("utf-8")
                logger.debug(f"[analyze_file] UTF-8解码成功，{len(source_code)} 字符")
            except UnicodeDecodeError:
                logger.warning(f"[analyze_file] UTF-8解码失败，使用errors='ignore'")
                source_code = raw_content.decode("utf-8", errors="ignore")
        except (IOError, OSError) as e:
            logger.error(f"[analyze_file] 文件读取失败: {e}")
            return result

        if not source_code.strip():
            logger.info(f"[analyze_file] 文件为空，跳过分析")
            return result

        try:
            logger.debug(f"[analyze_file] 解析AST")
            syntax_tree = ast.parse(source_code, filename=file_path)
            logger.debug(f"[analyze_file] AST解析成功")
        except (SyntaxError, ValueError) as e:
            logger.warning(f"[analyze_file] 语法错误: {e}")
            return result

        logger.debug(f"[analyze_file] 开始遍历AST节点")
        self._analyze_module_body(syntax_tree.body, result, file_path, None)
        
        logger.info(f"[analyze_file] 分析完成: {len(result.classes)}类, {len(result.functions)}函数, {len(result.imports)}导入")
        return result

    def _analyze_module_body(self, body, result, file_path, parent_class):
        """递归分析模块体或类体"""
        logger.debug(f"[_analyze_module_body] 分析模块体，{len(body)}个节点，parent_class={parent_class}")
        for i, node in enumerate(body):
            node_type = type(node).__name__
            logger.debug(f"[_analyze_module_body] 处理节点[{i}]: {node_type}")
            
            if isinstance(node, ast.ClassDef):
                self._analyze_class_definition(node, result, file_path)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._analyze_function_definition(node, result, file_path, parent_class)
            elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                self._analyze_import_statement(node, result)
            elif isinstance(node, ast.Assign):
                self._analyze_variable_assignment(node, result)
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                self._analyze_function_call(node.value, result)

    def _analyze_class_definition(self, node, result, file_path):
        """分析类定义"""
        logger.info(f"[_analyze_class_definition] 分析类: {node.name}")
        base_classes = [self._extract_name(base) for base in node.bases]
        logger.debug(f"[_analyze_class_definition] 基类: {base_classes}")

        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(item.name)
        logger.debug(f"[_analyze_class_definition] 方法: {methods}")

        class_info = {
            "name": node.name,
            "type": "Class",
            "line": node.lineno,
            "endLine": node.end_lineno or node.lineno,
            "bases": base_classes,
            "methods": methods,
            "docstring": ast.get_docstring(node) or ""
        }

        self._analyze_module_body(node.body, result, file_path, node.name)
        result.classes.append(class_info)
        logger.debug(f"[_analyze_class_definition] 类 {node.name} 分析完成")

        for base in base_classes:
            if base:
                result.inheritance.append({
                    "child": node.name,
                    "parent": base,
                    "type": "inherits"
                })
                logger.debug(f"[_analyze_class_definition] 添加继承关系: {node.name} -> {base}")

    def _analyze_function_definition(self, node, result, file_path, parent_class):
        """分析函数定义"""
        func_type = "Method" if parent_class else "Function"
        logger.info(f"[_analyze_function_definition] 分析{func_type}: {node.name}, parent={parent_class}")
        
        function_info = {
            "name": node.name,
            "type": func_type,
            "line": node.lineno,
            "endLine": node.end_lineno or node.lineno,
            "parentClass": parent_class,
            "arguments": [arg.arg for arg in node.args.args],
            "docstring": ast.get_docstring(node) or "",
            "decorators": []
        }
        logger.debug(f"[_analyze_function_definition] 参数: {function_info['arguments']}")

        for decorator in node.decorator_list:
            decorator_name = self._extract_name(decorator)
            if decorator_name:
                function_info["decorators"].append(decorator_name)
                result.decorations.append({
                    "target": node.name,
                    "decorator": decorator_name,
                    "line": decorator.lineno
                })
                logger.debug(f"[_analyze_function_definition] 装饰器: {decorator_name}")

        call_count = 0
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._extract_name(child.func)
                if call_name:
                    result.calls.append({
                        "caller": node.name,
                        "callee": call_name,
                        "line": child.lineno
                    })
                    call_count += 1
        logger.debug(f"[_analyze_function_definition] 发现 {call_count} 个函数调用")

        result.functions.append(function_info)
        logger.debug(f"[_analyze_function_definition] {func_type} {node.name} 分析完成")

    def _analyze_import_statement(self, node, result):
        """分析导入语句"""
        logger.debug(f"[_analyze_import_statement] 分析导入语句")
        if isinstance(node, ast.Import):
            for alias in node.names:
                result.imports.append({
                    "module": alias.name,
                    "alias": alias.asname or alias.name,
                    "line": node.lineno
                })
                logger.debug(f"[_analyze_import_statement] import {alias.name} as {alias.asname or alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            for alias in node.names:
                result.imports.append({
                    "module": module_name,
                    "name": alias.name,
                    "alias": alias.asname or alias.name,
                    "line": node.lineno
                })
                logger.debug(f"[_analyze_import_statement] from {module_name} import {alias.name}")

    def _analyze_function_call(self, node, result):
        """分析函数调用"""
        call_name = self._extract_name(node.func)
        if call_name:
            logger.debug(f"[_analyze_function_call] 顶层调用: {call_name}")

    def _analyze_variable_assignment(self, node, result):
        """分析变量赋值"""
        for target in node.targets:
            if isinstance(target, ast.Name):
                value_type = self._infer_value_type(node.value)
                result.variables.append({
                    "name": target.id,
                    "type": value_type,
                    "line": node.lineno
                })
                logger.debug(f"[_analyze_variable_assignment] 变量: {target.id} = {value_type}")

    def _extract_name(self, node):
        """从AST节点提取名称"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            attr_name = self._extract_name(node.value)
            return f"{attr_name}.{node.attr}" if attr_name else node.attr
        elif isinstance(node, ast.Call):
            return self._extract_name(node.func)
        return ""

    def _infer_value_type(self, node):
        """推断值的类型"""
        if isinstance(node, ast.Constant):
            return type(node.value).__name__
        elif isinstance(node, ast.List):
            return "list"
        elif isinstance(node, ast.Dict):
            return "dict"
        elif isinstance(node, ast.Call):
            return self._extract_name(node.func) or "unknown"
        return "unknown"


class ProjectCodeScanner:
    """项目代码扫描器"""

    def __init__(self):
        logger.info("[ProjectCodeScanner] 初始化项目扫描器")
        self.analyzer = PythonSourceAnalyzer()

    def scan_directory(self, directory_path, exclude_dirs=None):
        """扫描目录中的所有源代码文件"""
        logger.info(f"[scan_directory] 开始扫描目录: {directory_path}")
        exclude_dirs = exclude_dirs or {
            "__pycache__", ".git", "node_modules", ".venv", "venv",
            "env", ".env", "dist", "build", ".idea", ".vscode"
        }
        all_results = []
        scanned_files = []

        if not os.path.isdir(directory_path):
            logger.error(f"[scan_directory] 不是有效目录: {directory_path}")
            return all_results, scanned_files

        file_count = 0
        for root_dir, sub_dirs, file_names in os.walk(directory_path):
            sub_dirs[:] = [d for d in sub_dirs if d not in exclude_dirs]
            logger.debug(f"[scan_directory] 扫描目录: {root_dir}, 子目录: {len(sub_dirs)}, 文件: {len(file_names)}")

            for file_name in file_names:
                file_extension = os.path.splitext(file_name)[1].lower()
                if file_extension in SUPPORTED_SOURCE_EXTENSIONS:
                    full_path = os.path.join(root_dir, file_name)
                    relative_path = os.path.relpath(full_path, directory_path)
                    logger.debug(f"[scan_directory] 分析文件: {relative_path}")
                    
                    analysis_result = self.analyzer.analyze_file(full_path)
                    analysis_result.file_path = relative_path
                    all_results.append(analysis_result)
                    scanned_files.append(relative_path)
                    file_count += 1

        logger.info(f"[scan_directory] 扫描完成: {file_count}个文件, {len(all_results)}个结果")
        return all_results, scanned_files

    def scan_single_file(self, file_path):
        """扫描单个文件"""
        logger.info(f"[scan_single_file] 扫描单个文件: {file_path}")
        return self.analyzer.analyze_file(file_path)

    def extract_all_entities(self, analysis_results):
        """从分析结果中提取所有实体"""
        logger.info(f"[extract_all_entities] 从{len(analysis_results)}个结果中提取实体")
        entities = []
        for result in analysis_results:
            for cls in result.classes:
                entities.append({
                    "name": cls["name"],
                    "type": "Class",
                    "file": result.file_path,
                    "line": cls["line"],
                    "docstring": cls["docstring"]
                })
            for func in result.functions:
                entities.append({
                    "name": func["name"],
                    "type": func["type"],
                    "file": result.file_path,
                    "line": func["line"],
                    "parentClass": func.get("parentClass", ""),
                    "docstring": func["docstring"]
                })
            for imp in result.imports:
                entities.append({
                    "name": imp.get("alias", imp.get("module", "")),
                    "type": "Module",
                    "file": result.file_path,
                    "line": imp["line"]
                })
        logger.info(f"[extract_all_entities] 提取了{len(entities)}个实体")
        return entities

    def extract_all_relations(self, analysis_results):
        """从分析结果中提取所有关系"""
        logger.info(f"[extract_all_relations] 从{len(analysis_results)}个结果中提取关系")
        relations = []
        for result in analysis_results:
            for call in result.calls:
                relations.append({
                    "source": call["caller"],
                    "target": call["callee"],
                    "type": "calls",
                    "file": result.file_path,
                    "line": call["line"]
                })
            for inh in result.inheritance:
                relations.append({
                    "source": inh["child"],
                    "target": inh["parent"],
                    "type": "inherits",
                    "file": result.file_path
                })
            for imp in result.imports:
                module = imp.get("module", "")
                alias = imp.get("alias", "")
                if module and alias:
                    relations.append({
                        "source": result.file_path,
                        "target": module,
                        "type": "imports",
                        "file": result.file_path,
                        "line": imp["line"]
                    })
        logger.info(f"[extract_all_relations] 提取了{len(relations)}个关系")
        return relations
