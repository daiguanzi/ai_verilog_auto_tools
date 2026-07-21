# Review: 8-point Complex DFT (dft8)
Date: 2026-07-21

## What went well
- 多模块/层次化——2 层（dft8_top + complex_mul），依赖树正确
- IP 替身库探索——twiddle 因子用寄存器实现（原本计划用 BRAM 替身，但 8 点 DFT 太小不值得）
- 参考模型 + 随机测试——Python 手动 DFT + 5 组随机向量，Scoreboard 记分
- Verilator 4/4 PASS，ModelSim ALL TESTS PASSED
- Vivado 综合通过：222 LUT / 582 Reg / 4 DSP（纯手写，无 IP 依赖）

## Issues encountered
1. **Verilator 不支持 wire 数组的 `'{}` 初始化** → 改用 `reg + initial`
2. **DFT 累加器跨 bin 迭代未清零** → 根因：第二轮 k 循环开始时 acc 残留上一 bin 的值
3. **Vivado 实现失败** — 516 个物理引脚超过 xc7a200t 的 285 可用 I/O
   - 判定：硬件物理限制，非 RTL 错误
   - 解决：DFT 应作为子模块或改用 AXI 总线接口，不独立做顶层

## Test coverage
- Verilator: 4 tests — DC / 单频 / 全零 / 5 组随机
- ModelSim: 2 tests — DC 输入 / 全零
- Vivado: 综合通过，资源数据可用

## Knowledge entries
- `ip_stub_development.md` 第 6 坑：FIFO 空读不能更新 dout
- `wsl_verilator_ops.md`：wire 数组初始化、cmd.exe Vivado 桥接、导入回退模式
- `vivado_batch_runner.md`：xsim 坑、CRLF、路径

## Promotion recommendation
**提拔为 `examples/11_dft8`** — 第一个纯 DSP 示例，验证了层次化 + RTL 自含（无 IP 依赖）+ cocotb→ModelSim 全流程。可作为后续 DSP 类项目的起手模板。
