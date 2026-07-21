# Review: FIR Filter (AXI-Lite, 8-tap)
Date: 2026-07-21

## What went well
- AXI-Lite 封装模式成熟：直接从 dft8_axi 复用 AXI register file 模式，零修改
- 参考模型 + scoreboard + 随机测试：4 tests, 80 random checks 全通过
- Verilator (4/4) + ModelSim + Vivado(综合+实现) 三平台全 PASS
- Vivado GUI 工程增量更新：open_project 模式下修改源码后无需删除重生成
- full-run --no-sim 避免重复仿真
- WNS=+1.71ns @ 100MHz，时序收敛

## Issues encountered
1. **`.v` 扩展名 → Vivado 语法错误**
   - RTL 使用 SV 语法 (`for (int i...)`, `[8*i+:8]`)，文件名却是 `.v`
   - Vivado 将 `.v` 当纯 Verilog 处理，报 syntax error
   - Verilator 自动检测语法所以不受影响
   - Resolution: 改名 `.sv`
   - Knowledge: 已有 `cocotbext_axi.md` §6 (ModelSim -sv)，延伸为通用规则

2. **CTRL 寄存器地址与 sample[0] 冲突**
   - CTRL_IDX=16 恰好等于 sample 起始地址，写 start 覆盖了 sample[0]
   - Root cause: 16 taps 需要 34 寄存器 > 32 地址空间
   - Resolution: 精简到 8 taps，CTRL/RESULT 放在数据段后面
   - Knowledge: 新增到 `patterns/register_map_overlap.md`（待写）

3. **参考模型 unsigned vs DUT signed 格式不匹配**
   - 与 DFT8 完全相同的坑（第二次犯了！）
   - Knowledge entry: `model_dut_format_align.md` 存在但未在使用前重读
   - **Process failure**: 知识库有但 Agent 没读

4. **ModelSim 声明顺序**
   - `state`, `acc` 在 AXI always 块引用后才声明
   - Resolution: 移到文件顶部
   - Same pattern as dft8_axi → knowledge exists

## Test coverage
- Verilator: 4 tests — DC / impulse / all zeros / 5 random vectors
- ModelSim: basic compilation + reset test
- Vivado synth/impl: 923 LUT, 1105 Reg, 4 DSP @ 100MHz

## Knowledge delta
- **New**: `webfetch_strategy.md` (webfetch 搜索策略)
- **Updated**: `cocotbext_axi.md` §5-6 (AXI clock + ModelSim -sv)
- **Should create**: `register_map_overlap.md` (AXI 寄存器地址冲突防护)
- **Process note**: 格式对齐问题第二次出现——`model_dut_format_align.md` 应该在每个新项目前重读

## Promotion recommendation
**提拔为 `examples/13_fir_filter`** — 首个流水线 DSP 实例 + 首个从已有示例复用 AXI 模式的案例。
验证了：AXI 模式复用、FIR 参考模型、Vivado GUI 增量更新、`.sv` 命名规则。
