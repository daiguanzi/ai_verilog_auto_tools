---
title: "参考模型与 DUT 输出数值格式对齐"
category: patterns
severity: high
simulator: verilator, cocotb
created: 2026-07-21
updated: 2026-07-21
sources: [outputs/dft8_axi]
related: [knowledge/patterns/scoreboard_reference_model.md]
---

## Problem

参考模型 (Python) 和 DUT 输出的数值表示方式不一致时，scoreboard 的 `abs(exp - got)`
比较会产生巨大误差（65535 量级），导致 false negative。

## 具体案例

参考模型的 DFT 输出用 `val_r & 0xFFFF`（unsigned, 0~65535），
但 testbench 读取 DUT 时用 `s16()` 转换（signed, -32768~32767）。
同一个 bin 的值：expected=65172(unsigned)，got=-364(signed)。
`abs(65172 - (-364)) = 65536` → 判定失败。

## Correct Pattern

**统一一个格式**并保持不变。推荐 unsigned 16-bit：

```python
def u16(val):
    return val & 0xFFFF

# 参考模型输出
result.append((val_r & 0xFFFF, val_i & 0xFFFF))

# DUT 输出读取
raw = int.from_bytes(data, "little")
real = u16(raw)
imag = u16(raw >> 16)
```

## Why Unsigned

- Verilog `reg [15:0]` 是 unsigned
- 避免 signed/unsigned 转换
- `abs()` 比较在 0~65535 范围内直接有效

## When to Apply

任何 Python reference model + DUT 比较的场景，尤其是：
- DSP/数学计算（DFT、FIR、乘法器）
- 固定点数输出
- AXI 读取的寄存器数据

**通用规则**：在 scoreboard 注册前打印前 3 组 exp/got 值验证格式一致性。
