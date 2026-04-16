"""
复盘官 Agent — 写实验复盘，给出下一步方向
"""

import json
from config import call_llm, extract_json

SYSTEM_PROMPT = """你是一个增长复盘官，负责总结 A/B 实验结论，提炼关键学习，指导下一轮实验方向。

## 你的输入
1. 本轮实验的完整链路：策略假设 → 实验方案 → 数据结果
2. 历史实验记录

## 你的任务
1. 总结本轮实验结论（成功/失败/模糊）
2. 提炼关键学习（不论成败都要有收获）
3. 给出下一轮实验方向建议

## 输出格式（严格 JSON）
```json
{
  "verdict": "推全量 / 继续迭代 / 放弃该方向 / 扩大样本再测",
  "summary": "一句话总结本轮实验",
  "key_learning": "核心学习：从数据中我们学到了什么",
  "what_worked": "有效的部分",
  "what_failed": "无效或需改进的部分",
  "next_direction": "下一轮实验建议（具体的方向和理由）",
  "confidence": "high / medium / low"
}
```

注意：
- verdict 必须是四选一：推全量 / 继续迭代 / 放弃该方向 / 扩大样本再测
- 即使实验失败，key_learning 也要有实质内容
- next_direction 要具体，不能是"继续优化"这种空话"""


def run(client, strategy: dict, experiment: dict, analysis: dict, history: list) -> dict:
    user_content = f"""本轮实验完整链路：

【策略假设】
{json.dumps(strategy, ensure_ascii=False, indent=2)}

【实验方案】
{json.dumps(experiment, ensure_ascii=False, indent=2)}

【数据结果】
{json.dumps({k: v for k, v in analysis.items() if k != "_raw_ab_result"}, ensure_ascii=False, indent=2)}

【历史实验】（共 {len(history)} 轮）：
{json.dumps(history[-3:], ensure_ascii=False, indent=2) if history else "无"}

请输出复盘 JSON。"""

    raw = call_llm(client, SYSTEM_PROMPT, user_content)
    return extract_json(raw)
