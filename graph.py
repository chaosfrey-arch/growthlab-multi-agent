"""
LangGraph 状态图 — 多智能体编排 + 三级门控 + 多轮循环
"""

import json
import os
import sys
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END

os.environ["PYTHONIOENCODING"] = "utf-8"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from config import get_client
from agents import strategist, executor, analyst, reviewer
from validators.rules import (
    validate_strategy, validate_experiment,
    validate_analysis, validate_review,
)


# ── 状态定义 ──────────────────────────────────────────────────────────────────

class GrowthState(TypedDict):
    funnel: dict                # 漏斗基线
    history: list               # 历史实验记录
    round: int                  # 当前轮次
    max_rounds: int             # 最大轮次
    strategy: dict | None       # 策略师输出
    experiment: dict | None     # 执行官输出
    analysis: dict | None       # 分析师输出
    review: dict | None         # 复盘官输出
    retry_counts: dict          # 各 agent 重试计数 {"strategist": 0, ...}
    gate_verdict: str | None    # 最近一次门控裁决
    gate_reason: str | None     # 门控原因
    stopped: bool               # 是否被 STOP 终止


# ── Agent 节点 ────────────────────────────────────────────────────────────────

def strategist_node(state: GrowthState) -> dict:
    print(f"\n{'='*50}")
    print(f"  \U0001f504 第 {state['round']}/{state['max_rounds']} 轮实验")
    print(f"{'='*50}")
    print("\n  \U0001f9e0 [策略师] 分析漏斗，提出实验假设...")
    client = get_client()
    result = strategist.run(client, state["funnel"], state["history"])
    print(f"     → 选择策略: {result.get('intervention_name', result.get('intervention_id'))}")
    print(f"     → 假设: {result.get('hypothesis', '')[:80]}...")
    return {"strategy": result}


def executor_node(state: GrowthState) -> dict:
    print("\n  \U0001f4cb [执行官] 设计 A/B 方案 + 埋点...")
    client = get_client()
    result = executor.run(client, state["strategy"], state["funnel"])
    print(f"     → 实验: {result.get('experiment_name', '')}")
    print(f"     → 样本量: {result.get('sample_size', 'N/A')}/组")
    events = result.get("tracking_events", [])
    print(f"     → 埋点: {len(events)} 个事件")
    for e in events[:3]:
        name = e.get("event_name", e) if isinstance(e, dict) else e
        print(f"       · {name}")
    return {"experiment": result}


def analyst_node(state: GrowthState) -> dict:
    print("\n  \U0001f4ca [分析师] 运行 A/B 测试 + 统计检验...")
    client = get_client()
    result = analyst.run(client, state["strategy"], state["experiment"], state["funnel"])
    ab = result.get("_raw_ab_result", {})
    sig = "\u2705 显著" if result.get("significant") else "\u274c 不显著"
    print(f"     → lift: {result.get('lift_observed', 0):.2%}  p={result.get('p_value', 'N/A')}  {sig}")
    ci = result.get("ci_95", [0, 0])
    print(f"     → 95% CI: [{ci[0]:.2%}, {ci[1]:.2%}]")
    return {"analysis": result}


def reviewer_node(state: GrowthState) -> dict:
    print("\n  \U0001f4dd [复盘官] 总结实验，提炼学习...")
    client = get_client()
    result = reviewer.run(
        client, state["strategy"], state["experiment"],
        state["analysis"], state["history"],
    )
    print(f"     → 结论: {result.get('verdict', '')}")
    print(f"     → 学习: {result.get('key_learning', '')[:80]}...")
    print(f"     → 下一步: {result.get('next_direction', '')[:80]}...")

    # 把本轮结果写入历史
    record = {
        "round": state["round"],
        "intervention_id": state["strategy"].get("intervention_id"),
        "intervention_name": state["strategy"].get("intervention_name"),
        "hypothesis": state["strategy"].get("hypothesis"),
        "lift_observed": state["analysis"].get("lift_observed"),
        "p_value": state["analysis"].get("p_value"),
        "ci_95": state["analysis"].get("ci_95"),
        "significant": state["analysis"].get("significant"),
        "verdict": result.get("verdict"),
        "key_learning": result.get("key_learning"),
        "next_direction": result.get("next_direction"),
    }
    new_history = state["history"] + [record]

    return {
        "review": result,
        "history": new_history,
        "round": state["round"] + 1,
        "retry_counts": {"strategist": 0, "executor": 0, "analyst": 0, "reviewer": 0},
    }


# ── 门控节点 ──────────────────────────────────────────────────────────────────

def gate_strategy(state: GrowthState) -> dict:
    v = validate_strategy(
        state["strategy"], state["history"],
        state["retry_counts"].get("strategist", 0),
    )
    _print_gate("策略师", v)
    rc = dict(state["retry_counts"])
    if v["verdict"] == "RETRY":
        rc["strategist"] = rc.get("strategist", 0) + 1
    return {"gate_verdict": v["verdict"], "gate_reason": v["reason"],
            "retry_counts": rc, "stopped": v["verdict"] == "STOP"}


def gate_experiment(state: GrowthState) -> dict:
    v = validate_experiment(
        state["experiment"],
        state["retry_counts"].get("executor", 0),
    )
    _print_gate("执行官", v)
    rc = dict(state["retry_counts"])
    if v["verdict"] == "RETRY":
        rc["executor"] = rc.get("executor", 0) + 1
    return {"gate_verdict": v["verdict"], "gate_reason": v["reason"],
            "retry_counts": rc, "stopped": v["verdict"] == "STOP"}


def gate_analysis(state: GrowthState) -> dict:
    v = validate_analysis(
        state["analysis"],
        state["retry_counts"].get("analyst", 0),
    )
    _print_gate("分析师", v)
    rc = dict(state["retry_counts"])
    if v["verdict"] == "RETRY":
        rc["analyst"] = rc.get("analyst", 0) + 1
    return {"gate_verdict": v["verdict"], "gate_reason": v["reason"],
            "retry_counts": rc, "stopped": v["verdict"] == "STOP"}


def gate_review(state: GrowthState) -> dict:
    v = validate_review(
        state["review"],
        state["retry_counts"].get("reviewer", 0),
    )
    _print_gate("复盘官", v)
    rc = dict(state["retry_counts"])
    if v["verdict"] == "RETRY":
        rc["reviewer"] = rc.get("reviewer", 0) + 1
    return {"gate_verdict": v["verdict"], "gate_reason": v["reason"],
            "retry_counts": rc, "stopped": v["verdict"] == "STOP"}


def _print_gate(agent_name: str, v: dict):
    icons = {"PASS": "\u2705", "RETRY": "\U0001f504", "STOP": "\U0001f6d1"}
    print(f"\n  {icons.get(v['verdict'], '\u2753')} [门控·{agent_name}] {v['verdict']}: {v['reason']}")


# ── 路由函数 ──────────────────────────────────────────────────────────────────

def route_after_gate(target_retry: str, target_next: str):
    """通用门控路由：PASS→下一步，RETRY→重试当前，STOP→结束"""
    def router(state: GrowthState) -> str:
        v = state["gate_verdict"]
        if v == "PASS":
            return target_next
        elif v == "RETRY":
            return target_retry
        else:
            return END
    return router


def route_after_review_gate(state: GrowthState) -> str:
    if state["gate_verdict"] != "PASS":
        return "reviewer" if state["gate_verdict"] == "RETRY" else END
    if state["round"] > state["max_rounds"]:
        return END
    return "strategist"


# ── 构建图 ────────────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    g = StateGraph(GrowthState)

    # 注册节点
    g.add_node("strategist", strategist_node)
    g.add_node("gate_strategy", gate_strategy)
    g.add_node("executor", executor_node)
    g.add_node("gate_experiment", gate_experiment)
    g.add_node("analyst", analyst_node)
    g.add_node("gate_analysis", gate_analysis)
    g.add_node("reviewer", reviewer_node)
    g.add_node("gate_review", gate_review)

    # 边：agent → 门控
    g.add_edge("strategist", "gate_strategy")
    g.add_edge("executor", "gate_experiment")
    g.add_edge("analyst", "gate_analysis")
    g.add_edge("reviewer", "gate_review")

    # 条件边：门控 → 下一步 / 重试 / 终止
    g.add_conditional_edges("gate_strategy",
        route_after_gate("strategist", "executor"))
    g.add_conditional_edges("gate_experiment",
        route_after_gate("executor", "analyst"))
    g.add_conditional_edges("gate_analysis",
        route_after_gate("analyst", "reviewer"))
    g.add_conditional_edges("gate_review", route_after_review_gate)

    # 入口
    g.set_entry_point("strategist")

    return g.compile()
