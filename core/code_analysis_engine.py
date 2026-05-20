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

from system_configuration import SUPPORTED_SOURCE_EXTENSIONS


class CodeAnalysisResult:
    """代码分析结果容器"""

    def __init__(self, file_path=""):
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
        self.current_class = None
        self.current_function = None

    def analyze_file(self, file_path):
        """分析单个Python文件"""
        result = CodeAnalysisResult(file_path)

        try:
            # 首先以二进制模式读取，检测null bytes
            with open(file_path, "rb") as file_handle:
                raw_content = file_handle.read()
            
            # 检查并移除null bytes
            if b'\x00' in raw_content:
                raw_content = raw_content.replace(b'\x00', b'')
            
            # 解码为字符串
            try:
                source_code = raw_content.decode("utf-8")
            except UnicodeDecodeError:
                source_code = raw_content.decode("utf-8", errors="ignore")
        except (IOError, OSError):
            return result

        if not source_code.strip():
            return result

        try:
            syntax_tree = ast.parse(source_code, filename=file_path)
        except (SyntaxError, ValueError):
            # SyntaxError: 语法错误
            # ValueError: 包含无效字符（如null bytes残留）
            return result

        # 使用递归遍历而不是ast.walk()，以保持父子关系
        self._analyze_module_body(syntax_tree.body, result, file_path, None)

        return result

    def _analyze_module_body(self, body, result, file_path, parent_class):
        """递归分析模块体或类体"""
        for node in body:
            if isinstance(node, ast.ClassDef):
                self._analyze_class_definition(node, result, file_path)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._analyze_function_definition(node, result, file_path, parent_class)
            elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                self._analyze_import_statement(node, result)
            elif isinstance(node, ast.Assign):
                self._analyze_variable_assignment(node, result)
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                # 顶层函数调用
                self._analyze_function_call(node.value, result)

    def _analyze_class_definition(self, node, result, file_path):
        """分析类定义"""
        base_classes = [self._extract_name(base) for base in node.bases]
        
        # 收集类中的方法名
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(item.name)
        
        class_info = {
            "name": node.name,
            "type": "Class",
            "line": node.lineno,
            "endLine": node.end_lineno or node.lineno,
            "bases": base_classes,
            "methods": methods,
            "docstring": ast.get_docstring(node) or ""
        }

        # 递归分析类体中的方法
        self._analyze_module_body(node.body, result, file_path, node.name)

        result.classes.append(class_info)

        for base in base_classes:
            if base:
                result.inheritance.append({
                    "child": node.name,
                    "parent": base,
                    "type": "inherits"
                })

    def _analyze_function_definition(self, node, result, file_path, parent_class):
        """分析函数定义"""
        function_info = {
            "name": node.name,
            "type": "Method" if parent_class else "Function",
            "line": node.lineno,
            "endLine": node.end_lineno or node.lineno,
            "parentClass": parent_class,
            "arguments": [arg.arg for arg in node.args.args],
            "docstring": ast.get_docstring(node) or "",
            "decorators": []
        }

        for decorator in node.decorator_list:
            decorator_name = self._extract_name(decorator)
            if decorator_name:
                function_info["decorators"].append(decorator_name)
                result.decorations.append({
                    "target": node.name,
                    "decorator": decorator_name,
                    "line": decorator.lineno
                })

        # 分析函数体中的调用
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._extract_name(child.func)
                if call_name:
                    result.calls.append({
                        "caller": node.name,
                        "callee": call_name,
                        "line": child.lineno
                    })

        result.functions.append(function_info)

    def _analyze_import_statement(self, node, result):
        """分析导入语句"""
        if isinstance(node, ast.Import):
            for alias in node.names:
                result.imports.append({
                    "module": alias.name,
                    "alias": alias.asname or alias.name,
                    "line": node.lineno
                })
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            for alias in node.names:
                result.imports.append({
                    "module": module_name,
                    "name": alias.name,
                    "alias": alias.asname or alias.name,
                    "line": node.lineno
                })

    def _analyze_function_call(self, node, result):
        """分析函数调用"""
        call_name = self._extract_name(node.func)
        if call_name and not result.calls:
            pass  # 已在函数分析中处理

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
        self.analyzer = PythonSourceAnalyzer()

    def scan_directory(self, directory_path, exclude_dirs=None):
        """扫描目录中的所有源代码文件"""
        exclude_dirs = exclude_dirs or {
            "__pycache__", ".git", "node_modules", ".venv", "venv",
            "env", ".env", "dist", "build", ".idea", ".vscode"
        }
        all_results = []
        scanned_files = []

        if not os.path.isdir(directory_path):
            return all_results, scanned_files

        for root_dir, sub_dirs, file_names in os.walk(directory_path):
            sub_dirs[:] = [d for d in sub_dirs if d not in exclude_dirs]

            for file_name in file_names:
                file_extension = os.path.splitext(file_name)[1].lower()
                if file_extension in SUPPORTED_SOURCE_EXTENSIONS:
                    full_path = os.path.join(root_dir, file_name)
                    relative_path = os.path.relpath(full_path, directory_path)
                    analysis_result = self.analyzer.analyze_file(full_path)
                    analysis_result.file_path = relative_path
                    all_results.append(analysis_result)
                    scanned_files.append(relative_path)

        return all_results, scanned_files

    def scan_single_file(self, file_path):
        """扫描单个文件"""
        return self.analyzer.analyze_file(file_path)

    def extract_all_entities(self, analysis_results):
        """从分析结果中提取所有实体"""
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
        return entities

    def extract_all_relations(self, analysis_results):
        """从分析结果中提取所有关系"""
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
        return relations
