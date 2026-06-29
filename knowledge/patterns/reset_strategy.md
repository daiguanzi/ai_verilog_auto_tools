---
title: "复位同步与复位策略——为什么异步复位不可靠"
category: patterns
severity: high
simulator: verilator
created: 2026-06-29
updated: 2026-06-29
sources: []
related: [knowledge/patterns/cdc_guidelines.md, knowledge/patterns/robust_test_reset.md]
---

## 问题
异步复位 (`always_ff @(posedge clk or negedge rst_n)`) 在 Verilator/cocotb
里看起来很好用，但真实板子上有两个致命问题：
1. **复位释放时机**：rst_n 拉高时如果恰好离时钟沿太近，部分寄存器释放、
   部分还在复位——整个电路状态不一致。
2. **GPI 污染**：cocotb 里上一测试的 GPI 状态会漏到下一测试，异步复位
   `assert count == 0` after reset 经常失败。

## 解决方案

### 1. RTL 层面的复位同步器（上板用）
```verilog
logic rst_sync_q1, rst_synced;
always_ff @(posedge clk) begin  // 注意：仅用 posedge clk，不是异步
    rst_sync_q1 <= ~async_rst_n;  // 负逻辑转为正逻辑
    rst_synced  <= rst_sync_q1;
end
wire rst_n_synced = ~rst_synced; // 转回负逻辑
```
所有模块都用 `rst_n_synced`（同步释放），不要直接接外部 `rst_n`。

### 2. cocotb 里的安全做法
```python
async def reset_and_clear(dut):
    """用 load 或写入已知值初始化，不依赖 reset assertion 后的值。"""
    dut.rst_n.value = 0
    for _ in range(5):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    for _ in range(5):
        await RisingEdge(dut.clk)
    # 显式清零所有控制输入，防止跨测试 GPI 污染
    dut.enable.value = 0
    dut.a.value = 0
    dut.b.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
```

### 3. 已经有的知识条目
`robust_test_reset.md` 专门讲 cocotb 里 GPI 污染的应对，这里是上板层面的补充。
两篇合在一起 = 完整的复位策略（仿真 + 硬件）。

## 一句话
仿真里能跑 ≠ 复位可靠。**上板前加复位同步器**；**cocotb 测试里不依赖 reset 后的值**，用显式 load 代替。
