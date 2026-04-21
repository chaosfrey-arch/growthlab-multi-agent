"""
A/B 测试工具 — 伯努利采样 + 双比例 z 检验 + 95% 置信区间

设计说明：
每种干预策略有一个固定的真实提升值（true_lift），对 Agent 保密。
随机性仅来自伯努利采样过程（模拟用户层面的自然波动），
而非 true_lift 本身——这与真实 A/B 测试的统计原理一致：
策略的真实效果是固定的，观测到的 lift 因样本噪声而波动。
"""

import numpy as np
from scipy.stats import norm

# 每种干预策略的固定真实提升（对 agent 保密）
# 值基于行业经验设定：有的策略效果好，有的效果弱甚至无效
INTERVENTION_TRUE_LIFTS = {
    "onboarding_optimize":    0.18,    # 引导优化：效果较好
    "social_invite":          0.12,    # 社交邀请：中等效果
    "push_reactivation":      0.05,    # Push唤醒：效果弱，样本量小时可能不显著
    "trial_upgrade":          0.09,    # 付费引导：中等效果
    "churn_prevention":       0.14,    # 续费挽回：较稳定
    "personalized_playlist":  0.15,    # 个性化推荐：效果较好
}


def run_ab_test(intervention_id: str, baseline_rate: float, sample_size: int = 10000) -> dict:
    """
    运行一次 A/B 测试模拟。

    参数:
        intervention_id: 干预策略 ID（对应 INTERVENTION_TRUE_LIFTS 的 key）
        baseline_rate: 漏斗该步的基线转化率
        sample_size: 每组样本量

    返回:
        包含 lift、p_value、ci_95、significant 的结果字典
    """
    # 固定的真实提升（agent 不知道这个值）
    # 随机性仅来自下方的伯努利采样，不来自 true_lift 本身
    true_lift = INTERVENTION_TRUE_LIFTS.get(intervention_id, 0.05)
    treatment_rate = min(baseline_rate * (1 + true_lift), 0.99)

    # 伯努利采样
    n = sample_size
    control_conversions = np.random.binomial(n, baseline_rate)
    treatment_conversions = np.random.binomial(n, treatment_rate)

    p_c = control_conversions / n
    p_t = treatment_conversions / n

    # 双比例 z 检验（手动实现）
    p_pool = (control_conversions + treatment_conversions) / (2 * n)
    se_pool = np.sqrt(p_pool * (1 - p_pool) * (2 / n))
    z_stat = (p_t - p_c) / se_pool if se_pool > 0 else 0.0
    p_value = 1 - norm.cdf(z_stat)  # 单侧检验

    # 观测 lift
    lift_observed = (p_t - p_c) / p_c if p_c > 0 else 0.0

    # 95% 置信区间（lift 的 CI）
    diff = p_t - p_c
    se_diff = np.sqrt(p_c * (1 - p_c) / n + p_t * (1 - p_t) / n)
    ci_low = (diff - 1.96 * se_diff) / p_c if p_c > 0 else 0.0
    ci_high = (diff + 1.96 * se_diff) / p_c if p_c > 0 else 0.0

    return {
        "intervention_id": intervention_id,
        "sample_size_per_group": n,
        "control_rate": round(p_c, 4),
        "treatment_rate": round(p_t, 4),
        "lift_observed": round(lift_observed, 4),
        "p_value": round(p_value, 4),
        "ci_95": [round(ci_low, 4), round(ci_high, 4)],
        "significant": bool(p_value < 0.05),
        "z_stat": round(z_stat, 4),
    }
