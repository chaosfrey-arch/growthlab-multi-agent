"""
分析师 Agent — 调用 A/B 测试工具获取数据，用 LLM 解读结果
"""

import json
from config import call_llm, extract_json
from tools.ab_test import run_ab_test

SYSTEM_PROMPT = """你是一个数据分析师，负责解读 A/B 测试结果并给出数据驱动的结论。

## 你的输入
1. 实验方案（策略 + 执行细节）
2. A/B 测试的统计结果（lift、p值、置信区间）

## 你的任务
1. 解读统计结果的业务含义
2. 判断实验是否达到预期
3. 分析与预期的偏差原因
4. 计算对整体漏斗的影响

## 输出格式（严格 JSON）
```json
{
  "lift_observed": 0.15,
  "p_value": 0.003,
  "ci_95": [0.08, 0.22],
  "significant": true,
  "conclusion": "实验显著，观测提升15%，置信区间[8%, 22%]",
  "vs_expected": "低于预期25%，实际提升约为预期的60%",
  "funnel_impact": "该步转化率从35%提升至40.3%，预计日新增付费用户+X人",
  "recommendation": "建议推全量 / 建议迭代优化 / 建议放弃"
}
```

注意：
- lift_observed、p_value、ci_95 必须直接使用输入的统计数据，不要修改
- significant 必须基于 p_value < 0.05 判断
- funnel_impact 要算出对终端指标的具体影响"""


def run(client, strategy: dict, experiment: dict, funnel: dict) -> dict:
    target_step = strategy["target_step"]
    baseline_rate = 0.10
    for step in funnel["funnel"]:
        if step["key"] == target_step:
            baseline_rate = step["rate"]
            break

    ab_result = run_ab_test(
        intervention_id=strategy["intervention_id"],
        baseline_rate=baseline_rate,
        sample_size=experiment.get("sample_size", 10000),
    )

    user_content = f"""实验策略：
{json.dumps(strategy, ensure_ascii=False, indent=2)}

实验方案：
{json.dumps(experiment, ensure_ascii=False, indent=2)}

A/B 测试统计结果（来自模拟器，请直接使用这些数字）：
{json.dumps(ab_result, ensure_ascii=False, indent=2)}

当前漏斗基线：
{json.dumps(funnel["funnel"], ensure_ascii=False, indent=2)}
日流量：{funnel["daily_traffic"]}

请解读这些统计结果，分析业务影响。输出 JSON。
重要：lift_observed、p_value、ci_95、significant 必须直接使用上面的统计数据。"""

    raw = call_llm(client, SYSTEM_PROMPT, user_content)
    analysis = extract_json(raw)

    analysis["lift_observed"] = ab_result["lift_observed"]
    analysis["p_value"] = ab_result["p_value"]
    analysis["ci_95"] = ab_result["ci_95"]
    analysis["significant"] = ab_result["significant"]
    analysis["_raw_ab_result"] = ab_result

    return analysis
