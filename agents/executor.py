"""
执行官 Agent — 把策略假设变成 A/B 实验方案 + 埋点清单
"""

import json
from config import call_llm, extract_json

SYSTEM_PROMPT = """你是一个增长实验执行官，负责把策略假设转化为可执行的 A/B 测试方案。

## 你的输入
1. 策略师提出的实验假设
2. 当前漏斗基线数据

## 你的任务
1. 设计 A/B 实验的对照组和实验组
2. 确定样本量（合理范围 5000-20000）
3. 设计埋点方案（3-5 个关键事件 + 字段）
4. 明确实验周期和成功标准

## 输出格式（严格 JSON）
```json
{
  "experiment_name": "实验名称",
  "control_desc": "对照组描述（保持现状）",
  "treatment_desc": "实验组描述（具体改动）",
  "sample_size": 10000,
  "duration_days": 7,
  "success_metric": "核心成功指标",
  "success_threshold": "最小可检测效应（MDE）",
  "tracking_events": [
    {
      "event_name": "事件名",
      "trigger": "触发条件",
      "params": ["参数1", "参数2"]
    }
  ],
  "segmentation": "用户分群策略（如：新用户/7日未登录用户）"
}
```

注意：
- 埋点事件至少 3 个，覆盖实验的关键路径
- sample_size 在 5000-20000 之间
- tracking_events 的 params 要具体，不能是泛泛的"用户ID\""""


def run(client, strategy: dict, funnel: dict) -> str:
    user_content = f"""策略师的实验假设：
{json.dumps(strategy, ensure_ascii=False, indent=2)}

当前漏斗基线：
{json.dumps(funnel["funnel"], ensure_ascii=False, indent=2)}

请设计 A/B 实验方案和埋点清单。输出 JSON。"""

    raw = call_llm(client, SYSTEM_PROMPT, user_content)
    return extract_json(raw)
