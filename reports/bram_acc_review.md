# Review: BRAM IP (IP 双轨验证)
Date: 2026-07-21

## What went well
- `project.json` `ip` 段自动引入 `ip_models/bram/ip_bram.sv` 替身
- IP stub 的 LATENCY 参数正确工作（需要多 1 拍等待）
- Verilator + ModelSim + Vivado 三平台全 PASS
- IP 双轨模式验证成功：仿真用替身，上板用真 IP

## Issues encountered
1. **BRAM LATENCY=1 需要额外等待周期**
   - 读操作后需等 LATENCY+2 拍数据才在 dout 可见
   - Resolution: `await ClockCycles(dut.clk, 3)` 替代 `2`
   - Knowledge: `ip_stub_development.md` 已覆盖

## Test coverage
- Verilator: 1 test — 16× write/read (16/16 checks passed)
- ModelSim + Vivado: PASS

## Promotion recommendation
不单独提拔为 example——BRAM IP 本身已在 `ip_models/bram/` 作为共享替身库存在。`bram_acc` 是 IP 使用方示例，验证了 IP 双轨机制的有效性。
