# GrowthLab — 自动化增长实验多智能体系统

基于 LangGraph 编排的 4 智能体增长实验平台，模拟“策略→执行→分析→复盘”的增长团队工作流，自动运行多轮 A/B 实验并迭代优化。

## 架构

```
           ┌──────────────────────────────┐
           │      LangGraph StateGraph     │
           └──┬────────┬────────┬────────┬─┘
              ▼        ▼        ▼        ▼
          策略师    执行官    分析师    复盘官
          (LLM)    (LLM)    (LLM)    (LLM)
              │        │        │        │
           [门控]   [门控]   [门控]   [门控]
           PASS/    PASS/    PASS/    PASS/
           RETRY/   RETRY/   RETRY/   RETRY/
           STOP     STOP     STOP     STOP
```

**数据流**：
```
funnel.json (漏斗基线)
    ▼
策略师 → [门控] → 执行官 → [门控] → 分析师 → [门控] → 复盘官 → [门控]
                                       ↑                          │
                                  ab_test.py                      │
                                (z检验+95%CI)          round < 3? │
                                                          ▼       │
                                                       策略师 ◀───┘
                                                    (带着复盘结论)
```

## 核心组件

| 组件 | 说明 |
|------|------|
| **策略师** | 分析漏斗瓶颈，从预设策略库选择干预方案，提出可量化假设 |
| **执行官** | 设计 A/B 分组、样本量、埋点方案（3-5 个事件+字段） |
| **分析师** | 调用模拟器跑 A/B → z 检验 + 95% CI → LLM 解读业务含义 |
| **复盘官** | 总结成败、提炼学习、指导下一轮方向 |
| **三级门控** | 确定性 Python 规则（非 LLM），PASS/RETRY/STOP 防幻觉 |
| **A/B 模拟器** | 伯努利采样 + 隐藏真实 lift 表，制造有成功有失败的实验 |

## 运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置 API Key
set DEEPSEEK_API_KEY=your_key_here

# 3. 运行（自动跑 3 轮实验）
python main.py
```

## 产出

每次运行生成：
- `artifacts/final_report.json` — 结构化实验数据
- `artifacts/report.txt` — 可读的实验报告
- `history/experiments.json` — 累积历史记录（下次运行会参考）

## 项目结构

```
growthlab/
├── agents/
│   ├── strategist.py     # 策略师（LLM）
│   ├── executor.py       # 执行官（LLM）
│   ├── analyst.py        # 分析师（LLM + 工具）
│   └── reviewer.py       # 复盘官（LLM）
├── validators/
│   └── rules.py          # 三级门控规则（纯 Python）
├── tools/
│   └── ab_test.py        # A/B 模拟器（numpy + scipy）
├── graph.py              # LangGraph 状态图编排
├── config.py             # DeepSeek API 配置
├── funnel.json           # 漏斗基线 + 策略库
├── main.py               # 入口
└── history/
    └── experiments.json   # 实验历史
```

## 设计亮点

1. **真正的多智能体**：每个 agent 独立 LLM 调用 + 不同 system prompt + 不同工具
2. **三级门控防幻觉**：确定性规则校验（lift 合理性、字段完整、不重复策略），不用 LLM 判 LLM
3. **A/B 统计检验**：z 检验 + 95% 置信区间，不是拍脑袋看数字
4. **多轮闭环**：复盘结论回传策略师，失败实验驱动方向调整
5. **LangGraph 条件路由**：RETRY 回当前 agent，STOP 终止流程，PASS 继续下一步
