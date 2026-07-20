# ROADMAP.md — 长期路线图

> 新对话顺序：**AGENTS.md → STATUS.md → ROADMAP.md → knowledge/_index.md**
> 本文件记录项目的长期方向与决策依据，`STATUS.md` 记录"当前在哪一步"。
> 创建于 2026-06-22。

---

## 0. 已锁定的架构决策（动手前必读）

| # | 决策 | 理由 |
|---|------|------|
| D1 | **仿真统一用 Verilator + cocotb**；Vivado 只负责构建/时序/bitstream | cocotb 不支持 Vivado xsim；保留现有全部基建 |
| D2 | **混合运行模式**：仿真在 WSL（venv），Vivado 在 Windows 批处理调用 | 各用所长，最省事 |
| D3 | **IP 双轨**：仿真用"替身模型"，构建/上板用"真厂商 IP"，两者永不混用 | 迭代快、上板稳、跨项目一致、可证明等价 |
| D4 | 仅面向 **Xilinx (Vivado 2018.2)** | 用户唯一目标平台 |
| D5 | 所有项目**最终都要上板**，必须有综合/时序/bitstream 轨道 | 仿真过 ≠ 时序收敛 ≠ 能上板 |

### 环境备注
- WSL：Ubuntu，**Python 在虚拟环境 (.venv) 中**，运行命令前需 `source .venv/bin/activate`。
- Windows：Vivado 2018.2（用于综合/时序/bitstream，及 IP 仿真耗时探针）。

### IP 替身战略（D3 展开）
> 一句话：**仿真用替身，上板用真 IP。**

| 顾虑 | 解决办法 |
|------|----------|
| 换开源/手写 RTL 浪费资源、效果差 | 构建/上板永远用真 Xilinx IP，替身只服务仿真，不进最终工程 |
| 仿真与真 IP 行为不一致 | 每个替身配"契约测试"，证明接口行为与 IP 规格一致 |
| 跨项目同功能 IP 写法不一 | 共享替身库 `ip_models/`，全项目复用同一份 |
| 自写 RTL 有 bug、不如 IP 稳 | 替身 bug 不会上板；板上跑原厂 IP |

### 常设流程（贯穿所有阶段）
- **outputs → examples 提拔**：每个项目完成后，按 `AGENTS.md §8` 第 7 条评估是否提拔为
  示例（标准：全过 / 能力独特 / 对应 knowledge / 干净）。**先推荐候选，用户确认后再复制**；
  提拔后删除 outputs 工作副本，并清理与 examples 逐字节相同的冗余副本。`outputs/` 保持纯草稿区。

---

## 1. 路线图总览

```
阶段 0  单模块仿真闭环                          ✅ 已完成 (v1.2)
阶段 A  加固地基（解析/配置/lint）              ← 当前
阶段 B  复杂度升级（多模块 + 总线 + 验证方法学）
阶段 C  IP 双轨战略（替身库 + 真 IP）
阶段 D  上板轨道（综合 / 时序 / bitstream）
阶段 E  端到端整合 + 持续复盘
```

---

## 2. 各阶段任务清单

### 阶段 0 — 单模块仿真闭环 ✅
- [x] sim_driver / fpga_tools / project_gen / reference_reader
- [x] 7 个示例（adder, vending, debounce, uart_tx, spi, fifo, counter）
- [x] 知识库 7 条 + 复盘机制

### 阶段 A — 加固地基（当前）
- [x] A1 用 `verilator --xml-only` 替换 `fpga_tools.py` 的正则模块解析（带正则回退），可靠提取端口/参数/层次/自动找 top（2026-06-22）
- [x] A2 扩展 `project.json`：include 目录、宏定义、参数覆盖、timescale、多文件（2026-06-22，验证项目 `outputs/a2_check`）
- [x] A3 加 lint 门禁：生成 RTL 先过 `verilator --lint-only -Wall -Wno-fatal` 再仿真（2026-06-22，错误阻断、警告仅提示；`run` 默认门禁，可 `--no-lint` 跳过，另有独立 `lint` 命令）
- [x] A4 testbench 模板补充 scoreboard + 参考模型骨架（2026-06-22，`Scoreboard` 类支持 direct/queue 两种用法 + `reference_model` 骨架 + 演示测试，验证 `outputs/a4_check` 2/2）

### 阶段 B — 复杂度升级
- [x] B1 多模块/层次化工程支持（2026-06-22，`print_project_summary` 新增依赖树、多模块示例 `outputs/mac_unit` 4/4 PASS）
- [x] B2 接入 `cocotbext-axi`，验证 AXI-Lite / AXI-Stream 设计（2026-06-22，安装 `cocotbext-axi 0.1.28`、示例 `outputs/axil_regs` 3/3 PASS、知识 `cocotbext_axi.md`）
- [x] B3 随机化 / 覆盖率 / scoreboard 验证模式（2026-06-29，`random_test_sequence` + 种子 + scoreboard；验证 `b3_rand_check` 500 向量 2/2，知识 `randomized_testing.md`）
- [x] B4 知识库新增：总线、CDC（跨时钟域）、复位同步（2026-06-29，`axi_bus_verification.md` / `cdc_guidelines.md` / `reset_strategy.md`）

### 阶段 C — IP 双轨战略
- [x] C1 建 `ip_models/` 共享替身库（2026-07-08）
  - ✅ `ip_models/bram/` — SDP/ROM/SP_RAM + LATENCY + 字节写使能 + 5/5
  - ✅ `ip_models/fifo/` — common/independent clk + 对称/非对称 + 满空/折回/溢出 + 5/5
  - ✅ `ip_models/multiplier/` — signed/unsigned + latency 管线 + 5/5
- [x] C2 每个替身配契约测试（证明与 Xilinx IP 规格一致）（2026-07-08，规范 `contract_test_spec.md`——通用 T1–T5 + IP 专属清单）
- [x] C3 ...
- [x] C4 ...
- [x] C5 ...
- [x] C6 Agent 生成 Vivado Tcl 来创建/配置标准 IP 核 + 导出仿真文件（2026-07-08，`vivado_tools.py` + `fpga_tools.py vivado-ip-tcl`）

### 阶段 D — 上板轨道
- [x] D1 Windows 批处理调用 Vivado 2018.2（`vivado -mode batch -source *.tcl`）：综合→时序→实现→bitstream（2026-07-17，`vivado_backend/synth_runner.py` + `fpga_tools.py vivado-synth` + 项目 `vivado` 段；adder 综合验证通过，切片 LUT=9、寄存器=9、BRAM=0、DSP=0）
- [x] D2 自动生成/管理 XDC 约束（时钟、引脚、伪路径）（2026-07-17，`vivado_backend/xdc_tools.py` + `fpga_tools.py vivado-xdc` + project.json `vivado.clocks`/`pins`；adder+10ns时钟综合：WNS=4.5ns,TNS=0.0）
- [x] D3 解析时序报告(WNS/TNS)，形成"时序不收敛→自动迭代"闭环（2026-07-17，增强 `_parse_timing` 抽取 failure paths；`timing_loop` 自动放宽周期→重综合→收敛；验证 2→4→8ns 自动收敛到 WNS=+3.59ns）
- [x] D4 知识库新增：时序收敛、约束、资源占用（2026-07-17，`timing_closure.md`——WNS/TNS 解读/修复策略/资源解读/经验数字）

### 🧊 ISE VM 并行轨道（按需启用）
> 仅在项目明确需要 ISE（用户指定 / 器件老旧 / 有 `.xise`）时才走这条线。
> 前端仿真仍用 Verilator；ISim 仅作环境验证 + ISE 综合/bitstream。
> ⚠️ **ISim 只支持 Verilog-2001**（禁止 `logic`/`always_ff`/SV 端口声明）。
- [x] ISE-1 搬运 `ISE_Remote.ps1` + 建 `ise_backend/` 目录 + `vm_config.json`（2026-07-08）
- [x] ISE-2 实现 `ise_remote.py`：VM 管理 / ISE 命令执行 / XST 综合流 / ISim 仿真 + 自动 TB 生成 / 报告解析（2026-07-08，实测 fifo TB ✅ + auto-TB 加法器 4 向量 ✅）
- [x] ISE-3 扩展 `project.json` 增加 `ise` 可选段 + `fpga_tools.py` 集成（检测 ISE 需求、调 ISE 后端）（2026-07-20，`ise-synth`/`ise-sim` CLI 命令）
- [ ] ISE-4 实际端到端验证：用 ISE VM 跑一个 Spartan-6 工程全流程（含 XST 综合 + 时序报告）

### 阶段 E — 端到端整合
- [x] E1 一条命令：需求→仿真过→lint 过→Vivado综合（2026-07-20，`fpga_tools.py full-run`——lint→sim→vivado-synth 串行；WSL:lint+sim；Win:sim+vivado）
- [ ] E2 每个真实项目跑完强制复盘进 knowledge/

### 🧪 阶段 D/E 完成后的全流程验证项目
- [ ] **8 点 DFT**（信号处理类）——测全流程：多模块层次 + BRAM/Mult 替身 + Python 参考模型 + scoreboard + Vivado 综合 → 资源/时序报告
  测试目标：验证 agent 从需求 → RTL → 仿真 → lint → IP 替身 → Vivado 综合 → 时序报告 的完整闭环。

---

## 3. 数据探针（动手阶段 A 前后并行进行，给决策提供真实数据）

- [x] P1 实测一个带 IP 工程在 Vivado 2018.2 上的仿真模型导出与 Verilator 编译（2026-06-29）→ 结论：不能直接编译，替身是主要路径。
- [x] P2 验证能否从本环境批处理调起 Windows Vivado（2026-06-29）→ 可以，`vivado -mode batch -source script.tcl` 在 `C:\Xilinx\Vivado\2018.2` 正常工作。

---

## 4. 版本日志
| 版本 | 日期 | 内容 |
|------|------|------|
| — | 2026-06-22 | 制定长期路线图（阶段 A–E），锁定架构决策 D1–D5 |
