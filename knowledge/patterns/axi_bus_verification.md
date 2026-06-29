---
title: "AXI-Lite/Stream 总线验证模式（cocotb + Verilator）"
category: patterns
severity: high
simulator: verilator
created: 2026-06-29
updated: 2026-06-29
sources: [examples/10_axil_regs, templates/tb_comprehensive.py]
related: [knowledge/simulator/cocotbext_axi.md, knowledge/patterns/scoreboard_reference_model.md]
---

## 背景
复杂 FPGA 设计逃不开 AXI 总线（Xilinx 生态的标准互联协议）。在 cocotb 里
必须有一台"假 CPU"能像真的一样读写 DUT 寄存器——这就是 `cocotbext-axi` 的
`AxiLiteMaster` 做的事。

## 模式

### 1. DUT 端口命名（自动绑定）
`cocotbext-axi` 的 `AxiLiteBus.from_prefix(dut, "s_axil")` 会自动查找命名
匹配的信号。约定：**端口名 = 前缀 + 下划线 + AXI 标准信号名**。

```verilog
module my_ip (
    input  logic         s_axil_awaddr,
    input  logic         s_axil_awvalid,
    output logic         s_axil_awready,  // ... 以此类推所有 5 个通道
);
```
不匹配的信号需手动映射，建议直接遵守前缀约定省事。

### 2. Testbench 标准模式
```python
from cocotbext.axi import AxiLiteBus, AxiLiteMaster

bus    = AxiLiteBus.from_prefix(dut, "s_axil")
master = AxiLiteMaster(bus, dut.clk, dut.rst_n, reset_active_level=False)

# 读
val = int.from_bytes(await master.read(0x04, 4), "little")

# 写
await master.write(0x00, 0xDEAD_BEEF.to_bytes(4, "little"))
```

### 3. 数据是 bytes，不是 int
`write(addr, data)` 的 `data` 必须为 `bytes`；`read(addr, length)` 返回的也
是 `bytes`。转换：`int.to_bytes(4, "little")` / `int.from_bytes(b, "little")`。

### 4. 结合 scoreboard 做总线级验证
不满足于 `assert val == expected`——用 reference_model 驱动 AXI 读写，让
scoreboard 自动比对数以千计的寄存器访问。

## 与直连仿真的重要区别
- **直连端口**：testbench 直接写 `dut.a.value = 42`，零开销。
- **AXI 总线**：每次读写经过 5 通道握手（最少 2 个时钟周期），慢但**真实**。

只在 DUT 本身就是一个 AXI slave 时才用 AXI 验证；内部子模块继续保持直连。
混用两者是标准做法：顶层用 AXI BFM 模拟 CPU，内部子模块直连驱动。
