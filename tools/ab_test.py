"""
A/B 测试工具 — 伯努利采样 + 双比例 z 检验 + 95% 置信区间
"""

import numpy as np
from scipy.stats import norm

# 每种干预策略的"真实提升"区间（对 agent 保密）
# 模拟器从区间内随机抽取 true_lift，制造有成功也有失败的实验
INTERVENTION_TRUE_LIFTS = {
    "onboarding_optimize":    (0.10, 0.30),   # 引导优化：效果较好
    "social_invite":          (0.05, 0.25),   # 社交邀请：不确定性大
    "push_reactivation":      (-0.05, 0.15),  # Push唤醒：可能无效
    "trial_upgrade":          (0.03, 0.18),   # 付费引导：中等效果
    "churn_prevention":       (0.05, 0.20),   # 续费挽回：较稳定
    "personalized_playlist":  (0.08, 0.28),   # 个性化推荐：效果好
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
    # 从预设区间随机抽取"真实"提升（agent 不知道这个值）
    lift_range = INTERVENTION_TRUE_LIFTS.get(intervention_id, (0.0, 0.10))
    true_lift = np.random.uniform(*lift_range)
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
