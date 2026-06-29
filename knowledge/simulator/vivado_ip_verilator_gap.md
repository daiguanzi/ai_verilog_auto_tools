---
title: "Vivado IP 核与 Verilator 兼容性实测（2018.2 FIFO 示例）"
category: simulator
severity: must-know
simulator: verilator
created: 2026-06-29
updated: 2026-06-29
sources: [vivado_test Tcl probe]
related: [knowledge/simulator/wsl_verilator_ops.md]
---

## 实测结论

**Vivado 目录 IP 核（如 `fifo_generator`）导出的仿真模型不能直接被 Verilator 编译。**

## 测试流程
1. Tcl 批处理创建 `fifo_generator` IP（Independent Clocks, 32bit, depth 16）
2. `generate_target simulation` + `export_simulation` 导出所有仿真器脚本
3. 用 Verilator `--lint-only` 尝试编译导出的仿真源文件 + XPM 库

## 阻塞原因（三类）

| 问题 | 文件 | 根因 |
|------|------|------|
| 🔒 **加密段** | `fifo_generator_v13_2_rfs.v` | 含 `\`pragma protected data_block`，Verilator 跳过加密内容。关键实现不可编译。 |
| 🚫 **SVA 断言** | `xpm_cdc.sv` | 用 `## ()` 和 `[*]` 等 SystemVerilog 断言操作符，Verilator 不支持。 |
| 🚫 **1995 语法** | `xpm_memory.sv` | 用 `deassign` 关键字，Verilator 不支持。 |
| 📦 **unisim 依赖** | 间接 | 部分 RFS 模型还可能实例化 Xilinx 原语（RAMB18E1、BUFG），需 unisim 仿真库，也存在兼容问题。 |

## 可以做的事情
- ✅ Vivado Tcl 批处理调 IP **完全可行**（`vivado -mode batch -source script.tcl`）
- ✅ 生成的 `.xci` 可用于**综合/实现**（阶段 D）
- ✅ IP 的行为级封装 `my_fifo.v`（顶层 wrapper）是明文
- ✅ 纯行为级模型段落是明文，可做参考但不能完整编译

## 唯一现实的 Verilator 兼容路径

**阶段 C 的 `ip_models/` 替身库**——用纯 SystemVerilog 手写行为级等价模块（如 FIFO、BRAM、clk_wiz 的简化模型），只供仿真用。Verilator 直接编译替身，上板时 Vivado 仍用真 IP `.xci`。

如确实需要仿真 IP 的真实行为 → 回退到 **Vivado xsim**（不支持 cocotb，需独立 testbench）。
