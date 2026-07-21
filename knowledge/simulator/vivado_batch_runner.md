---
title: "Vivado 批处理合成——Agent 调用要点"
category: simulator
severity: high
simulator: vivado
created: 2026-07-17
updated: 2026-07-17
sources: [agent_tools/vivado_backend/synth_runner.py]
related: [knowledge/simulator/ise_vm_backend.md]
---

## 背景
Agent 需从 Windows 命令行调用 Vivado 跑综合/实现/bitstream。以下为实际调试中踩的坑。

## 踩坑记录

### 1. `-source Tcl` 路径必须用绝对路径
`vivado -mode batch -source ./_synth.tcl` → `no such file or directory`。
即使 `subprocess.run` 设了 `cwd`，Vivado 对 `-source` 的路径解析也有问题。
**修复**：永远用 `os.path.abspath(tcl_path)`。

### 2. CRLF 行尾（和 ISE 一样）
Tcl 文件必须以 `\r\n` 结尾，否则 Vivado Tcl 解释器可能读不到文件末尾。
**修复**：`"\r\n".join(lines) + "\r\n"`。

### 3. 没有约束文件时 WNS/TNS 为空
如果项目没有 XDC 约束，`report_timing_summary` 输出无时钟相关数值——WNS/TNS 解析结果
为 `None`。这不是 Bug，是"无约束 → 无时序检查"的正常行为。

### 4. Utilization 报告格式（Vivado 2018.2）
资源名称带 `*`（如 `Slice LUTs*`），需用 `Slice LUTs\*?` 正则匹配。
`Block RAM` 显示为 `Block RAM Tile`。

### 5. xsim 仿真要点（xvlog → xelab → xsim）
- **SystemVerilog 不兼容**：xsim（Vivado 2018.2）只认 Verilog-2001。`logic`/`always_ff` 会报
  `unknown type`。必须用 `wire`/`reg`/`always @(...)` 写 `.v` 文件。
  ⚠️ ModelSim 10.4 **支持** SystemVerilog（实测 compiles `logic`/`always_ff`），所以
  ModelSim 可以直接用 SV RTL。
- **timescale 一致性**：所有模块（含 TB）必须都有 `` `timescale``，否则 xelab 报
  `Module doesn't have a timescale`。
- **Tcl batch 路径**：`xsim -tclbatch` 必须传**绝对路径**且用 `/` 分隔符。
- **Windows 上 .bat 优先**：`xvlog`/`xelab`/`xsim` 的无后缀版本是 Linux 二进制；
  Windows Python 必须用 `.bat` 版本。
- **自动 TB 生成**：`generate_verilog_tb()` 通用函数——同时适用于 xsim 和 ISim。
  ⚠️ 限制：只适用于 1-cycle datapath（设输入→等 2 周期→检输出）。多周期 FSM
  （如 DFT、FIFO 状态机）必须**手写专用 Verilog TB**，包含 `wait_for_done()` 循环。

---

## 开发新 Vivado 工具时的必读清单
1. 本文
2. `ise_vm_backend.md`——同类"生成脚本→调工具→解析报告"模式
3. `wsl_verilator_ops.md`——路径/行尾等跨平台坑
