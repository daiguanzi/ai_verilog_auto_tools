---
title: "CDC（跨时钟域）要点——仿真看不出来的最危险问题"
category: patterns
severity: must-know
simulator: verilator
created: 2026-06-29
updated: 2026-06-29
sources: []
related: []
---

## 为什么仿真看不到 CDC 问题
Verilator（以及任何仿真器）假设所有信号在时钟沿前稳定。但在真实硬件上，
从一个时钟域跨到另一个时钟域时，信号可能在采样瞬间正好在跳变（亚稳态），
导致接收端采到错误的中间值。仿真**永远**不会重现这一点。

结果："仿真 100% 通过，上板随机崩溃"。

## 必做事项（上板前）

### 1. 单 bit 信号过域——两级同步器
```verilog
logic sync_q1, sync_q2;
always_ff @(posedge dst_clk) begin
    sync_q1 <= src_signal;
    sync_q2 <= sync_q1;
end
// 使用 sync_q2，不要直接用 src_signal
```
任何一个 bit 从慢域转快域（或快转慢且能保证宽度 ≥ 2 个目标周期），必须走同步器。

### 2. 多 bit 总线过域——只用同步 FIFO
不要对多 bit 总线的每个 bit 分别加同步器（各 bit 的亚稳态恢复时间不同，
会出现"部分 bit 旧值 + 部分 bit 新值"的垃圾）。用 **异步 FIFO**（Xilinx
`xpm_fifo_async` 或 `fifo_generator` with independent clocks）。

### 3. 仿真中无法验证的东西要在 Vivado 里报告
- `report_cdc`（Tcl 命令）检查设计中的跨域路径。
- 时序约束里对 CDC 路径设 `set_false_path`，告诉 Vivado"我知道、放心吧"。

## Verilator / cocotb 中能做的
- **命名约定**：跨域信号带 `_cdc` 后缀 → review 时一眼认出。
- **不放时钟发生器**：保持所有模块用同一个 clk，让仿真简单。真实的 CDC 结构
  在 Vivado 综合时再引入（IP 核自带的 clock wizard 会处理）。

## 一句话
**仿真通过 ≠ CDC 安全。** 在仿真中"它跑起来了"，不等于板子上不炸。
必须过 Vivado CDC 报告 + 时序约束。
