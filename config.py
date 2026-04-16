"""
GrowthLab 配置 — DeepSeek API 客户端
"""

import os
import sys
from openai import OpenAI

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = "deepseek-chat"


def get_client() -> OpenAI:
    if not DEEPSEEK_API_KEY:
        print("❌ 未找到 DEEPSEEK_API_KEY 环境变量")
        print("   请运行：set DEEPSEEK_API_KEY=your_key_here")
        sys.exit(1)
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")


def call_llm(client: OpenAI, system_prompt: str, user_content: str) -> str:
    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content


def extract_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON 代码块"""
    import re, json
    match = re.search(r"```json\s*([\s\S]+?)\s*```", text)
    if match:
        return json.loads(match.group(1))
    return json.loads(text.strip())
