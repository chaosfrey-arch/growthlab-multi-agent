"""
GrowthLab — 自动化增长实验多智能体系统
入口脚本：加载漏斗 → 运行 LangGraph → 输出实验报告
"""

import json
import sys
import os
from pathlib import Path

# Windows 终端 UTF-8 支持
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from graph import build_graph, GrowthState


def load_funnel() -> dict:
    path = BASE_DIR / "funnel.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_history() -> list:
    path = BASE_DIR / "history" / "experiments.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_history(history: list):
    path = BASE_DIR / "history" / "experiments.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def save_artifacts(state: dict):
    """把最终状态的关键产物写到 artifacts/"""
    artifacts_dir = BASE_DIR / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    # 最终报告
    report = {
        "total_rounds": state["round"] - 1,
        "experiments": state["history"],
        "stopped_early": state.get("stopped", False),
    }
    with open(artifacts_dir / "final_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 可读的文本报告
    lines = []
    lines.append("=" * 60)
    lines.append("  GrowthLab 实验报告")
    lines.append("=" * 60)
    for exp in state["history"]:
        r = exp.get("round", "?")
        sig = "\u2705 显著" if exp.get("significant") else "\u274c 不显著"
        lines.append(f"\n--- 第 {r} 轮 ---")
        lines.append(f"策略: {exp.get('intervention_name', exp.get('intervention_id'))}")
        lines.append(f"假设: {exp.get('hypothesis', 'N/A')}")
        lines.append(f"结果: lift={exp.get('lift_observed', 0):.2%}  p={exp.get('p_value', 'N/A')}  {sig}")
        ci = exp.get("ci_95", [0, 0])
        lines.append(f"置信区间: [{ci[0]:.2%}, {ci[1]:.2%}]")
        lines.append(f"结论: {exp.get('verdict', 'N/A')}")
        lines.append(f"学习: {exp.get('key_learning', 'N/A')}")
    lines.append(f"\n{'='*60}")

    with open(artifacts_dir / "report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n  \U0001f4c4 报告已保存至 artifacts/report.txt")


def main():
    print()
    print("\u2554" + "\u2550" * 58 + "\u2557")
    print("\u2551   GrowthLab — 自动化增长实验多智能体系统              \u2551")
    print("\u2551   LangGraph + DeepSeek + A/B Testing + 三级门控      \u2551")
    print("\u255a" + "\u2550" * 58 + "\u255d")

    funnel = load_funnel()
    history = load_history()
    max_rounds = 3

    print(f"\n  \U0001f4ca 漏斗场景: {funnel['scenario']}")
    print(f"  \U0001f504 计划运行: {max_rounds} 轮实验")
    print(f"  \U0001f4da 历史记录: {len(history)} 条")

    # 初始状态
    initial_state: GrowthState = {
        "funnel": funnel,
        "history": history,
        "round": 1,
        "max_rounds": max_rounds,
        "strategy": None,
        "experiment": None,
        "analysis": None,
        "review": None,
        "retry_counts": {"strategist": 0, "executor": 0, "analyst": 0, "reviewer": 0},
        "gate_verdict": None,
        "gate_reason": None,
        "stopped": False,
    }

    # 构建并运行 LangGraph
    graph = build_graph()
    final_state = graph.invoke(initial_state)

    # 保存结果
    save_history(final_state["history"])
    save_artifacts(final_state)

    completed = final_state["round"] - 1
    print(f"\n  \u2705 完成 {completed} 轮实验")
    if final_state.get("stopped"):
        print(f"  \u26a0\ufe0f  因门控 STOP 提前终止: {final_state.get('gate_reason', '')}")

    print()


if __name__ == "__main__":
    main()
