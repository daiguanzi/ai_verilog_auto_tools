---
title: "cocotbext-axi 快速上手（API 要点与坑）"
category: simulator
severity: high
simulator: verilator
created: 2026-06-22
updated: 2026-06-22
sources: [outputs/axil_regs]
related: []
---

## 背景
`cocotbext-axi` (pip install) 提供 AXI-Lite / AXI / AXI-Stream 的 BFM (Bus Functional
Model)，让 cocotb testbench 能像真实 CPU 一样通过 AXI 总线读写 DUT 寄存器。

## 必记要点

1. **数据格式**：`AxiLiteMaster.write(address, data)` 的 `data` 必须是 `bytes`
   （不是 `int`），`read(address, length)` 返回的也是 `bytes`。转换：
   ```python
   def to_bytes(val):  return val.to_bytes(4, "little")
   def from_bytes(b):  return int.from_bytes(b, "little")
   ```

2. **read 需要 length 参数**：`await master.read(addr, 4)` —— 缺少 `length` 会报
   `TypeError: missing 1 required positional argument: 'length'`。

3. **信号命名必须匹配 `from_prefix`**：`AxiLiteBus.from_prefix(dut, "s_axil")`
   会查找 `s_axil_awaddr`, `s_axil_wdata`, `s_axil_bvalid` 等信号（标准 AXI-Lite
   信号名加前缀下划线）。DUT 端口命名直接决定能否自动绑定。

4. **安装**：`pip install cocotbext-axi`（需先装 cocotb）。如果 venv 的 pip 路径
   损坏（因项目目录移动），用 `python -m pip install ...` 代替。
