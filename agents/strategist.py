"""
策略师 Agent — 基于漏斗现状和历史复盘，提出增长实验假设
"""

import json
from config import call_llm, extract_json

SYSTEM_PROMPT = """你是一个增长策略师，负责为音乐流媒体产品提出数据驱动的增长实验假设。

## 你的输入
1. 当前漏斗数据（各步转化率 + 业务目标）
2. 可选的干预策略列表（你必须从中选择一个）
3. 历史实验记录（包含之前的成功/失败复盘）

## 你的任务
1. 分析漏斗瓶颈，找到 ROI 最高的优化点
2. 从 allowed_interventions 中选一个策略
3. 提出具体的实验假设（预期提升必须合理，不超过 50%）
4. 如果有历史复盘，必须参考失败教训和成功经验

## 输出格式（严格 JSON）
```json
{
  "intervention_id": "策略ID（必须来自 allowed_interventions）",
  "intervention_name": "策略名称",
  "target_step": "漏斗目标步骤的 key",
  "hypothesis": "如果我们做X，预计Y指标提升Z%，因为...",
  "expected_lift": 0.25,
  "rationale": "选择该策略的数据依据（引用漏斗数字）",
  "risk": "主要风险点"
}
```

注意：
- expected_lift 是小数（0.25 表示 25%），不能超过 0.5
- 不要选择历史记录中已经用过的 intervention_id
- rationale 必须引用具体的漏斗数字"""


def run(client, funnel: dict, history: list) -> str:
    user_content = f"""当前漏斗数据：
{json.dumps(funnel, ensure_ascii=False, indent=2)}

历史实验记录（{len(history)} 轮）：
{json.dumps(history, ensure_ascii=False, indent=2) if history else "无历史记录，这是第一轮实验。"}

请从 allowed_interventions 中选择一个策略，提出本轮实验假设。输出 JSON。"""

    raw = call_llm(client, SYSTEM_PROMPT, user_content)
    return extract_json(raw)
