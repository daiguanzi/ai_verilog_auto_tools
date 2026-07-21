---
title: "Verilog 宽度截断：大位宽拼接赋值到小位宽目标"
category: patterns
severity: must-know
simulator: verilog, verilator, vivado
created: 2026-07-21
updated: 2026-07-21
sources: [outputs/dft8_axi]
related: [knowledge/simulator/wsl_verilator_ops.md]
---

## Problem

在 Verilog 中，拼接表达式 `{A, B}` 的位宽 = 位宽(A) + 位宽(B)。当赋值到
一个更窄的目标时，高位被静默截断，不会报错。

## 典型案例 (DFT8-AXI)

```verilog
// acc_i, acc_r 是 40-bit signed; m_i, m_r 是 32-bit
// (acc_i + m_i) >>> 15  结果是 40 bit
// (acc_r + m_r) >>> 15  结果也是 40 bit
// 拼接 {40-bit, 40-bit} = 80 bit
// 赋值给 32-bit regs[...] → 只保留低 32 bit!

regs[OUT_BASE + k_idx] <= {(acc_i + m_i) >>> 15, (acc_r + m_r) >>> 15};
//  ❌ 错误! imag 部分 (高 40 bit) 被截断丢失
```

## Correct Pattern

用中间 wire 截取所需位宽：

```verilog
wire [15:0] dft_out_r = (acc_r + m_r) >>> 15;  // 40→16 bit 隐式截断
wire [15:0] dft_out_i = (acc_i + m_i) >>> 15;
// 现在拼接是 {16-bit, 16-bit} = 32 bit → 安全
regs[index] <= {dft_out_i, dft_out_r};  // ✅ 正确!
```

## When to Apply

任何需要将多个计算结果打包为单个寄存器的场景，尤其是：
- AXI 总线寄存器（`{imag, real}` 打包）
- 状态+数据组合输出
- 多字段 FIFO 写入

**通用规则**：拼接表达式中每个操作数的位宽应等于目标字段位宽，不要让截断发生
在拼接之后。
