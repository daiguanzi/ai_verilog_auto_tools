# Review: Async FIFO (CDC, Gray-coded)
Date: 2026-07-21

## What went well
- 双时钟域 Gray code CDC 设计一次编译通过
- Verilator (3/3) + ModelSim + Vivado 三平台全 PASS
- 60 LUT / 174 Reg / WNS=+9.086ns @ 100MHz
- 标准 2-FF synchronizer 处理 CDC 路径
- 有效深度 DEPTH-1 = 7（标准异步 FIFO 行为，非 bug）

## Issues encountered
1. **FIFO 有效容量是 DEPTH-1**
   - 标准 async FIFO full 检测算法正确阻止第 DEPTH 次写入
   - 测试需写入 DEPTH-1 次而非 DEPTH 次
   - Knowledge: 更新 `ip_stub_development.md`

2. **dout 组合逻辑导致读采样时机错误**
   - 组合输出在 `rd_en` 上升沿后立即变化，采样点需在沿上
   - Resolution: 加 registered dout（标准 FIFO 输出寄存器）
   - Knowledge: `delayed_input_signal.md` 包含此模式

## Test coverage
- Verilator: 3 tests — write-read / full-empty / random (20/20)
- ModelSim: compilation + reset test
- Vivado: 60 LUT / 174 Reg / 0 BRAM / 0 DSP

## Promotion recommendation
**提拔为 `examples/14_async_fifo`** — 首个跨时钟域 (CDC) 示例，验证了双时钟 simulatoin + Gray code 指针同步。
