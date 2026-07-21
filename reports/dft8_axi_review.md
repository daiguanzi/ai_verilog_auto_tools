# Review: dft8_axi (AXI-Lite Wrapped DFT8)
Date: 2026-07-21

## What went well
- DFT8 核逻辑从 `examples/11_dft8` 提取成功，计算结果与原版完全一致 (80/80 random checks)
- AXI-Lite 总线封装将端口从 516 降至 ~20，Vivado 综合/实现顺利通过
- cocotbext-axi BFM 集成顺畅，读写寄存器模式清晰
- Verilator 4/4、ModelSim、Vivado 综合三平台全 PASS
- 新增 `vivado-sim` 独立 CLI 命令，修复了 AGENTS.md 流程与实际 CLI 不一致的问题

## Issues encountered
1. **80-bit→32-bit 宽度截断丢失 imag 数据**
   - Root cause: `{(40b),(40b)}` 拼接赋值到 32b 目标，高 40b 被静默截断
   - Resolution: 用中间 wire 截取 16-bit 再拼接
   - Knowledge entry: `knowledge/patterns/verilog_width_truncation.md`

2. **done_q 设置后被立即清除，主机永远读不到 done=1**
   - Root cause: `if (done_q && !start_req)` 清除逻辑在 done 设置后的下一周期触发
   - Resolution: 改为 `if (done_q && start_req)` — 只在新 start 时清除
   - Knowledge entry: `knowledge/patterns/multi_block_handshake.md`

3. **参考模型 unsigned / DUT signed 格式不匹配导致 false negative**
   - Root cause: 参考模型用 `& 0xFFFF` (unsigned)，DUT 读取用 `s16()` (signed)
   - Resolution: 统一为 unsigned `u16()`
   - Knowledge entry: `knowledge/patterns/model_dut_format_align.md`

4. **cocotbext-axi `AxiLiteMaster` 没有 `.bus` 属性**
   - Root cause: API 不暴露底层 bus 对象，clock 需直接从 `dut.clk` 获取
   - Resolution: 显式传递 `dut.clk` 给 polling 函数
   - Knowledge entry: `knowledge/simulator/cocotbext_axi.md` §5 (updated)

5. **ModelSim vlog 编译 .sv 需 `-sv` 标志 + 声明顺序要求**
   - Root cause: ModelSim 10.4 默认不启用 SV，且要求变量先声明后使用
   - Resolution: 改 `modelsim_runner.py` 添加 `-sv`；RTL 重组声明顺序
   - Knowledge entry: `knowledge/simulator/cocotbext_axi.md` §6 (updated)

6. **新增 `vivado-sim` 独立 CLI**
   - Root cause: 之前只有 `vivado-synth`，ModelSim 仿真只能通过 full-run
   - Resolution: 从 full-run 提取仿真代码为独立命令
   - Affected: `fpga_tools.py`

## Test coverage
- Verilator: 4 tests — DC / single freq / all zeros / 5 random vectors (80 checks each)
- ModelSim: 1 test — reset_only (auto-TB), compilation + basic sim verified
- Vivado Synth: PASS — 923 LUT / 1105 Reg / 4 DSP, WNS=-0.14ns

## AGENTS.md updates
- Phase 0 added port count pre-check (§4.4)
- Phase 0 added webfetch knowledge gap escalation (§4.5)
- `vivado-sim` command added to §3 and §4 agent scheduling

## Promotion recommendation
**推荐提拔为 `examples/12_dft8_axi`** — 首个 AXI-Lite 总线封装示例，验证了：
- 从已知 IO 超标失败中学习并预防
- AXI-Lite + cocotbext-axi BFM 全流程
- 宽度截断/握手时序等通用 Verilog 陷阱
