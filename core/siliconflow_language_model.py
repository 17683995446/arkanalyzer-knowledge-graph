"""
Arkanalyzer Knowledge Graph System - SiliconFlow LLM Client
=============================================================
基于第一性原理：LLM的本质是「文本到文本的映射」，
我们将其封装为统一接口，用于知识图谱的智能构建。
"""

import json
import requests
from typing import Optional

from system_configuration import (
    SILICONFLOW_API_ENDPOINT,
    SILICONFLOW_API_KEY,
    SILICONFLOW_DEFAULT_MODEL,
    SILICONFLOW_MAX_TOKENS,
    SILICONFLOW_TEMPERATURE,
)


class SiliconFlowLanguageModel:
    """硅基流动大语言模型客户端"""

    def __init__(self, api_key=None, model_name=None):
        self.api_endpoint = SILICONFLOW_API_ENDPOINT
        self.api_key = api_key or SILICONFLOW_API_KEY
        self.model_name = model_name or SILICONFLOW_DEFAULT_MODEL
        self.max_tokens = SILICONFLOW_MAX_TOKENS
        self.temperature = SILICONFLOW_TEMPERATURE
        self.request_timeout = 60

    def _build_request_headers(self):
        """构建API请求头"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def _build_request_payload(self, system_prompt, user_message, temperature=None):
        """构建API请求体"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": temperature or self.temperature,
            "stream": False
        }
        return payload

    def chat_completion(self, system_prompt, user_message, temperature=None):
        """发送对话请求并返回响应文本"""
        headers = self._build_request_headers()
        payload = self._build_request_payload(system_prompt, user_message, temperature)

        try:
            response = requests.post(
                self.api_endpoint,
                headers=headers,
                json=payload,
                timeout=self.request_timeout
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            return json.dumps({"error": "LLM请求超时，请稍后重试"})
        except requests.exceptions.RequestException as exception:
            return json.dumps({"error": f"LLM请求失败: {str(exception)}"})

    def extract_entities_and_relations(self, source_code, file_path=""):
        """使用LLM从源代码中提取实体和关系"""
        system_prompt = """你是一个专业的代码分析专家。请分析给定的源代码，提取其中的实体和关系。

请严格按照以下JSON格式输出，不要输出任何其他内容：
{
  "entities": [
    {"name": "实体名称", "type": "实体类型(Class/Function/Variable/Module/Interface/Enum/Method)"}
  ],
  "relations": [
    {"source": "源实体名称", "target": "目标实体名称", "type": "关系类型(calls/imports/inherits/contains/uses/implements/depends_on)"}
  ]
}

实体类型说明：
- Class: 类定义
- Function: 独立函数
- Method: 类中的方法
- Variable: 重要变量
- Module: 模块/文件
- Interface: 接口定义
- Enum: 枚举类型

关系类型说明：
- calls: 调用关系
- imports: 导入关系
- inherits: 继承关系
- contains: 包含关系
- uses: 使用关系
- implements: 实现关系
- depends_on: 依赖关系"""

        user_message = f"请分析以下源代码文件「{file_path}」中的实体和关系：\n\n```python\n{source_code}\n```"

        response_text = self.chat_completion(system_prompt, user_message, temperature=0.1)

        try:
            # 尝试解析JSON响应
            response_text = response_text.strip()
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {"entities": [], "relations": [], "raw_response": response_text}

    def generate_code_summary(self, source_code, file_path=""):
        """使用LLM生成代码摘要"""
        system_prompt = "你是一个代码分析专家，请用简洁的中文总结给定代码的功能和结构。"
        user_message = f"请总结以下代码文件「{file_path}」的功能：\n\n```python\n{source_code[:3000]}\n```"
        return self.chat_completion(system_prompt, user_message, temperature=0.3)

    def analyze_code_relationships(self, code_elements):
        """使用LLM分析代码元素之间的关系"""
        system_prompt = """你是一个代码架构分析专家。请分析以下代码元素列表，推断它们之间的深层关系。

请严格按照以下JSON格式输出：
{
  "inferred_relations": [
    {"source": "源元素", "target": "目标元素", "type": "关系类型", "confidence": 0.8, "reason": "推断原因"}
  ]
}"""

        elements_text = "\n".join(
            f"- {elem['name']} ({elem['type']}) in {elem.get('file', 'unknown')}"
            for elem in code_elements
        )
        user_message = f"请分析以下代码元素之间的关系：\n{elements_text}"

        response_text = self.chat_completion(system_prompt, user_message, temperature=0.2)

        try:
            response_text = response_text.strip()
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {"inferred_relations": [], "raw_response": response_text}
