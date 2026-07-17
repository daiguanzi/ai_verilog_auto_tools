---
title: "时序收敛与资源优化——从 Vivado 报告到可上板的 RTL"
category: patterns
severity: must-know
simulator: vivado
created: 2026-07-17
updated: 2026-07-17
sources: [agent_tools/vivado_backend, outputs/d2_xdc_test, outputs/d3_test]
related: [knowledge/simulator/vivado_batch_runner.md]
---

## 背景
仿真通过 ≠ 上板能跑。真实硬件有时序限制——每级组合逻辑的传播延迟不能超过
时钟周期。Vivado 综合后产生**时序报告**，Agent 必须能读懂并应对。

## 时序报告关键指标

| 指标 | 含义 | 目标 |
|------|------|------|
| **WNS** (Worst Negative Slack) | 最差路径比时钟周期晚了多少 ns | WNS ≥ 0 = 时序收敛 |
| **TNS** (Total Negative Slack) | 所有违例路径的总延迟违例 | TNS = 0 = 无违例 |
| **Failing Endpoints** | 多少条路径没通过 | 0 条 |

- WNS < 0 但接近 0（如 -0.2ns）→ 可以微调（小优化或略放宽周期）
- WNS << 0（如 -3.3ns）→ 设计结构需要改（加流水/分段/降逻辑深度）
- **没有时钟约束时 WNS 为空**——必须设 `create_clock` 才会有时序检查

## 时序不收敛时的修复策略（按优先级）

| # | 策略 | 做法 | 效果 |
|---|------|------|------|
| 1 | **放宽时钟周期** | 比如 100MHz→50MHz（10ns→20ns） | 直接消违例，但降低性能 |
| 2 | **加流水级** | 把一条长组合路径拆成 2-3 级寄存器 | 增加 latency，不降低吞吐 |
| 3 | **降逻辑深度** | 减少乘法/除法级联，用加法器代替 | 需要改 RTL |
| 4 | **伪路径** | 对 CDC 路径 set_false_path | 仅跨域路径适用 |

Agent 的 `timing_loop` 已实现了策略 1 的自动化——WNS < 0 时自动加倍时钟周期，重新综合，直到收敛。

## 约束必须项

- **时钟约束**（必须）：每个时钟域必须有一条 `create_clock`，否则 Vivado 不知道
  时钟频率，无法做时序分析
- **引脚约束**（上板时必须）：`set_property PACKAGE_PIN` + `IOSTANDARD` 指定
  哪个信号对应板子上哪个物理引脚
- **伪路径**（CDC 时必须）：跨时钟域路径不在同一时钟域内，必须设 `set_false_path`

## 资源报告解读

| 资源 | 典型用途 |
|------|---------|
| **Slice LUTs** | 组合逻辑 + 小型存储（distributed RAM） |
| **Slice Registers** | 流水线寄存器、状态寄存器、计数器 |
| **Block RAM** | 大容量存储（FIFO、查找表、ROM） |
| **DSPs** | 乘法、乘累加、浮点运算 |

- 这些数字对应 FPGA 芯片的物理资源数量（如 xc7a200t：LUT=134600，Reg=269200）
- 资源利用率 <70% 才能稳定布局布线；>90% 容易布线失败

## 经验数字（xc7a200t, -2L 速度等级）

- 纯组合逻辑（无乘法器）约可跑 200-300MHz（3-5ns 周期）
- 一级 DSP48E1 乘法约 4ns
- 大扇出/长走线会增加 1-2ns 延迟
- Agent 实测：adder（9 LUT/9 Reg）在 10ns 时钟下 WNS=+4.5ns（余量充足）
- cascade（69 LUT/7 DSP）在 1ns 时钟下 WNS=-3.3ns → 需放宽到 ~8ns
