---
title: "IP 替身模型开发要点——从 BRAM 项目踩坑中总结"
category: patterns
severity: must-know
simulator: verilator
created: 2026-07-08
updated: 2026-07-08
sources: [ip_models/bram]
related: [knowledge/patterns/robust_test_reset.md, knowledge/patterns/delayed_input_signal.md, knowledge/simulator/wsl_verilator_ops.md]
---

## 背景
为 Xilinx IP（如 `blk_mem_gen`）写 Verilator 兼容的替身模型时，会重复踩几类坑。
本文汇总 **开发 BRAM 替身过程中实际踩过的坑**，供后续 FIFO/时钟/浮点等替身开发时参考。

## 坑 1：String 参数在 Verilator 中不工作

```verilog
// ❌ Verilator 5.036 报 Illegal character in decimal constant: S
parameter MODE = "SDP";

// ✓ 用整数编码
parameter int MODE = 0;   // 0=SDP, 1=SP_RAM, 2=ROM
```
**根因**：Verilator 不支持 string 类型的模块参数。所有枚举型参数必须用整数。

## 坑 2：project.json 参数类型必须与 RTL 完全匹配

```json
// ❌ RTL 里 MODE 是 int，但 project.json 填了字符串
{ "parameters": {"MODE": "SDP"} }

// ✓ 类型一致
{ "parameters": {"MODE": 0} }
```
`MODE: "SDP"` 会被 cocotb 透传为 `-GMODE=SDP`，Verilator 把 `SDP` 当数组常量解析→报错。
**教训**：改 RTL 参数类型时一定要同步改 project.json。

## 坑 3：GPI 写延迟 + 跨测试污染（老问题，反复犯）

已有知识 `delayed_input_signal.md` 和 `robust_test_reset.md` 讲得很清楚，但写 BRAM 替身时又踩了一遍：
- 写 addr/data 后必须等至少 1 个 RisingEdge 才能读
- **每个 test 开头必须清空所有控制信号**（`reset_and_clear`），否则上一测试的 `mem` 数组残留数据会导致跨测试的假 pass/fail
- 写 helper 封装（`write_a` / `read_b`）把 GPI 时序锁死在函数里，避免每个测试手写时序

```python
async def write_a(dut, addr, data):
    dut.addra.value = addr
    dut.dina.value = data
    dut.wea.value = full_mask
    dut.ena.value = 1
    await RisingEdge(dut.clka)
    dut.wea.value = 0
    dut.ena.value = 0
    await RisingEdge(dut.clka)   # settle
```

## 坑 4：Verilator 中 prefer 显式移位寄存器 > generate + unpacked 数组

```verilog
// ❌ 复杂，Verilator 可能出现索引推断问题
logic [W-1:0] dout_q [0:LATENCY];
generate for (genvar i = 1; i <= LATENCY; i++)
    always_ff @(posedge clk) dout_q[i] <= dout_q[i-1];
endgenerate

// ✓ 简单直白，所有仿真器友好
logic [W-1:0] dout_s0, dout_s1, dout_s2;
always_ff @(posedge clk) begin
    dout_s0 <= raw;
    dout_s1 <= dout_s0;
    dout_s2 <= dout_s1;
end
assign dout = (LATENCY == 1) ? dout_s0 : (LATENCY == 2) ? dout_s1 : dout_s2;
```
代价：LATENCY 上限固定在 s2（3 级），但实际 BRAM 的 read latency 通常 ≤3 周期。

## 坑 5：LATENCY 的正确语义

Xilinx BRAM LATENCY=N 的含义：**地址在 cycle N 被锁存，数据在 cycle N+1 输出**。
在 Verilator + cocotb 中，这意味着 `dout = dout_s0`（一次寄存器延迟后的值），不是 `dout_s1`（两次延迟）。

## 事前应该查哪些知识条目

动笔写 IP 替身前，重新读这些（按优先级）：
1. `delayed_input_signal.md` — GPI 写延迟、采样点上文
2. `robust_test_reset.md` — 跨测试清除、helper 封装
3. `wsl_verilator_ops.md` — Verilator 语法/参数限制、CRLF 等
4. 本文 — IP 替身特定的 Verilator 陷阱

## 坑 6：FIFO 替身——空读/无效读时 dout 不能更新（FIFO 专属）

**现象**：读空 FIFO 时 dout 变成了下一个内存地址的垃圾值，而不是上次读的有效值。
**根因**：combinational `dout_d` 无条件地从 `mem[rd_ptr_q]` 组装——rd_ptr_q 在上次
成功读后已经推进到了下一个位置，此时再读（无效读）就会读出下一个地址的值。
**修复**：只在 `rd_en && (count >= read_units)` 时才从 mem 读，否则 `dout_d = dout_q`。
```verilog
for (int i = 0; i < READ_UNITS; i++)
    dout_d[i*U +: U] = (rd_en && (count >= RD_UNITS_SZ))
        ? mem[(rd_ptr_q + i) % MEM_DEPTH]
        : dout_q[i*U +: U];
```
