"""
三级门控 — 确定性 Python 规则（不调 LLM）
每个 validator 返回 {"verdict": "PASS"/"RETRY"/"STOP", "reason": str}
"""

ALLOWED_INTERVENTION_IDS = [
    "onboarding_optimize", "social_invite", "push_reactivation",
    "trial_upgrade", "churn_prevention", "personalized_playlist",
]

MAX_RETRIES = 2


def validate_strategy(strategy: dict, history: list, retry_count: int) -> dict:
    """校验策略师输出"""
    # 必需字段
    for field in ["intervention_id", "hypothesis", "expected_lift", "target_step"]:
        if field not in strategy:
            return {"verdict": "RETRY", "reason": f"缺少必需字段: {field}"}

    # 干预 ID 必须在允许列表内
    if strategy["intervention_id"] not in ALLOWED_INTERVENTION_IDS:
        return {"verdict": "RETRY", "reason": f"intervention_id 不在允许列表内: {strategy['intervention_id']}"}

    # 预期提升不能超过 50%（幻觉检测）
    if strategy.get("expected_lift", 0) > 0.5:
        return {"verdict": "RETRY", "reason": f"expected_lift={strategy['expected_lift']}，超过 50% 上限，疑似幻觉"}

    if strategy.get("expected_lift", 0) <= 0:
        return {"verdict": "RETRY", "reason": "expected_lift 必须为正数"}

    # 不能和历史实验重复同一策略
    used_ids = [h.get("intervention_id") for h in history]
    if strategy["intervention_id"] in used_ids:
        return {"verdict": "RETRY", "reason": f"策略 {strategy['intervention_id']} 已在历史中使用过，请选择新策略"}

    # 重试超限
    if retry_count >= MAX_RETRIES:
        return {"verdict": "STOP", "reason": "策略师重试超限"}

    return {"verdict": "PASS", "reason": "策略校验通过"}


def validate_experiment(experiment: dict, retry_count: int) -> dict:
    """校验执行官输出"""
    for field in ["control_desc", "treatment_desc", "sample_size", "tracking_events"]:
        if field not in experiment:
            return {"verdict": "RETRY", "reason": f"缺少必需字段: {field}"}

    if not isinstance(experiment.get("tracking_events"), list) or len(experiment["tracking_events"]) < 2:
        return {"verdict": "RETRY", "reason": "tracking_events 至少需要 2 个埋点事件"}

    if experiment.get("sample_size", 0) < 1000:
        return {"verdict": "RETRY", "reason": "sample_size 不能低于 1000"}

    if retry_count >= MAX_RETRIES:
        return {"verdict": "STOP", "reason": "执行官重试超限"}

    return {"verdict": "PASS", "reason": "实验方案校验通过"}


def validate_analysis(analysis: dict, retry_count: int) -> dict:
    """校验分析师输出"""
    for field in ["lift_observed", "p_value", "ci_95", "significant", "conclusion"]:
        if field not in analysis:
            return {"verdict": "RETRY", "reason": f"缺少必需字段: {field}"}

    # p 值合理性
    p = analysis.get("p_value")
    if p is None or not (0 <= p <= 1):
        return {"verdict": "RETRY", "reason": f"p_value={p}，不在 [0,1] 范围内"}

    # lift 方向和显著性一致性
    if analysis.get("significant") and analysis.get("lift_observed", 0) < 0:
        return {"verdict": "RETRY", "reason": "显著但 lift 为负，结论矛盾"}

    if retry_count >= MAX_RETRIES:
        return {"verdict": "STOP", "reason": "分析师重试超限"}

    return {"verdict": "PASS", "reason": "分析结果校验通过"}


def validate_review(review: dict, retry_count: int) -> dict:
    """校验复盘官输出"""
    for field in ["verdict", "key_learning", "next_direction"]:
        if field not in review:
            return {"verdict": "RETRY", "reason": f"缺少必需字段: {field}"}

    valid_verdicts = ["推全量", "继续迭代", "放弃该方向", "扩大样本再测"]
    if review.get("verdict") not in valid_verdicts:
        return {"verdict": "RETRY", "reason": f"verdict 必须是 {valid_verdicts} 之一"}

    if retry_count >= MAX_RETRIES:
        return {"verdict": "STOP", "reason": "复盘官重试超限"}

    return {"verdict": "PASS", "reason": "复盘校验通过"}
